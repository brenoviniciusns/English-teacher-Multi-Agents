"""
WebSocket Manager
Manages WebSocket connections for real-time audio streaming and communication.
"""
import logging
import json
import base64
from typing import Optional, Callable, Awaitable
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection."""
    websocket: WebSocket
    user_id: str
    session_id: str
    connected_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    namespace: str = "default"
    metadata: dict = field(default_factory=dict)


class WebSocketManager:
    """
    Manages WebSocket connections for the application.

    Supports:
    - Multiple namespaces (pronunciation, speaking, etc.)
    - User-specific connections
    - Broadcasting to namespaces
    - Audio streaming
    """

    def __init__(self):
        # Connections by namespace and user_id
        self._connections: dict[str, dict[str, ConnectionInfo]] = {}
        # Message handlers by namespace
        self._handlers: dict[str, Callable[[str, dict], Awaitable[dict]]] = {}

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        session_id: str,
        namespace: str = "default"
    ) -> bool:
        """
        Accept a new WebSocket connection.

        Args:
            websocket: The WebSocket connection
            user_id: User identifier
            session_id: Session identifier
            namespace: Connection namespace (pronunciation, speaking, etc.)

        Returns:
            True if connection successful
        """
        try:
            await websocket.accept()

            # Initialize namespace if needed
            if namespace not in self._connections:
                self._connections[namespace] = {}

            # Store connection
            connection = ConnectionInfo(
                websocket=websocket,
                user_id=user_id,
                session_id=session_id,
                namespace=namespace
            )
            self._connections[namespace][user_id] = connection

            logger.info(f"WebSocket connected: user={user_id}, namespace={namespace}")

            # Send confirmation
            await self.send_message(user_id, namespace, {
                "type": "connected",
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat()
            })

            return True

        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
            return False

    async def disconnect(self, user_id: str, namespace: str = "default"):
        """
        Disconnect a WebSocket connection.

        Args:
            user_id: User identifier
            namespace: Connection namespace
        """
        try:
            if namespace in self._connections and user_id in self._connections[namespace]:
                connection = self._connections[namespace][user_id]
                try:
                    await connection.websocket.close()
                except Exception:
                    pass  # Connection might already be closed
                del self._connections[namespace][user_id]
                logger.info(f"WebSocket disconnected: user={user_id}, namespace={namespace}")
        except Exception as e:
            logger.error(f"WebSocket disconnect error: {e}")

    async def send_message(
        self,
        user_id: str,
        namespace: str,
        message: dict
    ) -> bool:
        """
        Send a message to a specific user.

        Args:
            user_id: User identifier
            namespace: Connection namespace
            message: Message to send (dict)

        Returns:
            True if message sent successfully
        """
        try:
            if namespace in self._connections and user_id in self._connections[namespace]:
                connection = self._connections[namespace][user_id]
                await connection.websocket.send_json(message)
                return True
            return False
        except Exception as e:
            logger.error(f"WebSocket send error: {e}")
            return False

    async def send_binary(
        self,
        user_id: str,
        namespace: str,
        data: bytes
    ) -> bool:
        """
        Send binary data to a specific user.

        Args:
            user_id: User identifier
            namespace: Connection namespace
            data: Binary data to send

        Returns:
            True if data sent successfully
        """
        try:
            if namespace in self._connections and user_id in self._connections[namespace]:
                connection = self._connections[namespace][user_id]
                await connection.websocket.send_bytes(data)
                return True
            return False
        except Exception as e:
            logger.error(f"WebSocket binary send error: {e}")
            return False

    async def broadcast(self, namespace: str, message: dict):
        """
        Broadcast a message to all connections in a namespace.

        Args:
            namespace: Connection namespace
            message: Message to broadcast
        """
        if namespace not in self._connections:
            return

        disconnected = []
        for user_id, connection in self._connections[namespace].items():
            try:
                await connection.websocket.send_json(message)
            except Exception:
                disconnected.append(user_id)

        # Clean up disconnected
        for user_id in disconnected:
            await self.disconnect(user_id, namespace)

    def register_handler(
        self,
        namespace: str,
        handler: Callable[[str, dict], Awaitable[dict]]
    ):
        """
        Register a message handler for a namespace.

        Args:
            namespace: Connection namespace
            handler: Async function that processes messages and returns response
        """
        self._handlers[namespace] = handler
        logger.info(f"Registered handler for namespace: {namespace}")

    async def handle_message(
        self,
        user_id: str,
        namespace: str,
        message: dict
    ) -> Optional[dict]:
        """
        Handle an incoming message.

        Args:
            user_id: User identifier
            namespace: Connection namespace
            message: Received message

        Returns:
            Response message or None
        """
        if namespace in self._handlers:
            try:
                return await self._handlers[namespace](user_id, message)
            except Exception as e:
                logger.error(f"Handler error for namespace {namespace}: {e}")
                return {"error": str(e)}
        return None

    def get_connection(
        self,
        user_id: str,
        namespace: str = "default"
    ) -> Optional[ConnectionInfo]:
        """Get connection info for a user."""
        if namespace in self._connections:
            return self._connections[namespace].get(user_id)
        return None

    def is_connected(self, user_id: str, namespace: str = "default") -> bool:
        """Check if a user is connected in a namespace."""
        return (
            namespace in self._connections and
            user_id in self._connections[namespace]
        )

    def get_active_connections(self, namespace: str = "default") -> list[str]:
        """Get list of user IDs with active connections in a namespace."""
        if namespace in self._connections:
            return list(self._connections[namespace].keys())
        return []

    def get_stats(self) -> dict:
        """Get connection statistics."""
        stats = {
            "total_connections": 0,
            "namespaces": {}
        }
        for namespace, connections in self._connections.items():
            count = len(connections)
            stats["namespaces"][namespace] = count
            stats["total_connections"] += count
        return stats


# Singleton instance
websocket_manager = WebSocketManager()


# ==================== PRONUNCIATION WEBSOCKET HANDLER ====================

async def pronunciation_ws_handler(user_id: str, message: dict) -> dict:
    """
    Handle pronunciation WebSocket messages.

    Message types:
    - audio_chunk: Incoming audio data chunk
    - audio_complete: Audio recording complete, start assessment
    - get_reference: Request reference audio for a word
    """
    from app.agents.pronunciation_agent import pronunciation_agent
    from app.services.azure_speech_service import azure_speech_service

    msg_type = message.get("type")

    if msg_type == "audio_chunk":
        # For streaming audio - collect chunks
        # In production, would buffer and process
        return {"type": "chunk_received"}

    elif msg_type == "audio_complete":
        # Process complete audio
        audio_base64 = message.get("audio_base64")
        reference_text = message.get("reference_text")
        sound_id = message.get("sound_id")

        if not audio_base64 or not reference_text:
            return {
                "type": "error",
                "message": "Missing audio or reference text"
            }

        try:
            audio_bytes = base64.b64decode(audio_base64)
            result = azure_speech_service.pronunciation_assessment(
                audio_data=audio_bytes,
                reference_text=reference_text,
                granularity="phoneme"
            )

            return {
                "type": "assessment_result",
                "sound_id": sound_id,
                **result
            }
        except Exception as e:
            return {
                "type": "error",
                "message": str(e)
            }

    elif msg_type == "get_reference":
        # Generate reference audio
        word = message.get("word")
        voice = message.get("voice", "american_female")

        if not word:
            return {
                "type": "error",
                "message": "Missing word for reference audio"
            }

        try:
            audio_bytes = azure_speech_service.text_to_speech(
                text=word,
                voice=voice,
                output_format="wav"
            )
            audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

            return {
                "type": "reference_audio",
                "word": word,
                "audio_base64": audio_base64
            }
        except Exception as e:
            return {
                "type": "error",
                "message": str(e)
            }

    return {"type": "unknown", "message": f"Unknown message type: {msg_type}"}


# Register pronunciation handler
websocket_manager.register_handler("pronunciation", pronunciation_ws_handler)

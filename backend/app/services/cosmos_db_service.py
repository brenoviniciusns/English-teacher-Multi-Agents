"""
Azure Cosmos DB Service
Provides data persistence for users, progress tracking, activities, and schedules.
All containers use user_id as partition key for efficient queries.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Any
from azure.cosmos import CosmosClient, PartitionKey, exceptions

from app.config import settings

logger = logging.getLogger(__name__)


class CosmosDBService:
    """Service for Azure Cosmos DB operations"""

    def __init__(self):
        self.client = CosmosClient(
            url=settings.COSMOS_DB_ENDPOINT,
            credential=settings.COSMOS_DB_KEY
        )
        self.database_name = settings.COSMOS_DB_DATABASE_NAME
        self.database = None
        self.containers = {}

        # Container names from settings
        self.container_names = {
            "users": settings.COSMOS_DB_USERS_CONTAINER,
            "vocabulary_progress": settings.COSMOS_DB_VOCABULARY_PROGRESS_CONTAINER,
            "grammar_progress": settings.COSMOS_DB_GRAMMAR_PROGRESS_CONTAINER,
            "pronunciation_progress": settings.COSMOS_DB_PRONUNCIATION_PROGRESS_CONTAINER,
            "activities": settings.COSMOS_DB_ACTIVITIES_CONTAINER,
            "speaking_sessions": settings.COSMOS_DB_SPEAKING_SESSIONS_CONTAINER,
            "schedule": settings.COSMOS_DB_SCHEDULE_CONTAINER
        }

    async def initialize(self):
        """Initialize database and containers. Call on app startup."""
        try:
            # Create database if not exists
            self.database = self.client.create_database_if_not_exists(
                id=self.database_name
            )
            logger.info(f"Database '{self.database_name}' ready")

            # Create containers if not exist
            for key, container_name in self.container_names.items():
                container = self.database.create_container_if_not_exists(
                    id=container_name,
                    partition_key=PartitionKey(path="/partitionKey"),
                    offer_throughput=400  # Minimum RU/s
                )
                self.containers[key] = container
                logger.info(f"Container '{container_name}' ready")

            return True
        except Exception as e:
            logger.error(f"Cosmos DB initialization error: {e}")
            raise

    def _get_container(self, container_key: str):
        """Get a container by key."""
        if container_key not in self.containers:
            # Lazy initialization
            container_name = self.container_names.get(container_key)
            if not container_name:
                raise ValueError(f"Unknown container key: {container_key}")
            if not self.database:
                self.database = self.client.get_database_client(self.database_name)
            self.containers[container_key] = self.database.get_container_client(container_name)
        return self.containers[container_key]

    # ==================== GENERIC CRUD OPERATIONS ====================

    async def create_item(
        self,
        container_key: str,
        item: dict,
        partition_key: str
    ) -> dict:
        """Create a new item in a container."""
        try:
            container = self._get_container(container_key)
            item["partitionKey"] = partition_key
            item["createdAt"] = datetime.utcnow().isoformat()
            item["updatedAt"] = datetime.utcnow().isoformat()
            result = container.create_item(body=item)
            logger.debug(f"Created item in {container_key}: {item.get('id')}")
            return result
        except exceptions.CosmosResourceExistsError:
            logger.warning(f"Item already exists in {container_key}: {item.get('id')}")
            raise
        except Exception as e:
            logger.error(f"Create item error in {container_key}: {e}")
            raise

    async def get_item(
        self,
        container_key: str,
        item_id: str,
        partition_key: str
    ) -> Optional[dict]:
        """Get an item by ID and partition key."""
        try:
            container = self._get_container(container_key)
            item = container.read_item(item=item_id, partition_key=partition_key)
            return item
        except exceptions.CosmosResourceNotFoundError:
            return None
        except Exception as e:
            logger.error(f"Get item error in {container_key}: {e}")
            raise

    async def update_item(
        self,
        container_key: str,
        item_id: str,
        partition_key: str,
        updates: dict
    ) -> dict:
        """Update an existing item."""
        try:
            container = self._get_container(container_key)
            # Get current item
            item = container.read_item(item=item_id, partition_key=partition_key)
            # Apply updates
            item.update(updates)
            item["updatedAt"] = datetime.utcnow().isoformat()
            # Replace item
            result = container.replace_item(item=item_id, body=item)
            logger.debug(f"Updated item in {container_key}: {item_id}")
            return result
        except Exception as e:
            logger.error(f"Update item error in {container_key}: {e}")
            raise

    async def upsert_item(
        self,
        container_key: str,
        item: dict,
        partition_key: str
    ) -> dict:
        """Create or update an item."""
        try:
            container = self._get_container(container_key)
            item["partitionKey"] = partition_key
            item["updatedAt"] = datetime.utcnow().isoformat()
            if "createdAt" not in item:
                item["createdAt"] = datetime.utcnow().isoformat()
            result = container.upsert_item(body=item)
            logger.debug(f"Upserted item in {container_key}: {item.get('id')}")
            return result
        except Exception as e:
            logger.error(f"Upsert item error in {container_key}: {e}")
            raise

    async def delete_item(
        self,
        container_key: str,
        item_id: str,
        partition_key: str
    ) -> bool:
        """Delete an item."""
        try:
            container = self._get_container(container_key)
            container.delete_item(item=item_id, partition_key=partition_key)
            logger.debug(f"Deleted item in {container_key}: {item_id}")
            return True
        except exceptions.CosmosResourceNotFoundError:
            return False
        except Exception as e:
            logger.error(f"Delete item error in {container_key}: {e}")
            raise

    async def query_items(
        self,
        container_key: str,
        query: str,
        parameters: Optional[list] = None,
        partition_key: Optional[str] = None
    ) -> list:
        """Query items using SQL."""
        try:
            container = self._get_container(container_key)
            items = list(container.query_items(
                query=query,
                parameters=parameters or [],
                partition_key=partition_key,
                enable_cross_partition_query=partition_key is None
            ))
            return items
        except Exception as e:
            logger.error(f"Query error in {container_key}: {e}")
            raise

    # ==================== USER OPERATIONS ====================

    async def create_user(self, user_data: dict) -> dict:
        """Create a new user."""
        user_data["id"] = user_data.get("id") or user_data["email"]
        return await self.create_item("users", user_data, user_data["id"])

    async def get_user(self, user_id: str) -> Optional[dict]:
        """Get user by ID."""
        return await self.get_item("users", user_id, user_id)

    async def get_user_by_email(self, email: str) -> Optional[dict]:
        """Get user by email."""
        query = "SELECT * FROM c WHERE c.email = @email"
        parameters = [{"name": "@email", "value": email}]
        results = await self.query_items("users", query, parameters)
        return results[0] if results else None

    async def update_user(self, user_id: str, updates: dict) -> dict:
        """Update user data."""
        return await self.update_item("users", user_id, user_id, updates)

    # ==================== VOCABULARY PROGRESS ====================

    async def get_vocabulary_progress(
        self,
        user_id: str,
        word_id: Optional[str] = None
    ) -> list | dict | None:
        """Get vocabulary progress for a user."""
        if word_id:
            item_id = f"vocab_{user_id}_{word_id}"
            return await self.get_item("vocabulary_progress", item_id, user_id)
        else:
            query = "SELECT * FROM c WHERE c.partitionKey = @user_id"
            parameters = [{"name": "@user_id", "value": user_id}]
            return await self.query_items("vocabulary_progress", query, parameters, user_id)

    async def update_vocabulary_progress(
        self,
        user_id: str,
        word_id: str,
        progress_data: dict
    ) -> dict:
        """Update or create vocabulary progress for a word."""
        item_id = f"vocab_{user_id}_{word_id}"
        progress_data["id"] = item_id
        progress_data["userId"] = user_id
        progress_data["wordId"] = word_id
        return await self.upsert_item("vocabulary_progress", progress_data, user_id)

    async def get_vocabulary_due_for_review(self, user_id: str) -> list:
        """Get vocabulary items due for SRS review."""
        today = datetime.utcnow().isoformat()
        query = """
            SELECT * FROM c
            WHERE c.partitionKey = @user_id
            AND c.srsData.nextReview <= @today
            ORDER BY c.srsData.nextReview ASC
        """
        parameters = [
            {"name": "@user_id", "value": user_id},
            {"name": "@today", "value": today}
        ]
        return await self.query_items("vocabulary_progress", query, parameters, user_id)

    async def get_vocabulary_low_frequency(self, user_id: str, days: int = 7) -> list:
        """Get vocabulary items not used in the last N days."""
        threshold = (datetime.utcnow() - timedelta(days=days)).isoformat()
        query = """
            SELECT * FROM c
            WHERE c.partitionKey = @user_id
            AND (c.lastPracticed < @threshold OR NOT IS_DEFINED(c.lastPracticed))
        """
        parameters = [
            {"name": "@user_id", "value": user_id},
            {"name": "@threshold", "value": threshold}
        ]
        return await self.query_items("vocabulary_progress", query, parameters, user_id)

    # ==================== GRAMMAR PROGRESS ====================

    async def get_grammar_progress(
        self,
        user_id: str,
        rule_id: Optional[str] = None
    ) -> list | dict | None:
        """Get grammar progress for a user."""
        if rule_id:
            item_id = f"grammar_{user_id}_{rule_id}"
            return await self.get_item("grammar_progress", item_id, user_id)
        else:
            query = "SELECT * FROM c WHERE c.partitionKey = @user_id"
            parameters = [{"name": "@user_id", "value": user_id}]
            return await self.query_items("grammar_progress", query, parameters, user_id)

    async def update_grammar_progress(
        self,
        user_id: str,
        rule_id: str,
        progress_data: dict
    ) -> dict:
        """Update or create grammar progress for a rule."""
        item_id = f"grammar_{user_id}_{rule_id}"
        progress_data["id"] = item_id
        progress_data["userId"] = user_id
        progress_data["ruleId"] = rule_id
        return await self.upsert_item("grammar_progress", progress_data, user_id)

    async def get_grammar_due_for_review(self, user_id: str) -> list:
        """Get grammar rules due for review."""
        today = datetime.utcnow().isoformat()
        query = """
            SELECT * FROM c
            WHERE c.partitionKey = @user_id
            AND c.srsData.nextReview <= @today
        """
        parameters = [
            {"name": "@user_id", "value": user_id},
            {"name": "@today", "value": today}
        ]
        return await self.query_items("grammar_progress", query, parameters, user_id)

    # ==================== PRONUNCIATION PROGRESS ====================

    async def get_pronunciation_progress(
        self,
        user_id: str,
        sound_id: Optional[str] = None
    ) -> list | dict | None:
        """Get pronunciation progress for a user."""
        if sound_id:
            item_id = f"pronun_{user_id}_{sound_id}"
            return await self.get_item("pronunciation_progress", item_id, user_id)
        else:
            query = "SELECT * FROM c WHERE c.partitionKey = @user_id"
            parameters = [{"name": "@user_id", "value": user_id}]
            return await self.query_items("pronunciation_progress", query, parameters, user_id)

    async def update_pronunciation_progress(
        self,
        user_id: str,
        sound_id: str,
        progress_data: dict
    ) -> dict:
        """Update or create pronunciation progress for a sound."""
        item_id = f"pronun_{user_id}_{sound_id}"
        progress_data["id"] = item_id
        progress_data["userId"] = user_id
        progress_data["soundId"] = sound_id
        return await self.upsert_item("pronunciation_progress", progress_data, user_id)

    async def get_pronunciation_needs_practice(
        self,
        user_id: str,
        accuracy_threshold: int = 80
    ) -> list:
        """Get pronunciation sounds that need more practice."""
        query = """
            SELECT * FROM c
            WHERE c.partitionKey = @user_id
            AND c.averageAccuracy < @threshold
        """
        parameters = [
            {"name": "@user_id", "value": user_id},
            {"name": "@threshold", "value": accuracy_threshold}
        ]
        return await self.query_items("pronunciation_progress", query, parameters, user_id)

    # ==================== ACTIVITIES ====================

    async def create_activity(self, user_id: str, activity_data: dict) -> dict:
        """Create a new activity."""
        activity_data["id"] = f"activity_{user_id}_{datetime.utcnow().timestamp()}"
        activity_data["userId"] = user_id
        activity_data["status"] = activity_data.get("status", "pending")
        return await self.create_item("activities", activity_data, user_id)

    async def get_pending_activities(
        self,
        user_id: str,
        pillar: Optional[str] = None
    ) -> list:
        """Get pending activities for a user."""
        if pillar:
            query = """
                SELECT * FROM c
                WHERE c.partitionKey = @user_id
                AND c.status = 'pending'
                AND c.pillar = @pillar
                ORDER BY c.createdAt ASC
            """
            parameters = [
                {"name": "@user_id", "value": user_id},
                {"name": "@pillar", "value": pillar}
            ]
        else:
            query = """
                SELECT * FROM c
                WHERE c.partitionKey = @user_id
                AND c.status = 'pending'
                ORDER BY c.createdAt ASC
            """
            parameters = [{"name": "@user_id", "value": user_id}]
        return await self.query_items("activities", query, parameters, user_id)

    async def complete_activity(
        self,
        user_id: str,
        activity_id: str,
        result_data: dict
    ) -> dict:
        """Mark an activity as completed."""
        updates = {
            "status": "completed",
            "completedAt": datetime.utcnow().isoformat(),
            "result": result_data
        }
        return await self.update_item("activities", activity_id, user_id, updates)

    # ==================== SPEAKING SESSIONS ====================

    async def create_speaking_session(
        self,
        user_id: str,
        session_data: dict
    ) -> dict:
        """Create a new speaking session."""
        session_data["id"] = f"session_{user_id}_{datetime.utcnow().timestamp()}"
        session_data["userId"] = user_id
        session_data["startedAt"] = datetime.utcnow().isoformat()
        session_data["exchanges"] = []
        return await self.create_item("speaking_sessions", session_data, user_id)

    async def get_speaking_session(
        self,
        user_id: str,
        session_id: str
    ) -> Optional[dict]:
        """Get a speaking session by ID."""
        return await self.get_item("speaking_sessions", session_id, user_id)

    async def update_speaking_session(
        self,
        user_id: str,
        session_id: str,
        updates: dict
    ) -> dict:
        """Update a speaking session."""
        return await self.update_item("speaking_sessions", session_id, user_id, updates)

    async def end_speaking_session(
        self,
        user_id: str,
        session_id: str,
        summary: dict
    ) -> dict:
        """End a speaking session and save summary."""
        updates = {
            "endedAt": datetime.utcnow().isoformat(),
            "summary": summary
        }
        return await self.update_item("speaking_sessions", session_id, user_id, updates)

    # ==================== SCHEDULE ====================

    async def get_daily_schedule(self, user_id: str, date: str = None) -> Optional[dict]:
        """Get schedule for a specific date."""
        if date is None:
            date = datetime.utcnow().strftime("%Y-%m-%d")
        schedule_id = f"schedule_{user_id}_{date}"
        return await self.get_item("schedule", schedule_id, user_id)

    async def create_or_update_schedule(
        self,
        user_id: str,
        date: str,
        schedule_data: dict
    ) -> dict:
        """Create or update daily schedule."""
        schedule_id = f"schedule_{user_id}_{date}"
        schedule_data["id"] = schedule_id
        schedule_data["userId"] = user_id
        schedule_data["date"] = date
        return await self.upsert_item("schedule", schedule_data, user_id)

    async def get_week_schedule(self, user_id: str) -> list:
        """Get schedule for the next 7 days."""
        today = datetime.utcnow()
        dates = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

        query = """
            SELECT * FROM c
            WHERE c.partitionKey = @user_id
            AND c.date IN (@date0, @date1, @date2, @date3, @date4, @date5, @date6)
            ORDER BY c.date ASC
        """
        parameters = [{"name": "@user_id", "value": user_id}]
        for i, date in enumerate(dates):
            parameters.append({"name": f"@date{i}", "value": date})

        return await self.query_items("schedule", query, parameters, user_id)

    # ==================== STATISTICS ====================

    async def get_user_statistics(self, user_id: str) -> dict:
        """Get comprehensive statistics for a user."""
        stats = {
            "vocabulary": {},
            "grammar": {},
            "pronunciation": {},
            "speaking": {},
            "overall": {}
        }

        # Vocabulary stats
        vocab_progress = await self.get_vocabulary_progress(user_id)
        if vocab_progress:
            stats["vocabulary"]["total_words"] = len(vocab_progress)
            stats["vocabulary"]["mastered"] = sum(
                1 for v in vocab_progress if v.get("masteryLevel") == "mastered"
            )
            stats["vocabulary"]["learning"] = sum(
                1 for v in vocab_progress if v.get("masteryLevel") == "learning"
            )

        # Grammar stats
        grammar_progress = await self.get_grammar_progress(user_id)
        if grammar_progress:
            stats["grammar"]["total_rules"] = len(grammar_progress)
            stats["grammar"]["average_score"] = sum(
                g.get("lastScore", 0) for g in grammar_progress
            ) / len(grammar_progress) if grammar_progress else 0

        # Pronunciation stats
        pronun_progress = await self.get_pronunciation_progress(user_id)
        if pronun_progress:
            stats["pronunciation"]["total_sounds"] = len(pronun_progress)
            stats["pronunciation"]["average_accuracy"] = sum(
                p.get("averageAccuracy", 0) for p in pronun_progress
            ) / len(pronun_progress) if pronun_progress else 0

        # Speaking sessions count (last 30 days)
        thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).isoformat()
        query = """
            SELECT VALUE COUNT(1) FROM c
            WHERE c.partitionKey = @user_id
            AND c.startedAt > @threshold
        """
        parameters = [
            {"name": "@user_id", "value": user_id},
            {"name": "@threshold", "value": thirty_days_ago}
        ]
        result = await self.query_items("speaking_sessions", query, parameters, user_id)
        stats["speaking"]["sessions_last_30_days"] = result[0] if result else 0

        return stats


# Singleton instance
cosmos_db_service = CosmosDBService()
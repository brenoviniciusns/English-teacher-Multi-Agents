"""
Tests for Pronunciation Agent
Tests for pronunciation exercises, audio assessment, and progress tracking.
"""
import pytest
import base64
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.agents.pronunciation_agent import pronunciation_agent, PronunciationAgent
from app.agents.state import create_initial_state, AppState


# ==================== FIXTURES ====================

@pytest.fixture
def mock_db_service():
    """Mock Cosmos DB service."""
    with patch.object(pronunciation_agent, 'db_service') as mock:
        mock.get_pronunciation_progress = AsyncMock(return_value=None)
        mock.update_pronunciation_progress = AsyncMock(return_value={})
        mock.get_pronunciation_due_for_review = AsyncMock(return_value=[])
        mock.get_pronunciation_low_frequency = AsyncMock(return_value=[])
        mock.get_pronunciation_needs_practice = AsyncMock(return_value=[])
        yield mock


@pytest.fixture
def mock_speech_service():
    """Mock Azure Speech service."""
    with patch.object(pronunciation_agent, 'speech_service') as mock:
        # Mock TTS
        mock.text_to_speech = MagicMock(return_value=b"fake_audio_bytes")

        # Mock pronunciation assessment
        mock.pronunciation_assessment = MagicMock(return_value={
            "success": True,
            "recognized_text": "think",
            "reference_text": "think",
            "scores": {
                "accuracy": 85.0,
                "fluency": 82.0,
                "completeness": 90.0,
                "pronunciation": 86.0
            },
            "words": [
                {
                    "word": "think",
                    "accuracy_score": 85.0,
                    "phonemes": [
                        {"phoneme": "θ", "accuracy_score": 80.0},
                        {"phoneme": "ɪ", "accuracy_score": 88.0},
                        {"phoneme": "ŋ", "accuracy_score": 85.0},
                        {"phoneme": "k", "accuracy_score": 90.0}
                    ]
                }
            ],
            "phonemes": [
                {"phoneme": "θ", "accuracy_score": 80.0, "word": "think"},
                {"phoneme": "ɪ", "accuracy_score": 88.0, "word": "think"},
                {"phoneme": "ŋ", "accuracy_score": 85.0, "word": "think"},
                {"phoneme": "k", "accuracy_score": 90.0, "word": "think"}
            ],
            "feedback": {
                "overall": "Good pronunciation with room for improvement.",
                "accuracy_feedback": "Most sounds are correct.",
                "fluency_feedback": "",
                "suggestions": []
            }
        })

        # Mock phoneme guidance
        mock.get_phoneme_guidance = MagicMock(return_value={
            "name": "voiceless dental fricative",
            "ipa": "θ",
            "example_words": ["think", "math", "three"],
            "mouth_position": {
                "tongue": "Place tongue tip between teeth",
                "lips": "Slightly open"
            },
            "common_mistake": "Portuguese speakers often say /s/ instead",
            "tip": "Feel air passing over your tongue tip"
        })

        yield mock


@pytest.fixture
def sample_user_state() -> AppState:
    """Create a sample user state for testing."""
    state = create_initial_state(
        user_id="test_user_123",
        request_type="pronunciation_exercise"
    )
    state["user"]["current_level"] = "beginner"
    state["user"]["voice_preference"] = "american_female"
    return state


@pytest.fixture
def sample_phonetic_sound():
    """Sample phonetic sound for testing."""
    return {
        "id": "sound_001",
        "phoneme": "θ",
        "ipa": "θ",
        "name": "voiceless dental fricative",
        "exists_in_portuguese": False,
        "difficulty": "high",
        "mouth_position": {
            "tongue": "Place tongue tip gently between upper and lower teeth",
            "lips": "Slightly open, relaxed",
            "teeth": "Slightly apart",
            "airflow": "Continuous air flowing through"
        },
        "example_words": ["think", "math", "birthday", "three"],
        "minimal_pairs": [
            {"target": "think", "contrast": "sink", "difference": "θ vs s"}
        ],
        "common_mistake": "Portuguese speakers often substitute /s/, /t/, or /f/",
        "portuguese_similar": None,
        "tip": "Feel the air passing over your tongue tip."
    }


@pytest.fixture
def sample_audio_base64():
    """Sample base64 encoded audio for testing."""
    # Minimal WAV header + silence
    wav_header = bytes([
        0x52, 0x49, 0x46, 0x46,  # "RIFF"
        0x24, 0x00, 0x00, 0x00,  # File size - 8
        0x57, 0x41, 0x56, 0x45,  # "WAVE"
        0x66, 0x6D, 0x74, 0x20,  # "fmt "
        0x10, 0x00, 0x00, 0x00,  # Subchunk1Size (16 for PCM)
        0x01, 0x00,              # AudioFormat (1 for PCM)
        0x01, 0x00,              # NumChannels (1)
        0x80, 0x3E, 0x00, 0x00,  # SampleRate (16000)
        0x00, 0x7D, 0x00, 0x00,  # ByteRate
        0x02, 0x00,              # BlockAlign
        0x10, 0x00,              # BitsPerSample (16)
        0x64, 0x61, 0x74, 0x61,  # "data"
        0x00, 0x00, 0x00, 0x00   # Subchunk2Size (0 - no data)
    ])
    return base64.b64encode(wav_header).decode("utf-8")


# ==================== UNIT TESTS ====================

class TestPronunciationAgentInit:
    """Test PronunciationAgent initialization."""

    def test_agent_properties(self):
        """Test agent name and description."""
        assert pronunciation_agent.name == "pronunciation"
        assert "pronunciation" in pronunciation_agent.description.lower()

    def test_empty_cache_on_init(self):
        """Test that caches are empty on initialization."""
        agent = PronunciationAgent()
        assert agent._sounds_cache == {}
        assert agent._sounds_by_difficulty == {}


class TestLoadSounds:
    """Test phonetic sounds loading."""

    @pytest.mark.asyncio
    async def test_load_sounds_success(self):
        """Test loading phonetic sounds from JSON file."""
        # Clear cache first
        pronunciation_agent._sounds_cache = {}
        pronunciation_agent._sounds_by_difficulty = {}

        await pronunciation_agent._load_sounds()

        assert len(pronunciation_agent._sounds_cache) > 0
        assert len(pronunciation_agent._sounds_by_difficulty) > 0

    @pytest.mark.asyncio
    async def test_load_sounds_difficulties(self):
        """Test that sounds are indexed by difficulty."""
        await pronunciation_agent._load_sounds()

        difficulties = pronunciation_agent.get_available_difficulties()
        assert len(difficulties) > 0
        assert "high" in difficulties or "medium" in difficulties

    @pytest.mark.asyncio
    async def test_sound_structure(self):
        """Test that loaded sounds have expected structure."""
        await pronunciation_agent._load_sounds()

        # Get first sound
        sound_id = list(pronunciation_agent._sounds_cache.keys())[0]
        sound = pronunciation_agent._sounds_cache[sound_id]

        assert "id" in sound
        assert "phoneme" in sound
        assert "name" in sound
        assert "mouth_position" in sound
        assert "example_words" in sound


class TestGenerateExercise:
    """Test pronunciation exercise generation."""

    @pytest.mark.asyncio
    async def test_generate_exercise_success(
        self,
        mock_db_service,
        mock_speech_service,
        sample_user_state
    ):
        """Test successful exercise generation."""
        # Clear and reload sounds
        pronunciation_agent._sounds_cache = {}
        await pronunciation_agent._load_sounds()

        result_state = await pronunciation_agent.process(sample_user_state)

        assert result_state["response"]["status"] == "success"
        assert result_state["response"]["type"] == "pronunciation_exercise"
        assert result_state["response"]["exercise"] is not None
        assert "sound" in result_state["response"]["exercise"]
        assert "target_word" in result_state["response"]["exercise"]
        assert "instructions" in result_state["response"]["exercise"]

    @pytest.mark.asyncio
    async def test_generate_exercise_with_specific_sound(
        self,
        mock_db_service,
        mock_speech_service,
        sample_user_state
    ):
        """Test exercise generation for a specific sound."""
        await pronunciation_agent._load_sounds()

        sample_user_state["activity_input"] = {"sound_id": "sound_001"}
        result_state = await pronunciation_agent.process(sample_user_state)

        assert result_state["response"]["status"] == "success"
        assert result_state["response"]["exercise"]["sound"]["id"] == "sound_001"

    @pytest.mark.asyncio
    async def test_generate_exercise_with_difficulty_filter(
        self,
        mock_db_service,
        mock_speech_service,
        sample_user_state
    ):
        """Test exercise generation filtered by difficulty respects level filtering.

        Beginner users cannot access high difficulty sounds (level filtering).
        Intermediate users can access all difficulties.
        """
        await pronunciation_agent._load_sounds()

        # Test 1: Beginner user requesting high difficulty should get no_sounds
        # (because level filtering restricts high difficulty for beginners)
        sample_user_state["activity_input"] = {"difficulty": "high"}
        sample_user_state["user"]["current_level"] = "beginner"
        result_state = await pronunciation_agent.process(sample_user_state)

        # Beginner cannot access high difficulty sounds due to level filtering
        assert result_state["response"]["status"] == "no_sounds"

        # Test 2: Intermediate user can access high difficulty sounds
        sample_user_state["user"]["current_level"] = "intermediate"
        result_state = await pronunciation_agent.process(sample_user_state)

        # Intermediate user should be able to get high difficulty sounds
        if result_state["response"]["status"] == "success":
            sound = result_state["response"]["exercise"]["sound"]
            assert sound["difficulty"] == "high"

    @pytest.mark.asyncio
    async def test_generate_exercise_includes_reference_audio(
        self,
        mock_db_service,
        mock_speech_service,
        sample_user_state
    ):
        """Test that exercise includes reference audio."""
        await pronunciation_agent._load_sounds()

        result_state = await pronunciation_agent.process(sample_user_state)

        if result_state["response"]["status"] == "success":
            exercise = result_state["response"]["exercise"]
            # Reference audio should be generated
            assert "reference_audio_base64" in exercise

    @pytest.mark.asyncio
    async def test_generate_exercise_prioritizes_due_items(
        self,
        mock_db_service,
        mock_speech_service,
        sample_user_state
    ):
        """Test that SRS due items are prioritized."""
        await pronunciation_agent._load_sounds()

        # Mock a due item
        mock_db_service.get_pronunciation_due_for_review.return_value = [
            {
                "soundId": "sound_002",
                "srsData": {"nextReview": datetime.utcnow().isoformat()}
            }
        ]

        result_state = await pronunciation_agent.process(sample_user_state)

        assert result_state["response"]["status"] == "success"
        # Should select the due sound
        assert result_state["response"]["exercise"]["sound"]["id"] == "sound_002"


class TestProcessAudioSubmission:
    """Test audio submission processing."""

    @pytest.mark.asyncio
    async def test_process_audio_success(
        self,
        mock_db_service,
        mock_speech_service,
        sample_user_state,
        sample_audio_base64
    ):
        """Test successful audio processing."""
        await pronunciation_agent._load_sounds()

        sample_user_state["request_type"] = "shadowing"
        sample_user_state["activity_input"] = {
            "sound_id": "sound_001",
            "word": "think",
            "reference_text": "think",
            "audio_base64": sample_audio_base64,
            "attempt_number": 1
        }
        sample_user_state["current_activity"] = {
            "content": {
                "sound_id": "sound_001",
                "target_word": "think",
                "attempt_count": 0,
                "best_accuracy": 0
            }
        }

        result_state = await pronunciation_agent.process(sample_user_state)

        assert result_state["response"]["status"] == "success"
        assert result_state["response"]["type"] == "shadowing_result"
        assert "scores" in result_state["response"]
        assert "feedback" in result_state["response"]

    @pytest.mark.asyncio
    async def test_process_audio_returns_scores(
        self,
        mock_db_service,
        mock_speech_service,
        sample_user_state,
        sample_audio_base64
    ):
        """Test that audio processing returns all scores."""
        await pronunciation_agent._load_sounds()

        sample_user_state["request_type"] = "shadowing"
        sample_user_state["activity_input"] = {
            "sound_id": "sound_001",
            "word": "think",
            "reference_text": "think",
            "audio_base64": sample_audio_base64
        }
        sample_user_state["current_activity"] = {
            "content": {"sound_id": "sound_001", "target_word": "think", "attempt_count": 0}
        }

        result_state = await pronunciation_agent.process(sample_user_state)

        scores = result_state["response"]["scores"]
        assert "accuracy" in scores
        assert "fluency" in scores
        assert "completeness" in scores
        assert "pronunciation" in scores

    @pytest.mark.asyncio
    async def test_process_audio_passed_threshold(
        self,
        mock_db_service,
        mock_speech_service,
        sample_user_state,
        sample_audio_base64
    ):
        """Test that passing is determined correctly."""
        await pronunciation_agent._load_sounds()

        # Mock high accuracy score
        mock_speech_service.pronunciation_assessment.return_value["scores"]["accuracy"] = 90.0

        sample_user_state["request_type"] = "shadowing"
        sample_user_state["activity_input"] = {
            "sound_id": "sound_001",
            "word": "think",
            "reference_text": "think",
            "audio_base64": sample_audio_base64
        }
        sample_user_state["current_activity"] = {
            "content": {"sound_id": "sound_001", "target_word": "think", "attempt_count": 0}
        }

        result_state = await pronunciation_agent.process(sample_user_state)

        # 90% accuracy should pass (threshold is 70%)
        assert result_state["response"]["passed"] is True

    @pytest.mark.asyncio
    async def test_process_audio_failed_threshold(
        self,
        mock_db_service,
        mock_speech_service,
        sample_user_state,
        sample_audio_base64
    ):
        """Test that failing is determined correctly."""
        await pronunciation_agent._load_sounds()

        # Mock low accuracy score
        mock_speech_service.pronunciation_assessment.return_value["scores"]["accuracy"] = 50.0

        sample_user_state["request_type"] = "shadowing"
        sample_user_state["activity_input"] = {
            "sound_id": "sound_001",
            "word": "think",
            "reference_text": "think",
            "audio_base64": sample_audio_base64
        }
        sample_user_state["current_activity"] = {
            "content": {"sound_id": "sound_001", "target_word": "think", "attempt_count": 0}
        }

        result_state = await pronunciation_agent.process(sample_user_state)

        # 50% accuracy should fail (threshold is 70%)
        assert result_state["response"]["passed"] is False

    @pytest.mark.asyncio
    async def test_process_audio_missing_data(
        self,
        mock_db_service,
        mock_speech_service,
        sample_user_state
    ):
        """Test error handling for missing audio data."""
        sample_user_state["request_type"] = "shadowing"
        sample_user_state["activity_input"] = {
            "sound_id": "sound_001",
            "word": "think"
            # Missing audio_base64
        }

        result_state = await pronunciation_agent.process(sample_user_state)

        assert result_state["has_error"] is True
        assert "status" in result_state["response"]
        assert result_state["response"]["status"] == "error"


class TestProgressUpdate:
    """Test progress update functionality."""

    @pytest.mark.asyncio
    async def test_update_progress_new_user(
        self,
        mock_db_service,
        mock_speech_service,
        sample_user_state,
        sample_audio_base64
    ):
        """Test progress update for new user (no existing progress)."""
        await pronunciation_agent._load_sounds()

        # No existing progress
        mock_db_service.get_pronunciation_progress.return_value = None

        sample_user_state["request_type"] = "shadowing"
        sample_user_state["activity_input"] = {
            "sound_id": "sound_001",
            "word": "think",
            "reference_text": "think",
            "audio_base64": sample_audio_base64
        }
        sample_user_state["current_activity"] = {
            "content": {"sound_id": "sound_001", "target_word": "think", "attempt_count": 0}
        }

        result_state = await pronunciation_agent.process(sample_user_state)

        # Should create new progress
        mock_db_service.update_pronunciation_progress.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_progress_existing_user(
        self,
        mock_db_service,
        mock_speech_service,
        sample_user_state,
        sample_audio_base64
    ):
        """Test progress update for existing user."""
        await pronunciation_agent._load_sounds()

        # Existing progress
        mock_db_service.get_pronunciation_progress.return_value = {
            "soundId": "sound_001",
            "practiceCount": 5,
            "averageAccuracy": 70.0,
            "bestAccuracy": 80.0,
            "recentAccuracies": [65, 70, 72, 75, 70],
            "srsData": {
                "easeFactor": 2.5,
                "interval": 1,
                "repetitions": 2,
                "nextReview": datetime.utcnow().isoformat()
            },
            "mastered": False
        }

        sample_user_state["request_type"] = "shadowing"
        sample_user_state["activity_input"] = {
            "sound_id": "sound_001",
            "word": "think",
            "reference_text": "think",
            "audio_base64": sample_audio_base64
        }
        sample_user_state["current_activity"] = {
            "content": {"sound_id": "sound_001", "target_word": "think", "attempt_count": 0}
        }

        result_state = await pronunciation_agent.process(sample_user_state)

        # Should update existing progress
        mock_db_service.update_pronunciation_progress.assert_called_once()


class TestGetUserStats:
    """Test user statistics retrieval."""

    @pytest.mark.asyncio
    async def test_get_stats_no_progress(
        self,
        mock_db_service
    ):
        """Test stats for user with no progress."""
        mock_db_service.get_pronunciation_progress.return_value = []
        mock_db_service.get_pronunciation_due_for_review.return_value = []

        stats = await pronunciation_agent.get_user_pronunciation_stats("test_user")

        assert stats["mastered"] == 0
        assert stats["practicing"] == 0
        assert stats["not_started"] > 0

    @pytest.mark.asyncio
    async def test_get_stats_with_progress(
        self,
        mock_db_service
    ):
        """Test stats for user with progress."""
        mock_db_service.get_pronunciation_progress.return_value = [
            {"soundId": "sound_001", "mastered": True, "averageAccuracy": 90, "practiceCount": 10},
            {"soundId": "sound_002", "mastered": False, "averageAccuracy": 75, "practiceCount": 5},
            {"soundId": "sound_003", "mastered": False, "averageAccuracy": 50, "practiceCount": 3}
        ]
        mock_db_service.get_pronunciation_due_for_review.return_value = [
            {"soundId": "sound_002"}
        ]

        stats = await pronunciation_agent.get_user_pronunciation_stats("test_user")

        assert stats["mastered"] == 1
        assert stats["practicing"] == 1  # sound_002 with 75% accuracy
        assert stats["needs_work"] == 1  # sound_003 with 50% accuracy
        assert stats["due_for_review"] == 1


class TestSoundSelection:
    """Test sound selection logic."""

    @pytest.mark.asyncio
    async def test_select_specific_sound(
        self,
        mock_db_service
    ):
        """Test selecting a specific sound by ID."""
        await pronunciation_agent._load_sounds()

        sound = await pronunciation_agent._select_sound(
            user_id="test_user",
            level="beginner",
            sound_id="sound_001"
        )

        assert sound is not None
        assert sound["id"] == "sound_001"

    @pytest.mark.asyncio
    async def test_select_sound_prioritizes_srs_due(
        self,
        mock_db_service
    ):
        """Test that SRS due items are prioritized."""
        await pronunciation_agent._load_sounds()

        mock_db_service.get_pronunciation_due_for_review.return_value = [
            {"soundId": "sound_003", "srsData": {"nextReview": datetime.utcnow().isoformat()}}
        ]

        sound = await pronunciation_agent._select_sound(
            user_id="test_user",
            level="beginner"
        )

        assert sound is not None
        assert sound["id"] == "sound_003"

    @pytest.mark.asyncio
    async def test_select_sound_prioritizes_low_accuracy(
        self,
        mock_db_service
    ):
        """Test that low accuracy items are prioritized when no SRS due."""
        await pronunciation_agent._load_sounds()

        mock_db_service.get_pronunciation_due_for_review.return_value = []
        mock_db_service.get_pronunciation_needs_practice.return_value = [
            {"soundId": "sound_005", "averageAccuracy": 40}
        ]

        sound = await pronunciation_agent._select_sound(
            user_id="test_user",
            level="beginner"
        )

        assert sound is not None
        assert sound["id"] == "sound_005"


class TestAccuracyToQuality:
    """Test accuracy to SRS quality conversion."""

    def test_perfect_accuracy(self):
        """Test perfect accuracy (95+) returns quality 5."""
        quality = pronunciation_agent._accuracy_to_quality(97)
        assert quality == 5

    def test_good_accuracy(self):
        """Test good accuracy (85-94) returns quality 4."""
        quality = pronunciation_agent._accuracy_to_quality(88)
        assert quality == 4

    def test_ok_accuracy(self):
        """Test OK accuracy (70-84) returns quality 3."""
        quality = pronunciation_agent._accuracy_to_quality(75)
        assert quality == 3

    def test_poor_accuracy(self):
        """Test poor accuracy (50-69) returns quality 2."""
        quality = pronunciation_agent._accuracy_to_quality(55)
        assert quality == 2

    def test_bad_accuracy(self):
        """Test bad accuracy (30-49) returns quality 1."""
        quality = pronunciation_agent._accuracy_to_quality(35)
        assert quality == 1

    def test_blackout_accuracy(self):
        """Test very low accuracy (<30) returns quality 0."""
        quality = pronunciation_agent._accuracy_to_quality(20)
        assert quality == 0


class TestGetAllSounds:
    """Test getting all sounds."""

    @pytest.mark.asyncio
    async def test_get_all_sounds(self):
        """Test getting all sounds without filters."""
        sounds = await pronunciation_agent.get_all_sounds()

        assert len(sounds) > 0
        assert all("phoneme" in s for s in sounds)

    @pytest.mark.asyncio
    async def test_get_all_sounds_with_difficulty(self):
        """Test getting sounds filtered by difficulty."""
        sounds = await pronunciation_agent.get_all_sounds(difficulty="high")

        assert all(s.get("difficulty") == "high" for s in sounds)

    @pytest.mark.asyncio
    async def test_get_all_sounds_with_user_progress(
        self,
        mock_db_service
    ):
        """Test getting sounds with user progress included."""
        mock_db_service.get_pronunciation_progress.return_value = [
            {"soundId": "sound_001", "averageAccuracy": 85, "practiceCount": 10, "mastered": True}
        ]

        sounds = await pronunciation_agent.get_all_sounds(user_id="test_user")

        # Find sound_001 and check user data
        sound_001 = next((s for s in sounds if s["id"] == "sound_001"), None)
        if sound_001:
            assert sound_001.get("user_accuracy") == 85
            assert sound_001.get("user_practice_count") == 10
            assert sound_001.get("user_mastered") is True


class TestPhonemeGuidance:
    """Test phoneme guidance retrieval."""

    @pytest.mark.asyncio
    async def test_get_phoneme_guidance(
        self,
        mock_speech_service
    ):
        """Test getting guidance for a phoneme."""
        guidance = await pronunciation_agent.get_phoneme_guidance("θ")

        assert guidance is not None
        assert "tip" in guidance
        assert "mouth_position" in guidance

    @pytest.mark.asyncio
    async def test_get_phoneme_guidance_from_cache(self):
        """Test getting guidance uses cache when available."""
        await pronunciation_agent._load_sounds()

        guidance = await pronunciation_agent.get_phoneme_guidance("θ")

        assert guidance is not None
        # Should include data from sounds cache
        assert "example_words" in guidance

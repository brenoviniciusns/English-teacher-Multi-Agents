"""
Azure Speech Service
Provides Text-to-Speech, Speech-to-Text, and Pronunciation Assessment.
IMPORTANT: Speech-to-Text is configured WITHOUT filters for accurate pronunciation validation.
"""
import logging
import base64
from typing import Optional
import azure.cognitiveservices.speech as speechsdk

from app.config import settings

logger = logging.getLogger(__name__)


class AzureSpeechService:
    """Service for Azure Speech Services (TTS, STT, Pronunciation Assessment)"""

    def __init__(self):
        self.speech_config = speechsdk.SpeechConfig(
            subscription=settings.AZURE_SPEECH_KEY,
            region=settings.AZURE_SPEECH_REGION
        )
        # Set recognition language to American English
        self.speech_config.speech_recognition_language = settings.AZURE_SPEECH_LANGUAGE

        # Available voices for TTS
        self.voices = {
            "american_female": settings.AZURE_SPEECH_VOICE_AMERICAN,
            "american_male": settings.AZURE_SPEECH_VOICE_AMERICAN_MALE,
            "british_female": settings.AZURE_SPEECH_VOICE_BRITISH,
            "british_male": settings.AZURE_SPEECH_VOICE_BRITISH_MALE
        }

    def text_to_speech(
        self,
        text: str,
        voice: str = "american_female",
        output_format: str = "wav"
    ) -> bytes:
        """
        Convert text to speech audio.

        Args:
            text: Text to synthesize
            voice: Voice to use (american_female, american_male, british_female, british_male)
            output_format: Audio format (wav, mp3)

        Returns:
            Audio data as bytes
        """
        try:
            # Set voice
            voice_name = self.voices.get(voice, self.voices["american_female"])
            self.speech_config.speech_synthesis_voice_name = voice_name

            # Set output format
            if output_format == "mp3":
                self.speech_config.set_speech_synthesis_output_format(
                    speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
                )
            else:
                self.speech_config.set_speech_synthesis_output_format(
                    speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
                )

            # Create synthesizer with no audio output (we want the data)
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self.speech_config,
                audio_config=None
            )

            # Synthesize
            result = synthesizer.speak_text_async(text).get()

            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                logger.info(f"TTS completed for text: {text[:50]}...")
                return result.audio_data
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation = result.cancellation_details
                logger.error(f"TTS canceled: {cancellation.reason}")
                if cancellation.reason == speechsdk.CancellationReason.Error:
                    logger.error(f"TTS error: {cancellation.error_details}")
                raise Exception(f"TTS failed: {cancellation.error_details}")
            else:
                raise Exception(f"TTS unexpected result: {result.reason}")

        except Exception as e:
            logger.error(f"TTS error: {e}")
            raise

    def speech_to_text_from_bytes(
        self,
        audio_data: bytes,
        language: str = "en-US"
    ) -> dict:
        """
        Convert speech audio to text WITHOUT filters.
        IMPORTANT: This returns raw recognition without auto-correction
        for accurate pronunciation validation.

        Args:
            audio_data: Audio data as bytes (WAV format)
            language: Recognition language

        Returns:
            Dict with recognized text and confidence
        """
        try:
            # Create push stream for audio data
            stream = speechsdk.audio.PushAudioInputStream()
            audio_config = speechsdk.audio.AudioConfig(stream=stream)

            # Configure for raw recognition (no filters)
            self.speech_config.speech_recognition_language = language
            # Disable profanity filter for accurate recognition
            self.speech_config.set_profanity(speechsdk.ProfanityOption.Raw)

            # Create recognizer
            recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )

            # Push audio data
            stream.write(audio_data)
            stream.close()

            # Recognize
            result = recognizer.recognize_once_async().get()

            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                return {
                    "success": True,
                    "text": result.text,
                    "confidence": 1.0,  # Azure doesn't provide confidence in basic recognition
                    "raw_result": True
                }
            elif result.reason == speechsdk.ResultReason.NoMatch:
                return {
                    "success": False,
                    "text": "",
                    "error": "No speech recognized",
                    "details": str(result.no_match_details)
                }
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation = result.cancellation_details
                return {
                    "success": False,
                    "text": "",
                    "error": "Recognition canceled",
                    "details": cancellation.error_details
                }
            else:
                return {
                    "success": False,
                    "text": "",
                    "error": f"Unexpected result: {result.reason}"
                }

        except Exception as e:
            logger.error(f"STT error: {e}")
            return {
                "success": False,
                "text": "",
                "error": str(e)
            }

    def pronunciation_assessment(
        self,
        audio_data: bytes,
        reference_text: str,
        language: str = "en-US",
        granularity: str = "phoneme"
    ) -> dict:
        """
        Assess pronunciation accuracy against a reference text.
        Provides detailed phoneme-level feedback.

        Args:
            audio_data: Audio data as bytes (WAV format)
            reference_text: The expected text for comparison
            language: Assessment language
            granularity: "phoneme" for detailed, "word" for word-level

        Returns:
            Dict with pronunciation scores and detailed feedback
        """
        try:
            # Create push stream for audio data
            stream = speechsdk.audio.PushAudioInputStream()
            audio_config = speechsdk.audio.AudioConfig(stream=stream)

            # Configure pronunciation assessment
            pronunciation_config = speechsdk.PronunciationAssessmentConfig(
                reference_text=reference_text,
                grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
                granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme if granularity == "phoneme"
                else speechsdk.PronunciationAssessmentGranularity.Word,
                enable_miscue=True  # Detect insertions, omissions, etc.
            )

            # Enable prosody assessment for intermediate level
            pronunciation_config.enable_prosody_assessment()

            # Create recognizer
            self.speech_config.speech_recognition_language = language
            recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )

            # Apply pronunciation assessment config
            pronunciation_config.apply_to(recognizer)

            # Push audio data
            stream.write(audio_data)
            stream.close()

            # Recognize with assessment
            result = recognizer.recognize_once_async().get()

            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                # Get pronunciation assessment result
                pronunciation_result = speechsdk.PronunciationAssessmentResult(result)

                # Build detailed response
                response = {
                    "success": True,
                    "recognized_text": result.text,
                    "reference_text": reference_text,
                    "scores": {
                        "accuracy": pronunciation_result.accuracy_score,
                        "fluency": pronunciation_result.fluency_score,
                        "completeness": pronunciation_result.completeness_score,
                        "pronunciation": pronunciation_result.pronunciation_score
                    },
                    "words": [],
                    "phonemes": []
                }

                # Get word-level details
                for word in pronunciation_result.words:
                    word_detail = {
                        "word": word.word,
                        "accuracy_score": word.accuracy_score,
                        "error_type": word.error_type if hasattr(word, 'error_type') else "None"
                    }

                    # Get phoneme-level details if available
                    if hasattr(word, 'phonemes') and granularity == "phoneme":
                        word_detail["phonemes"] = []
                        for phoneme in word.phonemes:
                            word_detail["phonemes"].append({
                                "phoneme": phoneme.phoneme,
                                "accuracy_score": phoneme.accuracy_score
                            })
                            response["phonemes"].append({
                                "phoneme": phoneme.phoneme,
                                "accuracy_score": phoneme.accuracy_score,
                                "word": word.word
                            })

                    response["words"].append(word_detail)

                # Add feedback based on scores
                response["feedback"] = self._generate_pronunciation_feedback(response["scores"])

                return response

            elif result.reason == speechsdk.ResultReason.NoMatch:
                return {
                    "success": False,
                    "error": "No speech recognized",
                    "suggestion": "Please speak more clearly and closer to the microphone"
                }
            else:
                return {
                    "success": False,
                    "error": f"Recognition failed: {result.reason}"
                }

        except Exception as e:
            logger.error(f"Pronunciation assessment error: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _generate_pronunciation_feedback(self, scores: dict) -> dict:
        """Generate human-readable feedback based on pronunciation scores."""
        feedback = {
            "overall": "",
            "accuracy_feedback": "",
            "fluency_feedback": "",
            "suggestions": []
        }

        # Overall feedback
        avg_score = (scores["accuracy"] + scores["fluency"] + scores["pronunciation"]) / 3
        if avg_score >= 85:
            feedback["overall"] = "Excellent pronunciation! Keep up the great work."
        elif avg_score >= 70:
            feedback["overall"] = "Good pronunciation with room for improvement."
        elif avg_score >= 50:
            feedback["overall"] = "Fair pronunciation. Focus on the specific sounds highlighted below."
        else:
            feedback["overall"] = "Needs practice. Listen to the reference audio carefully and try again."

        # Accuracy feedback
        if scores["accuracy"] < 70:
            feedback["accuracy_feedback"] = "Focus on pronouncing each sound correctly."
            feedback["suggestions"].append("Practice individual phonemes that scored low")
        elif scores["accuracy"] < 85:
            feedback["accuracy_feedback"] = "Most sounds are correct, but some need refinement."

        # Fluency feedback
        if scores["fluency"] < 70:
            feedback["fluency_feedback"] = "Try to speak more smoothly without long pauses."
            feedback["suggestions"].append("Practice speaking the phrase multiple times")
        elif scores["fluency"] < 85:
            feedback["fluency_feedback"] = "Good flow, but could be more natural."

        return feedback

    def get_phoneme_guidance(self, phoneme: str) -> dict:
        """
        Get guidance for pronouncing a specific phoneme.
        Useful for sounds that don't exist in Portuguese.

        Args:
            phoneme: IPA phoneme symbol (e.g., "θ", "ð")

        Returns:
            Dict with mouth position and tips
        """
        # Common problematic phonemes for Portuguese speakers
        phoneme_guides = {
            "θ": {
                "name": "voiceless dental fricative",
                "ipa": "θ",
                "example_words": ["think", "math", "birthday", "three"],
                "mouth_position": {
                    "tongue": "Place tongue tip between upper and lower teeth",
                    "lips": "Slightly open, relaxed",
                    "teeth": "Slightly apart",
                    "airflow": "Blow air continuously through teeth"
                },
                "common_mistake": "Portuguese speakers often say /s/ or /t/ instead",
                "tip": "Feel the air passing over your tongue tip between your teeth"
            },
            "ð": {
                "name": "voiced dental fricative",
                "ipa": "ð",
                "example_words": ["this", "that", "mother", "brother"],
                "mouth_position": {
                    "tongue": "Place tongue tip between upper and lower teeth",
                    "lips": "Slightly open, relaxed",
                    "teeth": "Slightly apart",
                    "airflow": "Blow air while vibrating vocal cords"
                },
                "common_mistake": "Portuguese speakers often say /d/ or /z/ instead",
                "tip": "Same as /θ/ but add voice - feel your throat vibrate"
            },
            "æ": {
                "name": "near-open front unrounded vowel",
                "ipa": "æ",
                "example_words": ["cat", "bad", "man", "have"],
                "mouth_position": {
                    "tongue": "Low and front",
                    "lips": "Spread slightly",
                    "jaw": "Open wide"
                },
                "common_mistake": "Portuguese speakers often say /ɛ/ (like 'bed') instead",
                "tip": "Open your mouth wider than for Portuguese 'é'"
            },
            "ɪ": {
                "name": "near-close front unrounded vowel",
                "ipa": "ɪ",
                "example_words": ["bit", "sit", "fish", "quick"],
                "mouth_position": {
                    "tongue": "High and front, but relaxed",
                    "lips": "Slightly spread"
                },
                "common_mistake": "Portuguese speakers often use /i/ (like 'see') instead",
                "tip": "Shorter and more relaxed than Portuguese 'i'"
            },
            "ʊ": {
                "name": "near-close back rounded vowel",
                "ipa": "ʊ",
                "example_words": ["book", "good", "put", "could"],
                "mouth_position": {
                    "tongue": "High and back, but relaxed",
                    "lips": "Slightly rounded"
                },
                "common_mistake": "Portuguese speakers often use /u/ (like 'food') instead",
                "tip": "Shorter and more relaxed than Portuguese 'u'"
            },
            "ɹ": {
                "name": "alveolar approximant (American R)",
                "ipa": "ɹ",
                "example_words": ["red", "right", "car", "water"],
                "mouth_position": {
                    "tongue": "Curl back slightly, not touching roof of mouth",
                    "lips": "Slightly rounded"
                },
                "common_mistake": "Portuguese speakers may use rolled R or tap R",
                "tip": "The tongue never touches the roof of the mouth"
            },
            "ŋ": {
                "name": "velar nasal",
                "ipa": "ŋ",
                "example_words": ["sing", "thing", "going", "running"],
                "mouth_position": {
                    "tongue": "Back of tongue touches soft palate",
                    "airflow": "Through the nose"
                },
                "common_mistake": "Adding /g/ sound after (saying 'sing-g' instead of 'sing')",
                "tip": "Like the 'nh' sound but further back in the mouth"
            }
        }

        return phoneme_guides.get(phoneme, {
            "name": "Unknown phoneme",
            "tip": "Consult a pronunciation guide for this sound"
        })


# Singleton instance
azure_speech_service = AzureSpeechService()
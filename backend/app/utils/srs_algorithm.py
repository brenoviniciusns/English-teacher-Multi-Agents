"""
Spaced Repetition System (SRS) Algorithm
Implementation of the SM-2 algorithm with modifications for language learning.

The SM-2 algorithm calculates optimal review intervals based on:
- Quality of response (0-5 scale)
- Ease factor (difficulty multiplier)
- Number of successful repetitions

Quality Response Scale:
0 - Complete blackout, no recall
1 - Incorrect response, but upon seeing correct answer, it was remembered
2 - Incorrect response, but correct answer seemed easy to recall
3 - Correct response with serious difficulty
4 - Correct response after hesitation
5 - Perfect response with no hesitation
"""
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, Field

from app.config import settings


class SRSData(BaseModel):
    """SRS data structure"""
    ease_factor: float = Field(default=2.5, ge=1.3)
    interval: int = Field(default=1, ge=1)
    repetitions: int = Field(default=0, ge=0)
    next_review: datetime = Field(default_factory=datetime.utcnow)
    last_review: Optional[datetime] = None


class SRSResult(BaseModel):
    """Result of SRS calculation"""
    ease_factor: float
    interval: int
    repetitions: int
    next_review: datetime
    quality_response: int
    is_correct: bool


class SRSAlgorithm:
    """
    SM-2 Spaced Repetition Algorithm

    The algorithm adjusts review intervals based on performance:
    - Correct answers increase interval
    - Incorrect answers reset to beginning
    - Ease factor adjusts based on difficulty

    Modified for language learning with:
    - Minimum ease factor of 1.3 (instead of standard 1.3)
    - Initial intervals: 1 day, 6 days, then calculated
    - Support for partial correctness (quality 3)
    """

    def __init__(self):
        self.initial_interval = settings.SRS_INITIAL_INTERVAL_DAYS
        self.second_interval = settings.SRS_SECOND_INTERVAL_DAYS
        self.initial_ease_factor = settings.SRS_INITIAL_EASE_FACTOR
        self.min_ease_factor = settings.SRS_MIN_EASE_FACTOR

    def calculate(
        self,
        current_data: SRSData,
        quality_response: int
    ) -> SRSResult:
        """
        Calculate the next review based on SM-2 algorithm.

        Args:
            current_data: Current SRS data
            quality_response: Quality of response (0-5)

        Returns:
            SRSResult with updated SRS data
        """
        # Ensure quality is in valid range
        quality = max(0, min(5, quality_response))

        # Get current values
        ease_factor = current_data.ease_factor
        interval = current_data.interval
        repetitions = current_data.repetitions

        # Determine if response is correct (quality >= 3)
        is_correct = quality >= 3

        if is_correct:
            # Correct response - increase interval
            if repetitions == 0:
                interval = self.initial_interval
            elif repetitions == 1:
                interval = self.second_interval
            else:
                interval = round(interval * ease_factor)

            repetitions += 1

            # Update ease factor based on quality
            # EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
            ease_factor = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))

            # Ensure minimum ease factor
            ease_factor = max(self.min_ease_factor, ease_factor)

        else:
            # Incorrect response - reset
            repetitions = 0
            interval = self.initial_interval
            # Don't change ease factor on incorrect (some implementations do)

        # Calculate next review date
        next_review = datetime.utcnow() + timedelta(days=interval)

        return SRSResult(
            ease_factor=round(ease_factor, 2),
            interval=interval,
            repetitions=repetitions,
            next_review=next_review,
            quality_response=quality,
            is_correct=is_correct
        )

    def quality_from_accuracy(self, accuracy: float) -> int:
        """
        Convert accuracy percentage to quality response (0-5).

        Args:
            accuracy: Accuracy percentage (0-100)

        Returns:
            Quality response (0-5)
        """
        if accuracy >= 95:
            return 5  # Perfect
        elif accuracy >= 85:
            return 4  # Correct with hesitation
        elif accuracy >= 70:
            return 3  # Correct with difficulty
        elif accuracy >= 50:
            return 2  # Incorrect but seemed easy
        elif accuracy >= 25:
            return 1  # Incorrect but remembered after seeing
        else:
            return 0  # Complete blackout

    def quality_from_response_time(
        self,
        is_correct: bool,
        response_time_ms: int,
        expected_time_ms: int = 5000
    ) -> int:
        """
        Calculate quality based on correctness and response time.

        Args:
            is_correct: Whether the answer was correct
            response_time_ms: Time taken to respond
            expected_time_ms: Expected response time

        Returns:
            Quality response (0-5)
        """
        if not is_correct:
            return 2 if response_time_ms < expected_time_ms else 1

        # Correct answer - quality based on speed
        ratio = response_time_ms / expected_time_ms

        if ratio <= 0.5:
            return 5  # Very fast - perfect recall
        elif ratio <= 1.0:
            return 4  # Normal speed - good recall
        elif ratio <= 2.0:
            return 3  # Slow - some difficulty
        else:
            return 3  # Very slow but still correct

    def is_due_for_review(self, srs_data: SRSData) -> bool:
        """Check if an item is due for review."""
        return datetime.utcnow() >= srs_data.next_review

    def days_until_review(self, srs_data: SRSData) -> int:
        """Get days until next review (negative if overdue)."""
        delta = srs_data.next_review - datetime.utcnow()
        return delta.days

    def get_priority(self, srs_data: SRSData) -> str:
        """
        Get review priority based on how overdue the item is.

        Returns:
            'high' if very overdue, 'normal' if due, 'low' if not due yet
        """
        days = self.days_until_review(srs_data)

        if days < -7:
            return "high"  # Very overdue
        elif days <= 0:
            return "normal"  # Due now
        else:
            return "low"  # Not due yet


def calculate_next_review(
    current_data: dict,
    quality_response: int
) -> dict:
    """
    Convenience function to calculate next review.

    Args:
        current_data: Dict with ease_factor, interval, repetitions, next_review
        quality_response: Quality of response (0-5)

    Returns:
        Updated SRS data as dict
    """
    algorithm = SRSAlgorithm()

    srs_data = SRSData(
        ease_factor=current_data.get("easeFactor", 2.5),
        interval=current_data.get("interval", 1),
        repetitions=current_data.get("repetitions", 0),
        next_review=datetime.fromisoformat(current_data["nextReview"])
        if current_data.get("nextReview") else datetime.utcnow(),
        last_review=datetime.fromisoformat(current_data["lastReview"])
        if current_data.get("lastReview") else None
    )

    result = algorithm.calculate(srs_data, quality_response)

    return {
        "easeFactor": result.ease_factor,
        "interval": result.interval,
        "repetitions": result.repetitions,
        "nextReview": result.next_review.isoformat(),
        "lastReview": datetime.utcnow().isoformat()
    }


def should_review_low_frequency(
    last_practiced: Optional[datetime],
    threshold_days: int = 7
) -> bool:
    """
    Check if an item should be reviewed due to low frequency usage.

    Args:
        last_practiced: Last practice datetime
        threshold_days: Days threshold (default: 7)

    Returns:
        True if should be reviewed
    """
    if last_practiced is None:
        return True

    if isinstance(last_practiced, str):
        last_practiced = datetime.fromisoformat(last_practiced)

    days_since = (datetime.utcnow() - last_practiced).days
    return days_since >= threshold_days


# Singleton instance
srs_algorithm = SRSAlgorithm()
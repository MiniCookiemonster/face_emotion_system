from dataclasses import dataclass
from typing import List


@dataclass
class EmotionConfig:
    name: str
    default: float = 0.0
    minimum: float = 0.0
    maximum: float = 1.0
    step: float = 0.01


EMOTIONS: List[EmotionConfig] = [
    EmotionConfig("Happy", 0.20),
    EmotionConfig("Sad", 0.00),
    EmotionConfig("Angry", 0.00),
    EmotionConfig("Surprise", 0.10),
    EmotionConfig("Disgust", 0.00),
    EmotionConfig("Fear", 0.00),
]

FACE_REGIONS = [
    "Eyebrows",
    "Eyes",
    "Cheeks",
    "Mouth",
    "Jaw",
]
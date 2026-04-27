from typing import Dict, List, Tuple
from config import FACE_REGIONS


def maybe_normalize(values: Dict[str, float], normalize: bool) -> Dict[str, float]:
    if not normalize:
        return values.copy()

    total = sum(values.values())
    if total <= 1e-8:
        return values.copy()

    return {k: v / total for k, v in values.items()}


def compute_region_response(
    emotion_values: Dict[str, float],
    region_weights: Dict[str, float],
) -> Dict[str, float]:
    happy = emotion_values["Happy"]
    sad = emotion_values["Sad"]
    angry = emotion_values["Angry"]
    surprise = emotion_values["Surprise"]
    disgust = emotion_values["Disgust"]
    fear = emotion_values["Fear"]

    region_response = {
        "Eyebrows": max(0.0, 0.35 * angry + 0.25 * fear + 0.20 * sad + 0.15 * surprise),
        "Eyes": max(0.0, 0.30 * surprise + 0.25 * fear + 0.10 * sad + 0.10 * happy),
        "Cheeks": max(0.0, 0.35 * happy + 0.10 * disgust),
        "Mouth": max(0.0, 0.45 * happy + 0.25 * sad + 0.20 * disgust + 0.10 * surprise),
        "Jaw": max(0.0, 0.35 * surprise + 0.20 * fear + 0.15 * angry),
    }

    return {
        region: round(region_response[region] * region_weights[region], 4)
        for region in FACE_REGIONS
    }


def build_summary_table(
    emotion_values: Dict[str, float],
    region_response: Dict[str, float],
) -> List[Tuple[str, float]]:
    summary: List[Tuple[str, float]] = []
    for key, value in emotion_values.items():
        summary.append((f"Emotion / {key}", round(value, 4)))
    for key, value in region_response.items():
        summary.append((f"Region / {key}", round(value, 4)))
    return summary
from typing import Dict, List


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(value, max_value))


def deform_mesh(
    vertices: List[List[float]],
    emotion_values: Dict[str, float],
    region_weights: Dict[str, float],
) -> List[List[float]]:
    """
    保守版 3D 网格变形：
    - 仍然使用粗略区域
    - 但整体位移更小
    - 增加单顶点最大位移限制，避免脸部拉坏
    """
    if not vertices:
        return vertices

    happy = emotion_values.get("Happy", 0.0)
    sad = emotion_values.get("Sad", 0.0)
    angry = emotion_values.get("Angry", 0.0)
    surprise = emotion_values.get("Surprise", 0.0)
    disgust = emotion_values.get("Disgust", 0.0)
    fear = emotion_values.get("Fear", 0.0)

    mouth_weight = region_weights.get("Mouth", 1.0)
    jaw_weight = region_weights.get("Jaw", 1.0)
    eyes_weight = region_weights.get("Eyes", 1.0)
    brows_weight = region_weights.get("Eyebrows", 1.0)
    cheeks_weight = region_weights.get("Cheeks", 1.0)

    # 总体安全系数：先保守一点
    strength = 0.70

    new_vertices: List[List[float]] = []

    for vertex in vertices:
        x, y, z = vertex[0], vertex[1], vertex[2]

        dx, dy, dz = 0.0, 0.0, 0.0

        # 1. Mouth region
        if -0.45 <= x <= 0.45 and -0.45 <= y <= -0.05:
            center_factor = 1.0 - abs(x) / 0.45
            corner_factor = abs(x) / 0.45
            vertical_factor = (-y - 0.05) / 0.40
            vertical_factor = clamp(vertical_factor, 0.0, 1.0)

            happy_lift = happy * mouth_weight * (0.07 * corner_factor + 0.03 * center_factor)
            sad_drop = sad * mouth_weight * (0.07 * corner_factor + 0.025 * center_factor)
            open_amount = (surprise * 0.05 + fear * 0.025) * mouth_weight * vertical_factor

            disgust_offset = disgust * 0.010 * mouth_weight
            asymmetry = disgust_offset if x > 0 else -disgust_offset * 0.4

            dy += happy_lift
            dy -= sad_drop
            dy -= open_amount
            dy += asymmetry

            dz += (surprise * 0.010 + fear * 0.006) * mouth_weight * center_factor

        # 2. Jaw region
        if y < -0.35:
            jaw_factor = (-y - 0.35) / 0.65
            jaw_factor = clamp(jaw_factor, 0.0, 1.0)

            jaw_open = (surprise * 0.06 + fear * 0.03) * jaw_weight * jaw_factor
            sad_jaw = sad * 0.008 * jaw_weight * jaw_factor

            dy -= jaw_open
            dy -= sad_jaw

        # 3. Eyebrow region
        if -0.50 <= x <= 0.50 and 0.15 <= y <= 0.55:
            upper_factor = (y - 0.15) / 0.40
            upper_factor = clamp(upper_factor, 0.0, 1.0)
            center_factor = 1.0 - abs(x) / 0.50
            center_factor = clamp(center_factor, 0.0, 1.0)

            angry_drop = angry * 0.05 * brows_weight * center_factor * upper_factor
            raise_brow = (surprise * 0.08 + fear * 0.04) * brows_weight * center_factor

            dy -= angry_drop
            dy += raise_brow

        # 4. Eye region
        if ((-0.45 <= x <= -0.10) or (0.10 <= x <= 0.45)) and (0.00 <= y <= 0.30):
            eye_factor = (y - 0.00) / 0.30
            eye_factor = clamp(eye_factor, 0.0, 1.0)

            eye_expand = (surprise * 0.025 + fear * 0.018) * eyes_weight * eye_factor
            eye_drop = sad * 0.025 * eyes_weight
            eye_compress = angry * 0.012 * eyes_weight

            if x < 0:
                dx -= eye_expand
            else:
                dx += eye_expand

            dy -= eye_drop
            dy -= eye_compress * 0.5
            dz += eye_expand * 0.2

        # 5. Cheek region
        if ((-0.65 <= x <= -0.20) or (0.20 <= x <= 0.65)) and (-0.20 <= y <= 0.15):
            cheek_factor = 1.0 - abs(y) / 0.20
            cheek_factor = clamp(cheek_factor, 0.0, 1.0)

            cheek_lift = happy * 0.035 * cheeks_weight * cheek_factor
            cheek_tense = angry * 0.010 * cheeks_weight * cheek_factor

            dy += cheek_lift
            dz += cheek_tense

        # 全局安全限制：防止单点位移过大
        dx = clamp(dx * strength, -0.045, 0.045)
        dy = clamp(dy * strength, -0.060, 0.060)
        dz = clamp(dz * strength, -0.035, 0.035)

        new_vertices.append([x + dx, y + dy, z + dz])

    return new_vertices
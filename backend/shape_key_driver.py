from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional


def load_shape_key_data(json_path: str | Path) -> Optional[dict]:
    path = Path(json_path)
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def apply_shape_keys(
    vertices: List[List[float]],
    shape_key_data: Optional[dict],
    shape_key_weights: Dict[str, float],
    normalize_scale: float = 1.0,
) -> List[List[float]]:
    """
    把导出的 Blender shape key delta 叠加到当前顶点上。

    注意：
    - app.py 里上传 OBJ 后会做 normalize_vertices()
    - 所以这里需要用同一个 scale 把 delta 缩放回来
    """
    if not vertices or not shape_key_data:
        return vertices

    if shape_key_data.get("vertex_count") != len(vertices):
        return vertices

    shape_keys = shape_key_data.get("shape_keys", {})
    if not shape_keys:
        return vertices

    scale = normalize_scale if abs(normalize_scale) > 1e-8 else 1.0
    result = [v[:] for v in vertices]

    for key_name, weight in shape_key_weights.items():
        if abs(weight) < 1e-8:
            continue

        deltas = shape_keys.get(key_name)
        if not deltas or len(deltas) != len(vertices):
            continue

        for i, (dx, dy, dz) in enumerate(deltas):
            result[i][0] += dx / scale * weight
            result[i][1] += dy / scale * weight
            result[i][2] += dz / scale * weight

    return result


def build_test_shape_key_weights(emotion_values: Dict[str, float]) -> Dict[str, float]:
    """
    先只把 Python 里的 Happy / Sad 映射到 Blender 的 Joy / Sad key。
    """
    return {
        "Joy": emotion_values.get("Happy", 0.0),
        "Sad": emotion_values.get("Sad", 0.0),
    }
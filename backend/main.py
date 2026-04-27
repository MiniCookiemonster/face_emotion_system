from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from config import EMOTIONS, FACE_REGIONS
from emotion_engine import maybe_normalize
from mesh_deformer import deform_mesh
from obj_loader import load_obj_from_path, normalize_vertices
from shape_key_driver import apply_shape_keys, build_test_shape_key_weights, load_shape_key_data
import numpy as np

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Face Emotion Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def estimate_normalize_scale(vertices: list[list[float]]) -> float:
    if not vertices:
        return 1.0

    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    zs = [v[2] for v in vertices]

    cx = (max(xs) + min(xs)) / 2.0
    cy = (max(ys) + min(ys)) / 2.0
    cz = (max(zs) + min(zs)) / 2.0

    centered = [[x - cx, y - cy, z - cz] for x, y, z in vertices]
    max_abs = max(max(abs(v[0]), abs(v[1]), abs(v[2])) for v in centered)
    return max_abs if max_abs > 1e-8 else 1.0

def build_shape_key_weights_from_frontend(effective_emotions: dict[str, float], available_keys) -> dict[str, float]:
    available_map = {str(k).lower(): str(k) for k in available_keys}

    alias_groups = {
        "Happy": ["joy", "happy"],
        "Sad": ["sad"],
        "Angry": ["angry"],
        "Surprise": ["surprise"],
        "Disgust": ["disgust"],
        "Fear": ["fear"],
    }

    result = {}
    for emotion_name, aliases in alias_groups.items():
        value = float(effective_emotions.get(emotion_name, 0.0))
        if value <= 0:
            continue

        for alias in aliases:
            if alias.lower() in available_map:
                real_key_name = available_map[alias.lower()]
                result[real_key_name] = value
                break

    return result

def load_shape_key_json_from_path(path: Path):
    if not path.exists():
        return None
    return load_shape_key_data(path)

def get_shape_key_entries(shape_key_data):
    if not isinstance(shape_key_data, dict):
        return {}

    nested = shape_key_data.get("shape_keys")
    if isinstance(nested, dict):
        return nested

    return shape_key_data

def save_upload_to_temp(upload: UploadFile, suffix: str) -> Path:
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        data = upload.file.read()
        tmp.write(data)
        return Path(tmp.name)


def build_result_vertices(
    mesh_vertices: list[list[float]],
    shape_key_data,
    mesh_normalize_scale: float,
    emotion_values: dict[str, float],
    region_weights: dict[str, float],
    normalize_weights: bool,
) -> tuple[list[list[float]], dict[str, float]]:
    effective_emotions = maybe_normalize(emotion_values, normalize_weights)

    shape_key_vertices = mesh_vertices
    shape_key_weights = {}

    if shape_key_data is not None:
        shape_key_entries = get_shape_key_entries(shape_key_data)

        shape_key_weights = build_shape_key_weights_from_frontend(
            effective_emotions,
            shape_key_entries.keys(),
        )

        print("shape_key_weights =", shape_key_weights)
        print("mesh_vertex_count =", len(mesh_vertices))
        print("shape_key_vertex_count =",
              shape_key_data.get("vertex_count") if isinstance(shape_key_data, dict) else None)

        shape_key_vertices = apply_shape_keys(
            mesh_vertices,
            shape_key_data,  # 这里传原始 payload，不是 entries
            shape_key_weights,
            normalize_scale=mesh_normalize_scale,
        )

        base_np = np.asarray(mesh_vertices, dtype=float)
        shape_np = np.asarray(shape_key_vertices, dtype=float)
        shape_delta = np.linalg.norm(shape_np - base_np, axis=1)

        print("shape_only_max_delta =", float(shape_delta.max()))
        print("shape_only_mean_delta =", float(shape_delta.mean()))
        print("shape_only_changed_vertices =", int((shape_delta > 1e-6).sum()))

    residual_emotions = dict(effective_emotions)
    residual_emotions["Happy"] = 0.0
    residual_emotions["Sad"] = 0.0

    result_vertices = deform_mesh(
        shape_key_vertices,
        residual_emotions,
        region_weights,
    )
    return result_vertices, effective_emotions


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/config")
def get_config():
    return {
        "emotions": [
            {
                "name": item.name,
                "minimum": item.minimum,
                "maximum": item.maximum,
                "default": getattr(item, "default", 0.0),
                "step": item.step,
            }
            for item in EMOTIONS
        ],
        "face_regions": FACE_REGIONS,
    }


@app.post("/api/deform")
async def deform_api(
    obj_file: UploadFile = File(...),
    params_json: str = Form(...),
    shape_key_file: UploadFile | None = File(None),
):
    obj_temp_path: Path | None = None
    shape_temp_path: Path | None = None

    try:
        try:
            params = json.loads(params_json)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"params_json 不是合法 JSON：{exc}")

        emotion_values = params.get("emotion_values", {})
        region_weights = params.get("region_weights", {})
        normalize_weights = bool(params.get("normalize_weights", False))

        if not isinstance(emotion_values, dict):
            raise HTTPException(status_code=400, detail="emotion_values 必须是对象")
        if not isinstance(region_weights, dict):
            raise HTTPException(status_code=400, detail="region_weights 必须是对象")

        obj_temp_path = save_upload_to_temp(obj_file, ".obj")
        raw_vertices, faces = load_obj_from_path(obj_temp_path)
        mesh_vertices = normalize_vertices(raw_vertices)
        mesh_normalize_scale = estimate_normalize_scale(raw_vertices)

        shape_key_data = None

        if shape_key_file is not None:
            shape_temp_path = save_upload_to_temp(shape_key_file, ".json")
            shape_key_data = load_shape_key_json_from_path(shape_temp_path)
        else:
            default_shape_path = BASE_DIR / "shape_key_deltas.json"
            shape_key_data = load_shape_key_json_from_path(default_shape_path)

        result_vertices, effective_emotions = build_result_vertices(
            mesh_vertices=mesh_vertices,
            shape_key_data=shape_key_data,
            mesh_normalize_scale=mesh_normalize_scale,
            emotion_values=emotion_values,
            region_weights=region_weights,
            normalize_weights=normalize_weights,
        )

        base_np = np.asarray(mesh_vertices, dtype=float)
        result_np = np.asarray(result_vertices, dtype=float)
        delta = np.linalg.norm(result_np - base_np, axis=1)

        print("effective_emotions =", effective_emotions)
        print("available_shape_keys =", list(shape_key_data.keys()) if shape_key_data else [])
        print("max_delta =", float(delta.max()))
        print("mean_delta =", float(delta.mean()))
        print("changed_vertices =", int((delta > 1e-6).sum()))
        print("base_first_12 =", base_np.reshape(-1)[:12].tolist())
        print("result_first_12 =", result_np.reshape(-1)[:12].tolist())

        return {
            "model_name": obj_file.filename,
            "vertex_count": len(result_vertices),
            "face_count": len(faces),
            "effective_emotions": effective_emotions,
            "vertices": result_vertices,
            "faces": faces,
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"后端变形失败：{exc}")
    finally:
        for path in [obj_temp_path, shape_temp_path]:
            if path is not None and path.exists():
                try:
                    os.remove(path)
                except OSError:
                    pass
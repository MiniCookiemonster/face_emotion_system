
import argparse
import json
from pathlib import Path
from typing import List, Tuple, Dict

import numpy as np


def load_obj(path: Path) -> Tuple[np.ndarray, List[List[int]]]:
    vertices: List[List[float]] = []
    faces: List[List[int]] = []

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            if line.startswith("v "):
                parts = line.split()
                if len(parts) >= 4:
                    vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])

            elif line.startswith("f "):
                parts = line.split()[1:]
                face: List[int] = []
                for p in parts:
                    idx = p.split("/")[0]
                    if idx:
                        face.append(int(idx) - 1)

                if len(face) == 3:
                    faces.append(face)
                elif len(face) > 3:
                    for i in range(1, len(face) - 1):
                        faces.append([face[0], face[i], face[i + 1]])

    return np.asarray(vertices, dtype=np.float64), faces


def save_obj(path: Path, vertices: np.ndarray, faces: List[List[int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for v in vertices:
            f.write(f"v {v[0]:.8f} {v[1]:.8f} {v[2]:.8f}\n")
        for face in faces:
            f.write(f"f {face[0] + 1} {face[1] + 1} {face[2] + 1}\n")


def build_initial_vertex_mask(
    vertices: np.ndarray,
    mahal_keep_ratio: float,
    x_trim: float,
    y_trim: float,
    z_trim: float,
) -> np.ndarray:
    v = vertices
    center = np.median(v, axis=0)
    scale = np.std(v, axis=0)
    scale = np.where(scale < 1e-8, 1.0, scale)

    whitened = (v - center) / scale
    d2 = np.sum(whitened ** 2, axis=1)
    d2_thresh = np.quantile(d2, mahal_keep_ratio)

    qx0, qx1 = np.quantile(v[:, 0], [x_trim, 1.0 - x_trim])
    qy0, qy1 = np.quantile(v[:, 1], [y_trim, 1.0 - y_trim])
    qz0, qz1 = np.quantile(v[:, 2], [z_trim, 1.0 - z_trim])

    bbox_mask = (
        (v[:, 0] >= qx0) & (v[:, 0] <= qx1) &
        (v[:, 1] >= qy0) & (v[:, 1] <= qy1) &
        (v[:, 2] >= qz0) & (v[:, 2] <= qz1)
    )
    dist_mask = d2 <= d2_thresh

    keep = bbox_mask & dist_mask
    return keep


def keep_largest_face_component(
    faces: List[List[int]],
    vertex_mask: np.ndarray,
) -> Tuple[List[List[int]], np.ndarray]:
    filtered_faces: List[List[int]] = [
        face for face in faces if vertex_mask[face[0]] and vertex_mask[face[1]] and vertex_mask[face[2]]
    ]

    if not filtered_faces:
        raise RuntimeError("No faces remain after initial crop. Relax the crop parameters.")

    vert_to_faces: Dict[int, List[int]] = {}
    for fi, face in enumerate(filtered_faces):
        for vid in face:
            vert_to_faces.setdefault(vid, []).append(fi)

    visited = [False] * len(filtered_faces)
    components: List[List[int]] = []

    for start in range(len(filtered_faces)):
        if visited[start]:
            continue

        stack = [start]
        visited[start] = True
        comp: List[int] = []

        while stack:
            fi = stack.pop()
            comp.append(fi)
            for vid in filtered_faces[fi]:
                for nbr in vert_to_faces.get(vid, []):
                    if not visited[nbr]:
                        visited[nbr] = True
                        stack.append(nbr)

        components.append(comp)

    largest = max(components, key=len)
    kept_faces = [filtered_faces[i] for i in largest]

    kept_vertex_idx = sorted({vid for face in kept_faces for vid in face})
    final_mask = np.zeros(vertex_mask.shape[0], dtype=bool)
    final_mask[kept_vertex_idx] = True
    return kept_faces, final_mask


def remap_faces(faces: List[List[int]], kept_vertex_idx: List[int]) -> List[List[int]]:
    mapping = {old: new for new, old in enumerate(kept_vertex_idx)}
    return [[mapping[a], mapping[b], mapping[c]] for a, b, c in faces]


def choose_reference(input_dir: Path, processed_dir: Path, reference_name: str | None) -> Path:
    candidates = []
    if reference_name:
        candidates.append(processed_dir / reference_name)
        candidates.append(input_dir / reference_name)
    candidates.extend([
        processed_dir / "mean_neutral_aligned.obj",
        input_dir / "face_008.obj",
        input_dir / "face_000.obj",
    ])
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError("No usable reference OBJ found.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Consistently crop face core region across aligned OBJ files.")
    parser.add_argument("--project-dir", type=str, default=".")
    parser.add_argument("--input-subdir", type=str, default="data/aligned_faces")
    parser.add_argument("--output-subdir", type=str, default="data/cropped_faces")
    parser.add_argument("--processed-subdir", type=str, default="data/processed")
    parser.add_argument("--reference-name", type=str, default="mean_neutral_aligned.obj")
    parser.add_argument("--mahal-keep-ratio", type=float, default=0.95)
    parser.add_argument("--x-trim", type=float, default=0.02)
    parser.add_argument("--y-trim", type=float, default=0.03)
    parser.add_argument("--z-trim", type=float, default=0.03)
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    input_dir = project_dir / args.input_subdir
    output_dir = project_dir / args.output_subdir
    processed_dir = project_dir / args.processed_subdir

    obj_files = sorted(input_dir.glob("face_*.obj"))
    if not input_dir.exists():
        raise FileNotFoundError(f"Input dir not found: {input_dir}")
    if not obj_files:
        raise FileNotFoundError(f"No face_*.obj files found in: {input_dir}")

    reference_path = choose_reference(input_dir, processed_dir, args.reference_name)
    ref_vertices, ref_faces = load_obj(reference_path)

    if ref_vertices.size == 0 or not ref_faces:
        raise RuntimeError(f"Reference OBJ is empty or has no faces: {reference_path}")

    initial_mask = build_initial_vertex_mask(
        ref_vertices,
        mahal_keep_ratio=args.mahal_keep_ratio,
        x_trim=args.x_trim,
        y_trim=args.y_trim,
        z_trim=args.z_trim,
    )
    kept_faces_old_idx, final_mask = keep_largest_face_component(ref_faces, initial_mask)
    kept_vertex_idx = np.flatnonzero(final_mask).tolist()
    remapped_faces = remap_faces(kept_faces_old_idx, kept_vertex_idx)

    print(f"Reference: {reference_path.name}")
    print(f"Original vertices={len(ref_vertices)}, faces={len(ref_faces)}")
    print(f"Kept vertices={len(kept_vertex_idx)}, faces={len(remapped_faces)}")

    output_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    all_cropped_vertices = []

    for obj_path in obj_files:
        vertices, faces = load_obj(obj_path)

        if len(vertices) != len(ref_vertices):
            raise RuntimeError(
                f"Vertex count mismatch: {obj_path.name} has {len(vertices)}, "
                f"reference has {len(ref_vertices)}"
            )
        if len(faces) != len(ref_faces):
            raise RuntimeError(
                f"Face count mismatch: {obj_path.name} has {len(faces)}, "
                f"reference has {len(ref_faces)}"
            )

        cropped_vertices = vertices[kept_vertex_idx]
        all_cropped_vertices.append(cropped_vertices)

        out_path = output_dir / obj_path.name
        save_obj(out_path, cropped_vertices, remapped_faces)
        print(f"Saved: {out_path}")

    mean_candidates = [
        processed_dir / "mean_neutral_aligned.obj",
        project_dir / "mean_neutral_with_faces.obj",
    ]
    mean_source = next((p for p in mean_candidates if p.exists()), None)

    if mean_source is not None:
        mean_vertices, _ = load_obj(mean_source)
        if len(mean_vertices) == len(ref_vertices):
            mean_cropped = mean_vertices[kept_vertex_idx]
            save_obj(processed_dir / "mean_neutral_cropped.obj", mean_cropped, remapped_faces)
            print(f"Saved: {processed_dir / 'mean_neutral_cropped.obj'}")
    else:
        mean_stack = np.mean(np.stack(all_cropped_vertices, axis=0), axis=0)
        save_obj(processed_dir / "mean_neutral_cropped.obj", mean_stack, remapped_faces)
        print(f"Saved: {processed_dir / 'mean_neutral_cropped.obj'}")

    meta = {
        "reference": str(reference_path),
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "original_vertex_count": int(len(ref_vertices)),
        "original_face_count": int(len(ref_faces)),
        "kept_vertex_count": int(len(kept_vertex_idx)),
        "kept_face_count": int(len(remapped_faces)),
        "kept_vertex_indices": kept_vertex_idx,
        "params": {
            "mahal_keep_ratio": args.mahal_keep_ratio,
            "x_trim": args.x_trim,
            "y_trim": args.y_trim,
            "z_trim": args.z_trim,
        },
    }
    meta_path = processed_dir / "cropped_face_mask.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"Saved: {meta_path}")


if __name__ == "__main__":
    main()

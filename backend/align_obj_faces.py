from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np


@dataclass
class ObjData:
    path: Path
    lines: list[str]
    vertex_line_indices: list[int]
    vertices: np.ndarray


def load_obj_preserve_lines(path: Path) -> ObjData:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    vertex_line_indices: list[int] = []
    vertices: list[list[float]] = []

    for idx, raw_line in enumerate(lines):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("v "):
            parts = line.split()
            if len(parts) < 4:
                raise ValueError(f"Invalid vertex line in {path.name}: {raw_line!r}")
            vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
            vertex_line_indices.append(idx)

    if not vertices:
        raise ValueError(f"No vertices found in {path}")

    return ObjData(
        path=path,
        lines=lines,
        vertex_line_indices=vertex_line_indices,
        vertices=np.asarray(vertices, dtype=np.float64),
    )


def save_obj_with_new_vertices(obj: ObjData, vertices: np.ndarray, output_path: Path) -> None:
    if len(vertices) != len(obj.vertex_line_indices):
        raise ValueError(
            f"Vertex count mismatch for {obj.path.name}: {len(vertices)} vs {len(obj.vertex_line_indices)}"
        )

    new_lines = list(obj.lines)
    for line_idx, vertex in zip(obj.vertex_line_indices, vertices):
        new_lines[line_idx] = f"v {vertex[0]:.8f} {vertex[1]:.8f} {vertex[2]:.8f}"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def bbox_center(vertices: np.ndarray) -> np.ndarray:
    return (vertices.max(axis=0) + vertices.min(axis=0)) / 2.0


def build_alignment_subset(reference_vertices: np.ndarray, subset_ratio: float) -> np.ndarray:
    if not 0.0 < subset_ratio <= 1.0:
        raise ValueError("subset_ratio must be in (0, 1].")

    n_vertices = len(reference_vertices)
    if subset_ratio >= 0.999:
        return np.arange(n_vertices)

    center = reference_vertices.mean(axis=0)
    distances = np.linalg.norm(reference_vertices - center, axis=1)
    keep_count = max(8, int(round(n_vertices * subset_ratio)))
    return np.argsort(distances)[:keep_count]


def kabsch_align(
    source_vertices: np.ndarray,
    target_vertices: np.ndarray,
    subset_indices: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if source_vertices.shape != target_vertices.shape:
        raise ValueError("source_vertices and target_vertices must have the same shape")

    if subset_indices is None:
        src_fit = source_vertices
        tgt_fit = target_vertices
    else:
        src_fit = source_vertices[subset_indices]
        tgt_fit = target_vertices[subset_indices]

    src_center = src_fit.mean(axis=0)
    tgt_center = tgt_fit.mean(axis=0)

    src_centered = src_fit - src_center
    tgt_centered = tgt_fit - tgt_center

    covariance = src_centered.T @ tgt_centered
    u, _, vt = np.linalg.svd(covariance)
    rotation = vt.T @ u.T

    if np.linalg.det(rotation) < 0:
        vt[-1, :] *= -1
        rotation = vt.T @ u.T

    all_source_centered = source_vertices - src_center
    aligned_vertices = all_source_centered @ rotation + tgt_center

    return aligned_vertices, rotation, (tgt_center - src_center @ rotation)


def rms_distance(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.sum((a - b) ** 2, axis=1))))


def iter_obj_files(input_dir: Path) -> list[Path]:
    files = sorted(input_dir.glob("face_*.obj"))
    if not files:
        raise FileNotFoundError(f"No face_*.obj files found in: {input_dir}")
    return files


def ensure_consistent_vertex_counts(meshes: Iterable[ObjData]) -> None:
    meshes = list(meshes)
    base_count = len(meshes[0].vertices)
    base_name = meshes[0].path.name
    for mesh in meshes[1:]:
        if len(mesh.vertices) != base_count:
            raise ValueError(
                f"Vertex count mismatch: {mesh.path.name} has {len(mesh.vertices)}, "
                f"but {base_name} has {base_count}."
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Align raw face OBJ files so they are easier to use as Blender shape keys. "
            "The script preserves the original OBJ structure and only rewrites vertex positions."
        )
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="Project root containing data/raw_faces. Defaults to this script's folder.",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=None,
        help="Directory with raw OBJ files. Defaults to <project-dir>/data/raw_faces.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for aligned OBJ files. Defaults to <project-dir>/data/aligned_faces.",
    )
    parser.add_argument(
        "--processed-dir",
        type=Path,
        default=None,
        help="Directory for the mean neutral OBJ. Defaults to <project-dir>/data/processed.",
    )
    parser.add_argument(
        "--basis",
        type=str,
        default="face_008.obj",
        help="Reference OBJ filename used as alignment target.",
    )
    parser.add_argument(
        "--subset-ratio",
        type=float,
        default=0.80,
        help=(
            "Fraction of the most central vertices used to estimate rigid alignment. "
            "Lower values can reduce the influence of noisy scan boundaries."
        ),
    )
    parser.add_argument(
        "--full-fit",
        action="store_true",
        help="Use all vertices for rigid alignment instead of the central subset.",
    )
    parser.add_argument(
        "--no-rigid",
        action="store_true",
        help="Only center meshes to the basis bounding-box center; skip Kabsch rotation alignment.",
    )
    parser.add_argument(
        "--no-center-to-origin",
        action="store_true",
        help="Keep the aligned meshes in basis space instead of recentering them around the origin.",
    )
    parser.add_argument(
        "--mean-name",
        type=str,
        default="mean_neutral_aligned.obj",
        help="Filename for the averaged neutral mesh written to processed_dir.",
    )
    args = parser.parse_args()

    project_dir = args.project_dir.resolve()
    input_dir = (args.input_dir or (project_dir / "data" / "raw_faces")).resolve()
    output_dir = (args.output_dir or (project_dir / "data" / "aligned_faces")).resolve()
    processed_dir = (args.processed_dir or (project_dir / "data" / "processed")).resolve()

    obj_paths = iter_obj_files(input_dir)
    meshes = [load_obj_preserve_lines(path) for path in obj_paths]
    ensure_consistent_vertex_counts(meshes)

    mesh_by_name = {mesh.path.name: mesh for mesh in meshes}
    if args.basis not in mesh_by_name:
        available = ", ".join(mesh_by_name)
        raise FileNotFoundError(f"Basis {args.basis!r} not found. Available: {available}")

    basis_mesh = mesh_by_name[args.basis]
    basis_vertices = basis_mesh.vertices.copy()
    subset_indices = None if args.full_fit else build_alignment_subset(basis_vertices, args.subset_ratio)

    aligned_vertices_by_name: dict[str, np.ndarray] = {}

    print(f"Input dir      : {input_dir}")
    print(f"Output dir     : {output_dir}")
    print(f"Processed dir  : {processed_dir}")
    print(f"Basis          : {basis_mesh.path.name}")
    print(f"Vertex count   : {len(basis_vertices)}")
    if subset_indices is None:
        print("Alignment mode : full rigid fit")
    else:
        print(f"Alignment mode : rigid fit on {len(subset_indices)} central vertices ({args.subset_ratio:.0%})")
    if args.no_rigid:
        print("Rigid fit      : disabled (translation only)")

    basis_center_after = bbox_center(basis_vertices)

    for mesh in meshes:
        source = mesh.vertices

        if mesh.path.name == basis_mesh.path.name:
            aligned = source.copy()
        elif args.no_rigid:
            source_center = bbox_center(source)
            aligned = source - source_center + basis_center_after
        else:
            aligned, _, _ = kabsch_align(source, basis_vertices, subset_indices=subset_indices)

        aligned_vertices_by_name[mesh.path.name] = aligned

        if subset_indices is None:
            before = rms_distance(source, basis_vertices)
            after = rms_distance(aligned, basis_vertices)
        else:
            before = rms_distance(source[subset_indices], basis_vertices[subset_indices])
            after = rms_distance(aligned[subset_indices], basis_vertices[subset_indices])

        print(f"{mesh.path.name:12s} | subset RMS before {before:10.6f} -> after {after:10.6f}")

    if not args.no_center_to_origin:
        origin_shift = bbox_center(aligned_vertices_by_name[basis_mesh.path.name])
        for name in list(aligned_vertices_by_name):
            aligned_vertices_by_name[name] = aligned_vertices_by_name[name] - origin_shift
        print(f"Post-center    : shifted all meshes by {-origin_shift} so the basis sits near the origin")

    output_dir.mkdir(parents=True, exist_ok=True)
    for mesh in meshes:
        out_path = output_dir / mesh.path.name
        save_obj_with_new_vertices(mesh, aligned_vertices_by_name[mesh.path.name], out_path)

    processed_dir.mkdir(parents=True, exist_ok=True)
    all_aligned = np.stack([aligned_vertices_by_name[mesh.path.name] for mesh in meshes], axis=0)
    mean_vertices = np.mean(all_aligned, axis=0)
    mean_path = processed_dir / args.mean_name
    save_obj_with_new_vertices(basis_mesh, mean_vertices, mean_path)

    print()
    print("Done.")
    print(f"Aligned OBJs written to: {output_dir}")
    print(f"Mean neutral written to: {mean_path}")
    print()
    print("Next step in Blender:")
    print(f"1) Load shape keys from: {output_dir}")
    print(f"2) Use either {args.basis} or {args.mean_name} as the Basis mesh")
    print("3) Hide or delete helper objects after Join as Shapes")


if __name__ == "__main__":
    main()

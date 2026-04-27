import numpy as np
import os
from pathlib import Path


def load_obj(path: str):
    vertices = []

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw_line in f:
            line = raw_line.strip()

            if not line or line.startswith("#"):
                continue

            if line.startswith("v "):
                parts = line.split()
                vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])

    return vertices


def normalize_vertices(vertices: np.ndarray) -> np.ndarray:
    """
    将顶点居中并缩放到大致 [-1, 1] 范围，方便显示。
    """
    center = (vertices.max(axis=0) + vertices.min(axis=0)) / 2.0
    vertices = vertices - center

    scale = np.abs(vertices).max()
    if scale > 1e-8:
        vertices = vertices / scale

    return vertices


def save_obj(vertices: np.ndarray, output_path: str) -> None:
    """
    将顶点数据保存为 OBJ 格式
    """
    with open(output_path, "w", encoding="utf-8") as f:
        for v in vertices:
            f.write(f"v {v[0]} {v[1]} {v[2]}\n")

    print(f"文件已保存至 {output_path}")


def main():
    project_root = Path(__file__).resolve().parent.parent
    raw_dir = project_root / "data" / "raw_faces"
    processed_dir = project_root / "data" / "processed"
    processed_dir.mkdir(parents=True, exist_ok=True)

    obj_files = sorted(raw_dir.glob("*.obj"))
    if not obj_files:
        raise FileNotFoundError(f"未找到 OBJ 文件，请检查目录: {raw_dir}")

    print(f"共找到 {len(obj_files)} 个 OBJ 文件")

    all_vertices = []

    # 读取所有 OBJ 文件的顶点数据
    for obj_path in obj_files:
        vertices = load_obj(str(obj_path))
        all_vertices.append(vertices)

        print(f"已处理: {obj_path.name} | 顶点数={len(vertices)}")

    # 计算平均顶点
    mean_vertices = np.mean(all_vertices, axis=0)

    # 保存为 OBJ 文件
    mean_obj_path = processed_dir / "mean_neutral.obj"
    save_obj(mean_vertices, str(mean_obj_path))


if __name__ == "__main__":
    main()
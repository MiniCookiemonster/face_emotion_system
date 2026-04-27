from typing import List, Tuple
import tempfile
import os


def save_uploaded_obj_to_temp(uploaded_file) -> str:
    """
    将 Streamlit 上传的 OBJ 文件保存到临时路径，返回文件路径。
    """
    suffix = os.path.splitext(uploaded_file.name)[1] or ".obj"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        return tmp.name


def load_obj_from_path(file_path: str) -> Tuple[List[List[float]], List[List[int]]]:
    """
    从本地路径读取 OBJ 文件，返回:
    - vertices: [[x, y, z], ...]
    - faces: [[i, j, k], ...]  这里索引从 0 开始
    说明：
    - 只处理常见的 v / f
    - 如果面是四边形或更多边，会自动拆成三角形
    """
    vertices: List[List[float]] = []
    faces: List[List[int]] = []

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for raw_line in f:
            line = raw_line.strip()

            if not line or line.startswith("#"):
                continue

            if line.startswith("v "):
                parts = line.split()
                if len(parts) >= 4:
                    x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                    vertices.append([x, y, z])

            elif line.startswith("f "):
                parts = line.split()[1:]
                face_indices = []

                for p in parts:
                    # 支持 f 1/2/3 或 f 1//3 或 f 1
                    idx_str = p.split("/")[0]
                    if idx_str:
                        face_indices.append(int(idx_str) - 1)

                # 三角面
                if len(face_indices) == 3:
                    faces.append(face_indices)

                # 四边形/多边形 -> 扇形三角化
                elif len(face_indices) > 3:
                    for i in range(1, len(face_indices) - 1):
                        faces.append(
                            [face_indices[0], face_indices[i], face_indices[i + 1]]
                        )

    return vertices, faces


def normalize_vertices(vertices: List[List[float]]) -> List[List[float]]:
    """
    将顶点居中并缩放到大致 [-1, 1] 范围，方便显示。
    """
    if not vertices:
        return vertices

    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    zs = [v[2] for v in vertices]

    cx = (max(xs) + min(xs)) / 2
    cy = (max(ys) + min(ys)) / 2
    cz = (max(zs) + min(zs)) / 2

    centered = [[x - cx, y - cy, z - cz] for x, y, z in vertices]

    max_abs = max(
        max(abs(v[0]), abs(v[1]), abs(v[2])) for v in centered
    )

    if max_abs < 1e-8:
        return centered

    return [[v[0] / max_abs, v[1] / max_abs, v[2] / max_abs] for v in centered]
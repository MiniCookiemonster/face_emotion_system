import os
from pathlib import Path

def load_obj(path: str):
    vertices = []
    faces = []

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw_line in f:
            line = raw_line.strip()

            if not line or line.startswith("#"):
                continue

            if line.startswith("v "):
                parts = line.split()
                vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])

            elif line.startswith("f "):
                parts = line.split()[1:]
                face = []
                for p in parts:
                    idx = int(p.split("/")[0]) - 1
                    face.append(idx)

                if len(face) == 3:
                    faces.append(face)
                elif len(face) > 3:
                    for i in range(1, len(face) - 1):
                        faces.append([face[0], face[i], face[i + 1]])

    return vertices, faces


def check_consistency(directory: Path):
    obj_files = sorted(directory.glob("*.obj"))
    if not obj_files:
        raise FileNotFoundError(f"未找到 OBJ 文件，请检查目录: {directory}")

    print(f"共找到 {len(obj_files)} 个 OBJ 文件")

    first_vertices, first_faces = load_obj(str(obj_files[0]))

    consistent = True

    for obj_path in obj_files[1:]:
        vertices, faces = load_obj(str(obj_path))

        if len(vertices) != len(first_vertices):
            print(f"错误: {obj_path.name} 顶点数与 {obj_files[0].name} 不一致")
            consistent = False
        if len(faces) != len(first_faces):
            print(f"错误: {obj_path.name} 面数与 {obj_files[0].name} 不一致")
            consistent = False
        if faces != first_faces:
            print(f"错误: {obj_path.name} 面连接关系与 {obj_files[0].name} 不一致")
            consistent = False

    if consistent:
        print("所有 OBJ 文件顶点数和面连接关系一致！")
    else:
        print("部分 OBJ 文件顶点数或面连接关系不一致，请检查！")


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    raw_dir = project_root / "data" / "raw_faces"
    check_consistency(raw_dir)
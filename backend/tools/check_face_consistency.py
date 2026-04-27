import os
from pathlib import Path


def load_obj_faces(path: str):
    faces = []

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.startswith("f "):
                parts = line.split()[1:]
                face = [int(p.split("/")[0]) - 1 for p in parts]  # 提取顶点索引
                faces.append(face)

    return faces


def check_face_consistency(directory: Path):
    obj_files = sorted(directory.glob("*.obj"))
    if not obj_files:
        raise FileNotFoundError(f"未找到 OBJ 文件，请检查目录: {directory}")

    print(f"共找到 {len(obj_files)} 个 OBJ 文件")

    first_faces = load_obj_faces(str(obj_files[0]))

    consistent = True
    for obj_path in obj_files[1:]:
        faces = load_obj_faces(str(obj_path))

        if faces != first_faces:
            print(f"错误: {obj_path.name} 面连接关系与 {obj_files[0].name} 不一致")
            consistent = False

    if consistent:
        print("所有 OBJ 文件面连接关系一致！")
    else:
        print("部分 OBJ 文件面连接关系不一致，请检查！")


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parent.parent
    raw_dir = project_root / "data" / "raw_faces"
    check_face_consistency(raw_dir)
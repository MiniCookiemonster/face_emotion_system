
import bpy
from pathlib import Path

PROJECT_DIR = Path(r"C:\Users\halvinge\Desktop\毕设\face_emotion_system")
DATA_DIR = PROJECT_DIR / "data" / "cropped_faces"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"

PREFERRED_BASIS = ["mean_neutral_cropped.obj", "face_008.obj"]
DELETE_HELPERS = False
HIDE_HELPERS = True

OBJ_FILES = sorted(DATA_DIR.glob("face_*.obj"))
BASIS_CANDIDATES = [PROCESSED_DIR / name for name in PREFERRED_BASIS] + [DATA_DIR / name for name in PREFERRED_BASIS]


def import_obj(path: Path):
    bpy.ops.wm.obj_import(filepath=str(path))
    return bpy.context.selected_objects[0]


def clear_scene_meshes():
    bpy.ops.object.select_all(action='DESELECT')
    for obj in list(bpy.data.objects):
        if obj.type == 'MESH':
            obj.select_set(True)
    bpy.ops.object.delete()


def pick_basis_path() -> Path:
    for path in BASIS_CANDIDATES:
        if path.exists():
            return path
    if OBJ_FILES:
        return OBJ_FILES[0]
    raise FileNotFoundError(f"No OBJ files found in: {DATA_DIR}")


def main():
    print("PROJECT_DIR =", PROJECT_DIR)
    print("DATA_DIR =", DATA_DIR)
    print("DATA_DIR exists =", DATA_DIR.exists())
    print("OBJ_FILES =", [p.name for p in OBJ_FILES])

    if not DATA_DIR.exists():
        raise FileNotFoundError(f"Cropped face directory not found: {DATA_DIR}")
    if not OBJ_FILES:
        raise FileNotFoundError(f"No face_*.obj files found in: {DATA_DIR}")

    clear_scene_meshes()

    basis_path = pick_basis_path()
    basis_obj = import_obj(basis_path)
    basis_obj.name = "FaceBasis"

    bpy.context.view_layer.objects.active = basis_obj
    basis_obj.select_set(True)

    imported = []
    for path in OBJ_FILES:
        if path == basis_path:
            continue
        obj = import_obj(path)
        imported.append((path, obj))

    for path, obj in imported:
        bpy.ops.object.select_all(action='DESELECT')
        basis_obj.select_set(True)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = basis_obj
        bpy.ops.object.join_shapes()

        key_blocks = basis_obj.data.shape_keys.key_blocks
        key_blocks[-1].name = path.stem

        if DELETE_HELPERS:
            bpy.data.objects.remove(obj, do_unlink=True)
        elif HIDE_HELPERS:
            obj.hide_set(True)
            obj.hide_render = True

    if basis_obj.data.shape_keys:
        key_blocks = basis_obj.data.shape_keys.key_blocks
        key_blocks[0].name = "Basis"

    print("Done. Basis object:", basis_obj.name)
    print("Shape keys:", [kb.name for kb in basis_obj.data.shape_keys.key_blocks])


if __name__ == "__main__":
    main()

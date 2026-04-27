import bpy
from pathlib import Path

DATA_DIR = Path(r"C:\Users\halvinge\Desktop\毕设\face_emotion_system\data\raw_faces")
OBJ_FILES = sorted(DATA_DIR.glob("face_*.obj"))

BASIS_NAME = "face_008.obj"

print("DATA_DIR =", DATA_DIR)
print("DATA_DIR exists =", DATA_DIR.exists())
print("OBJ_FILES =", [p.name for p in OBJ_FILES])

def import_obj(path: Path):
    bpy.ops.wm.obj_import(filepath=str(path))
    return bpy.context.selected_objects[0]


def clear_scene_meshes():
    bpy.ops.object.select_all(action='DESELECT')
    for obj in list(bpy.data.objects):
        if obj.type == 'MESH':
            obj.select_set(True)
    bpy.ops.object.delete()


def main():
    if not OBJ_FILES:
        raise FileNotFoundError('No face_*.obj files found next to this script.')

    clear_scene_meshes()

    basis_path = DATA_DIR / BASIS_NAME
    if not basis_path.exists():
        basis_path = OBJ_FILES[0]

    basis_obj = import_obj(basis_path)
    basis_obj.name = 'FaceBasis'

    bpy.context.view_layer.objects.active = basis_obj
    basis_obj.select_set(True)

    imported = []
    for path in OBJ_FILES:
        if path == basis_path:
            continue
        obj = import_obj(path)
        imported.append((path, obj))

    # Join as shape keys one by one
    for path, obj in imported:
        bpy.ops.object.select_all(action='DESELECT')
        basis_obj.select_set(True)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = basis_obj
        bpy.ops.object.join_shapes()

        # Rename the newest shape key after the source file
        key_blocks = basis_obj.data.shape_keys.key_blocks
        key_blocks[-1].name = path.stem

        # Hide imported helper object
        obj.hide_set(True)
        obj.hide_render = True

    # Ensure Basis key exists and rename if needed
    if basis_obj.data.shape_keys:
        key_blocks = basis_obj.data.shape_keys.key_blocks
        key_blocks[0].name = 'Basis'

    print('Done. Basis object:', basis_obj.name)
    print('Shape keys:', [kb.name for kb in basis_obj.data.shape_keys.key_blocks])


if __name__ == '__main__':
    main()

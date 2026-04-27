from pathlib import Path
import bpy
import json

PROJECT_DIR = Path(r"C:\Users\halvinge\Desktop\毕设\face_emotion_system")
OUTPUT_PATH = PROJECT_DIR / "shape_key_deltas.json"
OBJ_NAME = "face_008"

def main():
    obj = bpy.data.objects.get(OBJ_NAME)
    if obj is None:
        raise ValueError(f'Object not found: {OBJ_NAME}')
    if obj.type != 'MESH':
        raise ValueError(f'Object is not a mesh: {OBJ_NAME}')
    if obj.data.shape_keys is None:
        raise ValueError(f'Object has no shape keys: {OBJ_NAME}')

    key_blocks = obj.data.shape_keys.key_blocks
    basis = key_blocks['Basis']

    result = {
        'object_name': obj.name,
        'vertex_count': len(obj.data.vertices),
        'shape_keys': {}
    }

    for key in key_blocks:
        if key.name == 'Basis':
            continue
        deltas = []
        for i in range(len(obj.data.vertices)):
            bx, by, bz = basis.data[i].co[:]
            kx, ky, kz = key.data[i].co[:]
            deltas.append([kx - bx, ky - by, kz - bz])
        result['shape_keys'][key.name] = deltas

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(result, f)

    print(f'Exported to: {OUTPUT_PATH}')
    print('Shape keys:', list(result['shape_keys'].keys()))


if __name__ == '__main__':
    main()

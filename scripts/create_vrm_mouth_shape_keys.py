import sys
from pathlib import Path

import bpy


EXTRA_KEYS = {
    "Fcl_MTH_MBP": {"Fcl_MTH_Close": 1.0},
    "Fcl_MTH_FV": {"Fcl_MTH_Close": 0.55, "Fcl_MTH_I": 0.35},
    "Fcl_MTH_SZH": {"Fcl_MTH_Close": 0.25, "Fcl_MTH_I": 0.45},
    "Fcl_MTH_CHSH": {"Fcl_MTH_U": 0.45, "Fcl_MTH_I": 0.25},
}


def import_vrm(path: Path) -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    try:
        bpy.ops.import_scene.vrm(filepath=str(path))
    except Exception:
        bpy.ops.import_scene.gltf(filepath=str(path))


def find_face_object():
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and obj.data.shape_keys:
            names = {key.name for key in obj.data.shape_keys.key_blocks}
            if {"Fcl_MTH_A", "Fcl_MTH_I", "Fcl_MTH_U", "Fcl_MTH_E", "Fcl_MTH_O"}.issubset(names):
                return obj
    raise RuntimeError("Face mesh with VRoid mouth shape keys not found")


def clear_key_values(face):
    for key in face.data.shape_keys.key_blocks:
        key.value = 0.0


def create_key_from_mix(face, name: str, mix: dict[str, float]):
    keys = face.data.shape_keys.key_blocks
    if name in keys:
        return keys[name]
    clear_key_values(face)
    for source, value in mix.items():
        if source not in keys:
            raise RuntimeError(f"Missing source shape key: {source}")
        keys[source].value = value
    bpy.context.view_layer.objects.active = face
    face.select_set(True)
    new_key = face.shape_key_add(name=name, from_mix=True)
    clear_key_values(face)
    return new_key


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    if len(args) < 2:
        raise SystemExit(
            "Usage: blender --background --python create_vrm_mouth_shape_keys.py -- <input.vrm> <output.blend>"
        )
    in_path = Path(args[0]).resolve()
    out_blend = Path(args[1]).resolve()

    import_vrm(in_path)
    face = find_face_object()
    for name, mix in EXTRA_KEYS.items():
        create_key_from_mix(face, name, mix)

    bpy.ops.wm.save_as_mainfile(filepath=str(out_blend))
    print(f"Created {out_blend}")
    print("Added shape keys:", ", ".join(EXTRA_KEYS))


if __name__ == "__main__":
    main()

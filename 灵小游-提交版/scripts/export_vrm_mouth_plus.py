import sys
from pathlib import Path

import addon_utils
import bpy


EXTRA_KEYS = {
    "mbp": ("Fcl_MTH_MBP", {"Fcl_MTH_Close": 1.0}),
    "fv": ("Fcl_MTH_FV", {"Fcl_MTH_Close": 0.55, "Fcl_MTH_I": 0.35}),
    "szh": ("Fcl_MTH_SZH", {"Fcl_MTH_Close": 0.25, "Fcl_MTH_I": 0.45}),
    "chsh": ("Fcl_MTH_CHSH", {"Fcl_MTH_U": 0.45, "Fcl_MTH_I": 0.25}),
}


def enable_vrm_addon():
    addon_utils.enable("bl_ext.user_default.vrm", default_set=True)


def import_vrm(path: Path):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    bpy.ops.import_scene.vrm(filepath=str(path))


def face_object():
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH" and obj.data.shape_keys:
            names = {key.name for key in obj.data.shape_keys.key_blocks}
            if {"Fcl_MTH_A", "Fcl_MTH_I", "Fcl_MTH_U", "Fcl_MTH_E", "Fcl_MTH_O"}.issubset(names):
                return obj
    raise RuntimeError("Face object with mouth shape keys not found")


def armature_object():
    return next(obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE")


def clear_values(face):
    for key in face.data.shape_keys.key_blocks:
        key.value = 0.0


def add_shape_key(face, key_name: str, mix: dict[str, float]):
    keys = face.data.shape_keys.key_blocks
    if key_name in keys:
        return
    clear_values(face)
    for source, value in mix.items():
        if source not in keys:
            raise RuntimeError(f"Missing source shape key: {source}")
        keys[source].value = value
    bpy.context.view_layer.objects.active = face
    face.select_set(True)
    face.shape_key_add(name=key_name, from_mix=True)
    clear_values(face)


def add_custom_expression(armature, expression_name: str, mesh_name: str, key_name: str):
    expressions = armature.data.vrm_addon_extension.vrm1.expressions
    current = expressions.all_name_to_expression_dict()
    if expression_name in current:
        expr = current[expression_name]
    else:
        expr = expressions.custom.add()
        expr.custom_name = expression_name

    expr.is_binary = False
    expr.override_blink = "none"
    expr.override_look_at = "none"
    expr.override_mouth = "none"
    expr.morph_target_binds.clear()
    bind = expr.morph_target_binds.add()
    bind.node.mesh_object_name = mesh_name
    bind.index = key_name
    bind.weight = 1.0


def export_vrm(path: Path):
    bpy.ops.export_scene.vrm(filepath=str(path))


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    if len(args) < 2:
        raise SystemExit("Usage: blender --background --python export_vrm_mouth_plus.py -- <input.vrm> <output.vrm>")
    input_path = Path(args[0]).resolve()
    output_path = Path(args[1]).resolve()

    enable_vrm_addon()
    import_vrm(input_path)
    face = face_object()
    armature = armature_object()

    for expression_name, (key_name, mix) in EXTRA_KEYS.items():
        add_shape_key(face, key_name, mix)
        add_custom_expression(armature, expression_name, face.name, key_name)

    export_vrm(output_path)
    print(f"Exported {output_path}")


if __name__ == "__main__":
    main()

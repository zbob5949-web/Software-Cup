import sys
from pathlib import Path

import addon_utils
import bpy


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    in_path = Path(args[0]).resolve()
    addon_utils.enable("bl_ext.user_default.vrm", default_set=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    bpy.ops.import_scene.vrm(filepath=str(in_path))
    arm = next(obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE")
    ext = arm.data.vrm_addon_extension
    print("ARM", arm.name)
    print("EXT DIR", [n for n in dir(ext) if "vrm" in n.lower() or "expression" in n.lower()])
    vrm1 = ext.vrm1
    print("VRM1 DIR", [n for n in dir(vrm1) if "expression" in n.lower() or "meta" in n.lower()])
    expressions = vrm1.expressions
    print("EXP DIR", [n for n in dir(expressions) if not n.startswith("_")])
    print("PRESET DIR", [n for n in dir(expressions.preset) if not n.startswith("_")])
    for name in ["happy", "relaxed", "aa", "ih", "ou", "ee", "oh"]:
        expr = getattr(expressions.preset, name)
        print("EXPR", name, "binds", len(expr.morph_target_binds))
        for bind in expr.morph_target_binds:
            print("  BIND", bind.node.mesh_object_name, bind.index, bind.weight)
    print("CUSTOM LEN", len(expressions.custom))
    print("CUSTOM METHODS", [n for n in dir(expressions.custom) if not n.startswith("_")][:50])


if __name__ == "__main__":
    main()

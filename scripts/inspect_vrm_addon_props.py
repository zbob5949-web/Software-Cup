import json
import sys
from pathlib import Path

import addon_utils
import bpy


def serializable(value, depth=0):
    if depth > 3:
        return str(type(value).__name__)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [serializable(v, depth + 1) for v in value[:20]]
    if hasattr(value, "keys"):
        return {k: serializable(value[k], depth + 1) for k in list(value.keys())[:30]}
    attrs = {}
    for name in dir(value):
        if name.startswith("_"):
            continue
        if name in {"bl_rna", "rna_type"}:
            continue
        try:
            v = getattr(value, name)
        except Exception:
            continue
        if callable(v):
            continue
        if isinstance(v, (str, int, float, bool)) or hasattr(v, "__len__"):
            attrs[name] = serializable(v, depth + 1)
    return attrs


def main():
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    in_path = Path(args[0]).resolve()
    out_path = Path(args[1]).resolve()
    addon_utils.enable("bl_ext.user_default.vrm", default_set=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    bpy.ops.import_scene.vrm(filepath=str(in_path))
    ext = bpy.context.scene.vrm_addon_extension
    out = {
        "scene_vrm_addon_extension": serializable(ext),
        "objects": [
            {
                "name": obj.name,
                "props": [p for p in dir(obj) if "vrm" in p.lower()],
            }
            for obj in bpy.context.scene.objects
        ],
    }
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()

import json
import sys
from pathlib import Path

import bpy


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Usage: blender --background --python inspect_vrm_in_blender.py -- <vrm_path> <out_json>")
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    vrm_path = Path(args[0]).resolve()
    out_path = Path(args[1]).resolve()

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    try:
        bpy.ops.import_scene.vrm(filepath=str(vrm_path))
    except Exception:
        bpy.ops.import_scene.gltf(filepath=str(vrm_path))

    objects = []
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        keys = []
        if obj.data.shape_keys and obj.data.shape_keys.key_blocks:
            keys = [key.name for key in obj.data.shape_keys.key_blocks]
        objects.append(
            {
                "name": obj.name,
                "type": obj.type,
                "vertex_count": len(obj.data.vertices),
                "shape_keys": keys,
            }
        )

    out_path.write_text(json.dumps(objects, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()

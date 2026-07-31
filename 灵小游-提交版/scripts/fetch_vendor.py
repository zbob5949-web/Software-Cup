"""一次性下载前端依赖到 app/digital_human/vendor/，避免依赖外网 CDN。

国内可访问的镜像源：
  - registry.npmmirror.com (阿里云 npm 镜像)
  - fastly.jsdelivr.net (Fastly 节点, 国内通畅)

用法：
    python scripts/fetch_vendor.py

成功后, 数字人前端不再依赖任何外部 CDN, 满足赛题"系统稳定"要求。
"""
from __future__ import annotations

import sys
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "app" / "digital_human" / "vendor"

NPM_MIRROR = "https://registry.npmmirror.com"
JSD_FASTLY = "https://fastly.jsdelivr.net/npm"

# (源 URL, 落地相对路径)
ASSETS = [
    # three.js core + 用到的 addon
    (f"{NPM_MIRROR}/three/0.160.0/files/build/three.module.js",
     "three/build/three.module.js"),
    (f"{NPM_MIRROR}/three/0.160.0/files/examples/jsm/loaders/GLTFLoader.js",
     "three/examples/jsm/loaders/GLTFLoader.js"),
    (f"{NPM_MIRROR}/three/0.160.0/files/examples/jsm/controls/OrbitControls.js",
     "three/examples/jsm/controls/OrbitControls.js"),
    (f"{NPM_MIRROR}/three/0.160.0/files/examples/jsm/utils/BufferGeometryUtils.js",
     "three/examples/jsm/utils/BufferGeometryUtils.js"),

    # @pixiv/three-vrm — 单文件 bundle
    (f"{NPM_MIRROR}/@pixiv/three-vrm/2.0.7/files/lib/three-vrm.module.js",
     "three-vrm/three-vrm.module.js"),

    # pixi.js (Live2D 用)
    (f"{NPM_MIRROR}/pixi.js/5.3.12/files/dist/pixi.min.js",
     "pixi/pixi.min.js"),

    # pixi-live2d-display 不在 npmmirror unpkg 白名单, 用 jsdelivr fastly
    (f"{JSD_FASTLY}/pixi-live2d-display@0.4.0/dist/cubism4.min.js",
     "pixi-live2d-display/cubism4.min.js"),
]


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={"User-Agent": "lingshan-guide-vendor-fetch"})
    with urlopen(req, timeout=60) as resp:
        data = resp.read()
    dest.write_bytes(data)
    print(f"  ✓ {dest.relative_to(VENDOR)}  ({len(data)/1024:.1f} KB)")


def main() -> int:
    print(f"[fetch_vendor] 目标目录: {VENDOR}")
    VENDOR.mkdir(parents=True, exist_ok=True)
    failed = []
    for url, rel in ASSETS:
        dest = VENDOR / rel
        try:
            download(url, dest)
        except Exception as e:
            print(f"  ✗ {rel}  ←  {url}\n    {e}")
            failed.append(rel)
    if failed:
        print(f"\n[fetch_vendor] {len(failed)} 个文件下载失败, 请检查网络后重试。")
        return 1
    print(f"\n[fetch_vendor] 全部 {len(ASSETS)} 个依赖下载完成。")
    return 0


if __name__ == "__main__":
    sys.exit(main())

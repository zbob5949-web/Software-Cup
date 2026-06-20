# 灵小游 VRM 口型 BlendShape 修改方案

## 结论

当前模型 `app/digital_human/灵小游.vrm` 是 VRoid Studio 2.13.0 导出的 VRM 1.0 模型。

模型可以改口型，因为脸部 mesh `Face (merged)(Clone)` 已经带有 57 个 morph target / shape key。当前项目使用的 VRM 标准口型绑定如下：

| VRM 表情 | Shape Key | Index |
| --- | --- | --- |
| `aa` | `Fcl_MTH_A` | 39 |
| `ih` | `Fcl_MTH_I` | 40 |
| `ou` | `Fcl_MTH_U` | 41 |
| `ee` | `Fcl_MTH_E` | 42 |
| `oh` | `Fcl_MTH_O` | 43 |

已有嘴部相关 shape keys：

`Fcl_MTH_Close`, `Fcl_MTH_Up`, `Fcl_MTH_Down`, `Fcl_MTH_Angry`, `Fcl_MTH_Small`, `Fcl_MTH_Large`, `Fcl_MTH_Neutral`, `Fcl_MTH_Fun`, `Fcl_MTH_Joy`, `Fcl_MTH_Sorrow`, `Fcl_MTH_Surprised`, `Fcl_MTH_SkinFung`, `Fcl_MTH_SkinFung_R`, `Fcl_MTH_SkinFung_L`, `Fcl_MTH_A`, `Fcl_MTH_I`, `Fcl_MTH_U`, `Fcl_MTH_E`, `Fcl_MTH_O`

缺失中文口型：

- `mbp`：闭唇，适配 m/b/p
- `fv`：唇齿音，适配 f
- `szh`：齿音/咬合，适配 s/z/c
- `chsh`：翘舌/收口，适配 zh/ch/sh/r
- `nltk`：舌尖音近似，适配 d/t/n/l/g/k/h

## 推荐目标

不要重做整个人物模型，只改脸部 shape keys 和 VRM expression 绑定。

最终新增自定义 expressions：

| 新 expression | 用途 | 推荐基础 |
| --- | --- | --- |
| `mbp` | 双唇闭合 | 从 `Fcl_MTH_Close` 复制 |
| `fv` | 上齿轻触下唇 | 从 `Fcl_MTH_I` + `Fcl_MTH_Close` 混合后微调 |
| `szh` | 齿音，嘴窄、牙齿轻露 | 从 `Fcl_MTH_I` 复制后压低开口 |
| `chsh` | 翘舌/收口 | 从 `Fcl_MTH_U` + `Fcl_MTH_I` 混合 |
| `wideSmile` 可选 | 友好讲解时的微笑口型 | 从 `Fcl_MTH_Joy` 复制 |

## Blender 操作步骤

### 1. 安装工具

1. 安装 Blender 4.x。
2. 安装 VRM Add-on for Blender。
3. 备份原文件：
   - 原始：`app/digital_human/灵小游.vrm`
   - 备份：`app/digital_human/灵小游.backup.vrm`

### 2. 导入模型

1. Blender 菜单选择 `File > Import > VRM`。
2. 导入 `app/digital_human/灵小游.vrm`。
3. 在 Outliner 中找到脸部对象，通常名为：
   - `Face (merged)(Clone)`
   - 或类似包含 `Face` 的 mesh

### 3. 查看现有 Shape Keys

1. 选中 Face mesh。
2. 右侧面板进入 `Object Data Properties`。
3. 找到 `Shape Keys`。
4. 检查是否存在：
   - `Fcl_MTH_A`
   - `Fcl_MTH_I`
   - `Fcl_MTH_U`
   - `Fcl_MTH_E`
   - `Fcl_MTH_O`
   - `Fcl_MTH_Close`

### 4. 新增 `mbp`

1. 将 `Fcl_MTH_Close` 的值设为 `1.0`，其他 shape key 设为 `0`。
2. 在 Shape Keys 下拉菜单选择 `New Shape from Mix`。
3. 重命名为 `Fcl_MTH_MBP`。
4. 选中 `Fcl_MTH_MBP`，进入 Edit Mode。
5. 调整嘴部顶点：
   - 上下唇完全贴合
   - 嘴角不要过度上扬
   - 口腔内部尽量不可见
   - 不要影响鼻子、眼睛、脸颊

### 5. 新增 `fv`

1. 将 `Fcl_MTH_I = 0.35`，`Fcl_MTH_Close = 0.55`。
2. `New Shape from Mix`。
3. 重命名为 `Fcl_MTH_FV`。
4. Edit Mode 微调：
   - 下唇稍微向内/向上
   - 上齿区域轻微可见
   - 嘴不要大开
   - 形状比 `mbp` 松一点

### 6. 新增 `szh`

1. 将 `Fcl_MTH_I = 0.45`，`Fcl_MTH_Close = 0.25`。
2. `New Shape from Mix`。
3. 重命名为 `Fcl_MTH_SZH`。
4. Edit Mode 微调：
   - 嘴横向略展
   - 上下牙接近
   - 开口很小
   - 适合 `s/z/c` 和部分 `j/q/x`

### 7. 新增 `chsh`

1. 将 `Fcl_MTH_U = 0.45`，`Fcl_MTH_I = 0.25`。
2. `New Shape from Mix`。
3. 重命名为 `Fcl_MTH_CHSH`。
4. Edit Mode 微调：
   - 嘴唇略圆
   - 开口小
   - 嘴角不要太扁
   - 适合 `zh/ch/sh/r`

### 8. 在 VRM 表情里绑定

使用 VRM Add-on 的 Expressions 面板：

1. 找到 `VRM > Expressions`。
2. 新增 Custom Expression：
   - `mbp`
   - `fv`
   - `szh`
   - `chsh`
3. 每个 expression 添加 Morph Target Bind：
   - Node: Face mesh
   - Index/Shape Key: 对应新增 shape key
   - Weight: `1.0`
4. `overrideMouth` 建议保持 `none`，避免覆盖 `aa/ih/ou/ee/oh`。

### 9. 导出

1. `File > Export > VRM`。
2. 导出为：
   - `app/digital_human/灵小游_mouth_plus.vrm`
3. 不要直接覆盖原文件，先测试。

### 10. 接入前端

确认新 VRM 加载后，浏览器控制台应能看到 custom expressions。

然后前端需要扩展：

```js
const MOUTH_NAMES = ["aa", "ih", "ou", "ee", "oh", "mbp", "fv", "szh", "chsh"];
```

并在拼音映射里：

| 拼音声母/韵母 | expression |
| --- | --- |
| b/p/m | `mbp` |
| f | `fv` |
| s/z/c | `szh` |
| zh/ch/sh/r | `chsh` |
| a/ai/an/ang/ao | `aa` |
| i/in/ing | `ih` |
| u/ou/ong/uo | `ou` 或 `oh` |
| e/ei/en/eng/ie | `ee` |
| o/uo | `oh` |

## 判断是否改成功

改完后，在项目页面打开口型测试面板：

1. `妈 ma` 应先闭唇再张 `aa`。
2. `佛 fo` 应先出现唇齿/轻闭口，再转圆唇。
3. `山 shan` 应先收口/翘舌，再转 `aa`。
4. `寺 si` 应是轻咬合/扁口，而不是大张嘴。

如果新增 expression 在控制台清单里看不到，说明 VRM expression 没绑定成功，或者导出时 custom expression 被丢失。

## 注意事项

- 不建议直接修改 `aa/ih/ou/ee/oh` 太激进，否则基础 TTS 口型会崩。
- 新增辅音 expression 比重做元音更划算，因为当前最假的地方是 `m/b/p/f/s/sh` 这些音没有专用嘴型。
- 当前 VRM 模型仍然是二次元风格，无法达到 Sonic 那种视频级真实唇形；BlendShape 优化目标是“比赛演示更自然”，不是影视级口型。

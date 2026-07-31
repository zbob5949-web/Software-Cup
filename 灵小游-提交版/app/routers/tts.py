# ==================== 导入模块 ====================
import base64
import os
import re
import tempfile
from fastapi import HTTPException, APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import edge_tts
from app.services.digital_human_config import get_active_voice

try:
    from pypinyin import lazy_pinyin, Style
    PINYIN_OK = True
except ImportError:
    PINYIN_OK = False

router = APIRouter()

# ==================== 配置 ====================
TTS_VOICE = "zh-CN-XiaoyiNeural"   # 晓伊：年轻活泼
TTS_PITCH = "+15Hz"                # 微提音调，16岁不幼化


def _get_tts_rate() -> str:
    """从活跃数字人配置中读取语速，映射为 edge_tts rate 字符串"""
    try:
        profile = get_active_profile()
        speed = float(profile.get("speed", 1.0))
        # speed 0.5-2.0 → rate "-50%" 到 "+100%"
        rate_pct = int((speed - 1.0) * 100)
        return f"{rate_pct:+d}%"
    except Exception:
        return "+10%"


class TTSForm(BaseModel):
    text: str


def clean_text(text: str) -> str:
    """去掉 TTS 不应该朗读的内容：markdown、emoji、特殊符号，并规范化时间格式"""
    # Markdown 链接和图片
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)
    # Markdown 强调标记
    text = re.sub(r'\*{1,3}', '', text)
    text = re.sub(r'_{1,3}', '', text)
    text = re.sub(r'#+\s*', '', text)
    text = re.sub(r'`{1,3}', '', text)
    text = re.sub(r'~~', '', text)
    # 行首的列表标记（- 或数字序号）：移除标记符号保留内容
    text = re.sub(r'^\s*[-•‣◦]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+[.)]\s*', '', text, flags=re.MULTILINE)
    # Emoji 全覆盖：U+1F000-1FFFF (全部 Emoji+Pictographs 区块), U+2600-27BF, 杂项符号+变体选择器
    text = re.sub(r'[\U0001F000-\U0001FFFF☀-➿︀-️‍⃣]', '', text)
    # 其他符号：箭头、几何、星号装饰等（但保留中文标点）
    text = re.sub(r'[←↑→↓↔↕↖↗↘↙↩↪↶↷]', '', text)
    # 表格绘制字符 → 逗号
    text = re.sub(r'[|│├└─┼┤┬┴┌┐└┘]', '，', text)

    # ── 时间格式规范化（必须在换行→逗号之前）──
    # "10:00" / "10:35" → "10点" / "10点35分"
    # "09:00-17:00" → "9点到17点"
    text = re.sub(r'(\d{1,2}):(\d{2})', lambda m: (
        f"{int(m.group(1))}点" if m.group(2) == "00"
        else f"{int(m.group(1))}点{int(m.group(2))}分"
    ), text)
    # ── 破折号/短横线规范化（数字间→"到"，其余→逗号）──
    # "3-5小时" "6-7小时" "15-20分钟" 等数字范围 → "到"
    text = re.sub(r'(\d)\s*[-–—]\s*(\d)', r'\1到\2', text)
    # "9点-17点" "8点到18点" 等时间范围（含中文破折号/波浪号连接）
    text = re.sub(r'(\d+点)\s*[-–—~～]\s*(\d+点)', r'\1到\2', text)
    # 其余独立破折号/长划线 → 逗号
    text = re.sub(r'(?<!\d)\s*[-–—]{1,2}\s*(?!\d)', '，', text)

    # 换行 → 逗号
    text = re.sub(r'[\n\r]+', '，', text)
    # 压缩重复标点
    text = re.sub(r'，{2,}', '，', text)
    text = re.sub(r'。{2,}', '。', text)
    # 括号内是纯数字/编号时去掉括号（如 "(1) "）
    text = re.sub(r'[（(]\d+[)）]\s*', '', text)
    return text.strip('，。 ')


def build_pinyin_track(text: str) -> list:
    """对每个字符给出拼音 (无声调) + 是否标点; 用于前端口型时间轴.

    返回每项形如: {"c": "你", "py": "ni", "rest": false}
    rest=True 表示标点/空白, 前端会让嘴闭合短暂停顿.
    """
    track = []
    if not PINYIN_OK:
        # 兜底: 没装 pypinyin 时退化, 前端会用旧字典
        for ch in text[:500]:
            is_punct = bool(re.match(r"[，。！？、；：,.!?;:\s]", ch))
            track.append({"c": ch, "py": "" if is_punct else ch.lower(),
                          "rest": is_punct})
        return track

    # pypinyin: 一次性把整句转成拼音, 连续汉字会按上下文走分词更准
    chars = list(text[:500])
    py_list = lazy_pinyin(chars, style=Style.NORMAL, errors=lambda x: [c for c in x])
    for ch, py in zip(chars, py_list):
        is_punct = bool(re.match(r"[，。！？、；：,.!?;:\s]", ch))
        # ASCII / 数字保持小写, 标点/空白置空
        if is_punct:
            py = ""
        elif re.match(r"[a-zA-Z]", ch):
            py = ch.lower()
        track.append({"c": ch, "py": py, "rest": is_punct})
    return track


def _sapi_tts(text: str, output_path: str) -> None:
    """Edge TTS 不可用时使用 Windows 中文 SAPI，保证本地演示仍可播报。"""
    text_b64 = base64.b64encode(text.encode("utf-8")).decode("ascii")
    path_b64 = base64.b64encode(output_path.encode("utf-8")).decode("ascii")
    script = f"""
Add-Type -AssemblyName System.Speech
$text = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{text_b64}'))
$path = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('{path_b64}'))
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {{
  $synth.SelectVoice('Microsoft Huihui Desktop')
  $synth.Rate = 0
  $synth.Volume = 100
  $synth.SetOutputToWaveFile($path)
  $synth.Speak($text)
}} finally {{
  $synth.Dispose()
}}
"""
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded],
        capture_output=True,
        text=True,
        timeout=45,
    )
    if result.returncode != 0 or not os.path.exists(output_path) or os.path.getsize(output_path) < 100:
        detail = (result.stderr or result.stdout or "SAPI 未生成音频").strip()
        raise RuntimeError(detail)


def _estimate_mp3_duration_ms(data: bytes) -> int:
    """使用MPEG帧头计数估算MP3时长（毫秒），比固定时间分配精准很多。"""
    frames = 0
    i = 0
    sample_rate = 44100
    ver = 3  # 默认 MPEG1
    while i < len(data) - 3:
        # 寻找帧同步字 0xFFE0
        if data[i] == 0xFF and (data[i + 1] & 0xE0) == 0xE0:
            ver = (data[i + 1] >> 3) & 0x03
            layer = (data[i + 1] >> 1) & 0x03
            if layer == 1:  # Layer 3
                sr_idx = (data[i + 2] >> 2) & 0x03
                bitrate_idx = (data[i + 2] >> 4) & 0x0F
                pad = (data[i + 2] >> 1) & 0x01
                if ver == 3:  # MPEG1
                    rates = [44100, 48000, 32000]
                    sample_rate = rates[sr_idx] if sr_idx < 3 else 44100
                    bitrates = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 0]
                    bitrate = bitrates[bitrate_idx] if bitrate_idx < 16 else 128
                    frame_bytes = int(144 * bitrate * 1000 / sample_rate) + pad
                else:
                    rates = [22050, 24000, 16000]
                    sample_rate = rates[sr_idx] if sr_idx < 3 else 22050
                    bitrates = [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160, 0]
                    bitrate = bitrates[bitrate_idx] if bitrate_idx < 16 else 64
                    frame_bytes = int(72 * bitrate * 1000 / sample_rate) + pad
                frames += 1
                i += max(frame_bytes, 1)
            else:
                i += 1
        else:
            i += 1
    if frames > 0:
        samples_per_frame = 1152 if ver == 3 else 576
        return int(frames * samples_per_frame * 1000 / sample_rate)
    return 0


@router.post("/api/tts")
async def text_to_speech(form: TTSForm):
    text = form.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="文本不能为空")

    text = clean_text(text)
    # 按句子边界截断，避免硬切导致说到一半突然中断
    if len(text) > 500:
        # 在最后一个完整句号/问号/感叹号处截断
        cut = text[:500]
        last_period = max(cut.rfind('。'), cut.rfind('？'), cut.rfind('！'), cut.rfind('，'))
        if last_period > 200:
            text = cut[:last_period + 1]
        else:
            text = cut

    tmp_path = None
    try:
        try:
            communicate = edge_tts.Communicate(
                text=text,
                voice=get_active_voice(),
                rate=_get_tts_rate(),
                pitch=TTS_PITCH,
            )
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
            tmp_path = tmp.name
            tmp.close()
            await communicate.save(tmp_path)
            audio_mime = "audio/mpeg"
        except Exception as edge_error:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            tmp_path = tempfile.mktemp(suffix=".wav")
            try:
                _sapi_tts(text, tmp_path)
            except Exception as sapi_error:
                raise RuntimeError(f"Edge TTS: {edge_error}; Windows SAPI: {sapi_error}") from sapi_error
            audio_mime = "audio/wav"

        with open(tmp_path, "rb") as f:
            audio_bytes = f.read()

        # 估算音频时长（ms）：用MP3帧计数得到精确时长，供前端口型时间轴等比缩放
        duration = _estimate_mp3_duration_ms(audio_bytes) if audio_mime == "audio/mpeg" else 0
        if duration <= 0:
            # 回退：中文字数 × 220ms
            duration = max(len([c for c in text if '一' <= c <= '鿿']) * 220, 1000)

        return JSONResponse({
            "audio": base64.b64encode(audio_bytes).decode("ascii"),
            "audio_mime": audio_mime,
            "pinyin": build_pinyin_track(text),
            "text": text,
            "duration": duration,
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"语音合成失败: {str(e)}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
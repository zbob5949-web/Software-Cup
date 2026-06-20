# ==================== 导入模块 ====================
import base64
import os
import re
import tempfile
from fastapi import HTTPException, APIRouter
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import edge_tts

try:
    from pypinyin import lazy_pinyin, Style
    PINYIN_OK = True
except ImportError:
    PINYIN_OK = False

router = APIRouter()

# ==================== 配置 ====================
TTS_VOICE = "zh-CN-XiaoyiNeural"   # 晓伊：年轻活泼
TTS_RATE = "+10%"
TTS_PITCH = "+15Hz"                # 微提音调，16岁不幼化


class TTSForm(BaseModel):
    text: str


def clean_text(text: str) -> str:
    """去掉 TTS 不应该朗读的内容"""
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'\*{1,3}', '', text)
    text = re.sub(r'_{1,3}', '', text)
    text = re.sub(r'#+\s*', '', text)
    text = re.sub(r'`{1,3}', '', text)
    text = re.sub(r'~~', '', text)
    text = re.sub(r'[|│├└─┼┤┬┴┌┐└┘]', '，', text)
    text = re.sub(r'[\n\r]+', '，', text)
    text = re.sub(r'，{2,}', '，', text)
    text = re.sub(r'。{2,}', '。', text)
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


@router.post("/api/tts")
async def text_to_speech(form: TTSForm):
    text = form.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="文本不能为空")

    text = clean_text(text)
    if len(text) > 500:
        text = text[:500]

    try:
        communicate = edge_tts.Communicate(
            text=text,
            voice=TTS_VOICE,
            rate=TTS_RATE,
            pitch=TTS_PITCH,
        )
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tmp_path = tmp.name
        tmp.close()
        await communicate.save(tmp_path)

        with open(tmp_path, "rb") as f:
            audio_bytes = f.read()
        os.unlink(tmp_path)

        # 同时返回拼音序列, 让前端拿去算口型时间轴
        # 用 JSON + base64 一次返回, 避免再发第二次请求
        return JSONResponse({
            "audio": base64.b64encode(audio_bytes).decode("ascii"),
            "audio_mime": "audio/mpeg",
            "pinyin": build_pinyin_track(text),
            "text": text,
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"语音合成失败: {str(e)}")

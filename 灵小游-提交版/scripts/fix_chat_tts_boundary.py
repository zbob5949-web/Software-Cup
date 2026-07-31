from pathlib import Path

path = Path('frontend/src/pages/ChatPage.tsx')
s = path.read_text(encoding='utf-8')
old = '''    try {
      setPlayingId(messageId);
      setDhStatus('speaking');
      const tts = await textToSpeech(finalChunks.length > 1 ? finalChunks[0] : text);

      const frame = dhFrameRef.current?.contentWindow;
      if (frame) {
        // ── 走 Live2D 口型同步路径 ──
        // 用 postMessage 把文本按句子拆分逐条发给 Live2D iframe
        const chunks = text.split(/(?<=[。！？!?])/).map(s => s.trim()).filter(Boolean);
        const finalChunks = chunks.length > 0 ? chunks : [text];
'''
new = '''    try {
      setPlayingId(messageId);
      setDhStatus('speaking');
      const chunks = text.split(/(?<=[。！？!?])/).map(s => s.trim()).filter(Boolean);
      const finalChunks = chunks.length > 0 ? chunks : [text];
      const tts = await textToSpeech(finalChunks.length > 1 ? finalChunks[0] : text);

      const frame = dhFrameRef.current?.contentWindow;
      if (frame) {
        // ── 走 Live2D 口型同步路径 ──
        // 用 postMessage 把文本按句子拆分逐条发给 Live2D iframe
'''
if old not in s:
    raise RuntimeError('TTS block not found')
path.write_text(s.replace(old, new, 1), encoding='utf-8')

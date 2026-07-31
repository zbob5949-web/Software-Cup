from pathlib import Path

path = Path('frontend/src/pages/ChatPage.tsx')
s = path.read_text(encoding='utf-8')
old = '''      const tts = await textToSpeech(finalChunks.length > 1 ? finalChunks[0] : text);

      const frame = dhFrameRef.current?.contentWindow;'''
new = '''      const tts = await textToSpeech(finalChunks.length > 1 ? finalChunks[0] : text);
      if (mutedRef.current) {
        setPlayingId(null);
        setDhStatus('idle');
        return;
      }

      const frame = dhFrameRef.current?.contentWindow;'''
if old not in s: raise RuntimeError('TTS await boundary not found')
s = s.replace(old, new, 1)
s = s.replace('            if (settled) break;\n            const chunkTTS', '            if (settled || mutedRef.current) break;\n            const chunkTTS', 1)
path.write_text(s, encoding='utf-8')

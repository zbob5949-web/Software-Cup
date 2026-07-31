from pathlib import Path

chat = Path('frontend/src/pages/ChatPage.tsx')
s = chat.read_text(encoding='utf-8')
s = s.replace('  const [muted, setMuted] = useState(false);', '  const [muted, setMuted] = useState(false);\n  const mutedRef = useRef(false);')
s = s.replace('    if (muted) return;', '    if (muted || mutedRef.current) return;', 1)
s = s.replace('const tts = await textToSpeech(text);', 'const tts = await textToSpeech(finalChunks.length > 1 ? finalChunks[0] : text);', 1)
s = s.replace('            const next = !muted;\n            setMuted(next);', '            const next = !muted;\n            mutedRef.current = next;\n            setMuted(next);')
s = s.replace('              window.speechSynthesis?.cancel();', "              window.speechSynthesis?.cancel();\n              dhFrameRef.current?.contentWindow?.postMessage({ type: 'digital-human-mute' }, '*');")
s = s.replace('  const [userInterests, setUserInterests] = useState<string[]>([]);', '  const [userInterests, setUserInterests] = useState<string[]>([]);\n  const [showInterestTags, setShowInterestTags] = useState(false);')
start = s.index('      {/* ── Interest tags ── */}')
end = s.index('      {/* ── Floating shortcuts ── */}', start)
replacement = '''      {/* ── Interest tags ── */}
      <section className="ai-chat-interest-panel">
        <button type="button" className="ai-chat-interest-toggle" onClick={() => setShowInterestTags((open) => !open)} aria-expanded={showInterestTags}>
          <span><strong>个性化偏好</strong><small>用于推荐，不是景点快捷入口</small></span><span>{showInterestTags ? '收起 ▲' : '展开 ▼'}</span>
        </button>
        {showInterestTags ? <div className="ai-chat-interest-tags">
          {interestTags.map(tag => <button key={tag.key} className={`ai-chat-interest-tag ${userInterests.includes(tag.key) ? 'ai-cs-active' : ''}`} onClick={() => toggleInterest(tag.key)}><span className="ai-chat-shortcut-icon">{tag.icon}</span><span className="ai-chat-shortcut-label">{tag.label}</span></button>)}
          {userInterests.length > 0 ? <span className="ai-chat-interest-confirm">✓ 已选择 {userInterests.length} 项偏好</span> : null}
        </div> : null}
      </section>

'''
s = s[:start] + replacement + s[end:]
chat.write_text(s, encoding='utf-8')

bundle = next(Path('app/digital_human/live2d_host/live2d/dist/assets').glob('*.js'))
s = bundle.read_text(encoding='utf-8')
old = 'const e=t.data;if(e&&e.type==="digital-human-speak"&&e.audio){'
new = 'const e=t.data;if(e&&e.type==="digital-human-mute"){this._clearSpeechState();return}if(e&&e.type==="digital-human-speak"&&e.audio){'
if old not in s: raise RuntimeError('Live2D message handler not found')
bundle.write_text(s.replace(old, new, 1), encoding='utf-8')

from pathlib import Path
import re

def write(path, text):
    Path(path).write_text(text, encoding='utf-8')

avatar = Path('frontend/src/pages/admin/AvatarManage.tsx')
s = avatar.read_text(encoding='utf-8')
s = s.replace("const nativeVoiceOptions = ['温柔女声', '知性女声', '沉稳男声', '亲切男声'];", "const nativeVoiceOptions = [\n  { value: 'zh-CN-XiaoyiNeural', label: '清亮活泼' },\n  { value: 'zh-CN-XiaoxiaoNeural', label: '清新温柔' },\n  { value: 'zh-CN-XiaohanNeural', label: '中年女播音' },\n  { value: 'zh-CN-YunxiNeural', label: '亲切男声' },\n];")
s = s.replace("if (v.includes('Xiaohan')) return '知性沉稳';", "if (v.includes('Xiaohan')) return '中年女播音';")
s = s.replace('<select className="admin-form-select" value={config.voiceType} disabled>\n                {nativeVoiceOptions.map(v => <option key={v} value={v}>{v}</option>)}\n              </select>', '<select className="admin-form-select" value={config.voiceType} onChange={(event) => setConfig((current) => ({ ...current, voiceType: event.target.value }))}>\n                {nativeVoiceOptions.map((voice) => <option key={voice.value} value={voice.value}>{voice.label}</option>)}\n              </select>\n              <button type="button" className="admin-btn admin-btn-primary" onClick={() => void updateAvatarConfig({ name: config.name, welcome_message: config.welcomeMessage, introduction: config.introduction, video_url: config.videoUrl, voice_type: config.voiceType, speed: config.speed, volume: config.volume })}>保存音色</button>')
write(avatar, s)

ticket = Path('frontend/src/pages/TicketPage.tsx')
s = ticket.read_text(encoding='utf-8')
s = s.replace('type TicketProduct = { id: string; name: string; price: number; note: string };', 'type TicketProduct = { id: string; name: string; price: number; note: string; ticket_type?: string };')
s = s.replace("  { id: '16', name: '灵山胜境门票 + 观光车联票', price: 225, note: '包含景区门票和观光车服务。' },\n];", "  { id: '16', name: '灵山胜境门票 + 观光车联票', price: 225, note: '包含景区门票和观光车服务。', ticket_type: '联票' },\n];\nconst fallbackServices: TicketProduct[] = [\n  { id: '9001', name: '素面', price: 35, note: '景区内清淡素食，方便快捷。', ticket_type: '餐食服务' },\n  { id: '9002', name: '素斋', price: 50, note: '体验佛门饮食文化的素斋套餐。', ticket_type: '餐食服务' },\n  { id: '9003', name: '导游服务', price: 300, note: '景区历史文化深度讲解服务。', ticket_type: '导游服务' },\n];")
s = s.replace("  const [products, setProducts] = useState<TicketProduct[]>(fallbackProducts);\n  const [selected, setSelected] = useState('16');", "  const [products, setProducts] = useState<TicketProduct[]>(fallbackProducts);\n  const [services, setServices] = useState<TicketProduct[]>(fallbackServices);\n  const [selected, setSelected] = useState('16');")
s = s.replace('const product = useMemo(() => products.find((item) => item.id === selected) ?? products[0], [products, selected]);', 'const product = useMemo(() => [...products, ...services].find((item) => item.id === selected) ?? products[0], [products, services, selected]);')
s = s.replace("      if (items.length) { setProducts(items); setSelected((current) => items.some((item) => item.id === current) ? current : items[0].id); }", "      const ticketItems = items.filter((item) => !['餐食服务', '导游服务'].includes(item.ticket_type || ''));\n      const serviceItems = items.filter((item) => ['餐食服务', '导游服务'].includes(item.ticket_type || ''));\n      if (ticketItems.length) setProducts(ticketItems);\n      if (serviceItems.length) setServices(serviceItems);\n      const available = [...(ticketItems.length ? ticketItems : products), ...(serviceItems.length ? serviceItems : services)];\n      if (available.length) setSelected((current) => available.some((item) => item.id === current) ? current : available[0].id);")
pattern = re.compile(r'<section className="ticket-section"><h2>选择票种</h2>.*?</section><section className="ticket-section"><h2>游客信息</h2>', re.S)
replacement = '<div className="ticket-purchase-grid"><section className="ticket-section"><h2>选择票种</h2><div className="ticket-products">{products.map((item) => <button type="button" key={item.id} className={`ticket-product${selected === item.id ? \' selected\' : \'\'}`} onClick={() => setSelected(item.id)}><span><strong>{item.name}</strong><small>{item.note}</small></span><b>¥{item.price}</b></button>)}</div></section><section className="ticket-section ticket-service-section"><h2>导游餐食服务</h2><p className="ticket-section-hint">按需选择素食或景区导游服务</p><div className="ticket-products">{services.map((item) => <button type="button" key={item.id} className={`ticket-product${selected === item.id ? \' selected\' : \'\'}`} onClick={() => setSelected(item.id)}><span><strong>{item.name}</strong><small>{item.note}</small></span><b>¥{item.price}</b></button>)}</div></section></div><section className="ticket-section"><h2>游客信息</h2>'
s, n = pattern.subn(replacement, s, count=1)
if n != 1: raise RuntimeError('ticket section not found')
write(ticket, s)

chat = Path('frontend/src/pages/ChatPage.tsx')
s = chat.read_text(encoding='utf-8')
s = s.replace('  const [muted, setMuted] = useState(false);', '  const [muted, setMuted] = useState(false);\n  const mutedRef = useRef(false);')
s = s.replace('    if (muted) return;', '    if (muted || mutedRef.current) return;', 1)
s = s.replace('const tts = await textToSpeech(text);', 'const tts = await textToSpeech(finalChunks.length > 1 ? finalChunks[0] : text);', 1)
s = s.replace('            const next = !muted;\n            setMuted(next);', '            const next = !muted;\n            mutedRef.current = next;\n            setMuted(next);')
s = s.replace('              window.speechSynthesis?.cancel();', "              window.speechSynthesis?.cancel();\n              dhFrameRef.current?.contentWindow?.postMessage({ type: 'digital-human-mute' }, '*');")
s = s.replace('  const [userInterests, setUserInterests] = useState<string[]>([]);', '  const [userInterests, setUserInterests] = useState<string[]>([]);\n  const [showInterestTags, setShowInterestTags] = useState(false);')
pattern = re.compile(r'      /\* ── Interest tags ── \*/\n      <div className="ai-chat-shortcuts".*?</div>\n\n      /\* ── Floating shortcuts ── \*/', re.S)
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

      {/* ── Floating shortcuts ── */}'''
s, n = pattern.subn(replacement, s, count=1)
if n != 1: raise RuntimeError('interest tag block not found')
write(chat, s)

bundle = next(Path('app/digital_human/live2d_host/live2d/dist/assets').glob('*.js'))
s = bundle.read_text(encoding='utf-8')
old = 'const e=t.data;if(e&&e.type==="digital-human-speak"&&e.audio){'
new = 'const e=t.data;if(e&&e.type==="digital-human-mute"){this._clearSpeechState();return}if(e&&e.type==="digital-human-speak"&&e.audio){'
if old not in s: raise RuntimeError('Live2D message handler not found')
write(bundle, s.replace(old, new, 1))

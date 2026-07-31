from pathlib import Path

path = Path('frontend/src/styles.css')
s = path.read_text(encoding='utf-8')
css = '''

/* Purchase services and preference controls. */
.ticket-purchase-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 16px; align-items: start; }
.ticket-service-section { border-left: 3px solid #d6a84f; }
.ticket-section-hint { margin: -7px 0 12px; color: var(--text-secondary, #6b7280); font-size: 13px; }
.ai-chat-interest-panel { margin: 10px 16px 4px; border: 1px solid rgba(104, 200, 169, .35); border-radius: 10px; background: #fbfefb; overflow: hidden; }
.ai-chat-interest-toggle { width: 100%; display: flex; justify-content: space-between; align-items: center; gap: 12px; border: 0; background: transparent; color: #166b5b; padding: 10px 13px; cursor: pointer; text-align: left; }
.ai-chat-interest-toggle span:first-child { display: grid; gap: 3px; }
.ai-chat-interest-toggle small { color: #789287; font-size: 11px; font-weight: 400; }
.ai-chat-interest-tags { display: flex; flex-wrap: wrap; gap: 6px; padding: 0 10px 10px; border-top: 1px solid rgba(104, 200, 169, .18); }
.ai-chat-interest-tags .ai-chat-interest-tag { margin-top: 8px; }
.ai-chat-interest-confirm { align-self: center; color: #168b75; font-size: 12px; }
@media (max-width: 700px) { .ticket-purchase-grid { grid-template-columns: 1fr; } .ticket-service-section { border-left: 0; border-top: 3px solid #d6a84f; } }
'''
if '/* Purchase services and preference controls. */' not in s:
    path.write_text(s + css, encoding='utf-8')

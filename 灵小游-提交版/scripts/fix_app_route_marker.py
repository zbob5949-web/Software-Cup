from pathlib import Path

path = Path('frontend/src/App.tsx')
text = path.read_text(encoding='utf-8')
text = text.replace('`r`n', '\n')
path.write_text(text, encoding='utf-8')

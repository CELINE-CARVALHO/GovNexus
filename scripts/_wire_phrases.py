import re
from pathlib import Path

root = Path(r"a:/schemesathi/frontend")
pattern = re.compile(r"<script src=\"([^\"]*?)localization\.js\"></script>")
for path in root.rglob("*.html"):
    text = path.read_text(encoding="utf-8")
    if "phrases.js" in text:
        continue
    match = pattern.search(text)
    if not match:
        print("skip", path)
        continue
    prefix = match.group(1)
    insert = f"<script src=\"{prefix}phrases.js\"></script>\n  {match.group(0)}"
    text = pattern.sub(insert, text, count=1)
    path.write_text(text, encoding="utf-8")
    print("updated", path)

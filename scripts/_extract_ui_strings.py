import re
import pathlib

root = pathlib.Path(r"a:/schemesathi/frontend")
texts = set()
for p in root.rglob("*.html"):
    html = p.read_text(encoding="utf-8", errors="ignore")
    html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.I)
    for t in re.findall(r">([^<]{2,200})<", html):
        s = " ".join(t.split())
        if re.search(r"[A-Za-z]{3,}", s):
            texts.add(s)
    for t in re.findall(r'placeholder="([^"]+)"', html):
        texts.add(t)
    for t in re.findall(r'aria-label="([^"]+)"', html):
        texts.add(t)
out = pathlib.Path(r"a:/schemesathi/scripts/_ui_strings.txt")
out.write_text("\n".join(sorted(texts, key=str.lower)), encoding="utf-8")
print(len(texts))

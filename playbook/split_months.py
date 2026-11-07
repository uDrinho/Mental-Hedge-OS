"""Divide o acervo em arquivos mensais compactos (texto) para análise por subagentes."""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
BASE = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "chunks"
OUT.mkdir(parents=True, exist_ok=True)

tweets = json.load(open(BASE / "mentalhedgebr_1_ano_tweets.json", encoding="utf-8"))
by_month = defaultdict(list)
for t in tweets:
    by_month[t.get("created_at_iso", "")[:7]].append(t)

for month, items in sorted(by_month.items()):
    items.sort(key=lambda x: x.get("created_at_iso", ""))
    lines = []
    for t in items:
        m = t.get("metrics") or {}
        kind = "RESPOSTA a @" + t["in_reply_to_screen_name"] if t.get("in_reply_to_screen_name") and t["in_reply_to_screen_name"].lower() != "mentalhedgebr" else ("THREAD" if t.get("in_reply_to_screen_name") else "POST")
        lines.append(f"### {t['created_at_iso'][:16]} | id {t['id']} | {kind} | likes {m.get('likes', '?')} | bookmarks {m.get('bookmarks', '?')}")
        lines.append(t.get("text", "").strip())
        if t.get("quoted_text"):
            lines.append(f"[CITA @{t.get('quoted_author')}]: {t['quoted_text'].strip()}")
        for it in t.get("image_transcriptions", []):
            if it.get("transcription"):
                lines.append(f"[IMAGEM {Path(it['image']).name}]: {it['transcription'].strip()}")
        lines.append("")
    path = OUT / f"{month}.txt"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"{month}: {len(items)} tweets, {path.stat().st_size // 1024} KB")

import json
import os
from pathlib import Path
import datetime

BASE_DIR = Path(__file__).parent.resolve()
RAW_JSON_PATH = BASE_DIR / "tweets_raw.json"
TRANSCRIPTIONS_PATH = BASE_DIR / "image_transcriptions.json"
OUTPUT_MD_PATH = BASE_DIR / "mentalhedgebr_1_ano_tweets.md"
OUTPUT_JSON_PATH = BASE_DIR / "mentalhedgebr_1_ano_tweets.json"


def load_json(path: Path) -> dict:
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Erro ao carregar {path}: {e}")
    return {}


def load_all_transcriptions() -> dict:
    merged = {}
    for p in sorted(BASE_DIR.glob("transcriptions_part*.json")):
        merged.update(load_json(p))
    merged.update(load_json(TRANSCRIPTIONS_PATH))
    return merged


def build_exports():
    tweets = load_json(RAW_JSON_PATH)
    transcriptions = load_all_transcriptions()

    sorted_tweets = sorted(
        tweets.values(),
        key=lambda t: t.get("created_at_iso", ""),
        reverse=True,
    )

    total_imgs = 0
    transcribed_imgs = 0
    for t in sorted_tweets:
        for img in t.get("local_images", []):
            total_imgs += 1
            lpath = img.get("local_path", "").replace("\\", "/")
            fname = Path(lpath).name
            if transcriptions.get(fname) or transcriptions.get(lpath):
                transcribed_imgs += 1

    enriched_list = []
    md_lines = [
        "# Arquivo Completo de Tweets — @mentalhedgebr (Último 1 Ano)",
        "",
        f"- **Perfil**: [https://x.com/mentalhedgebr](https://x.com/mentalhedgebr)",
        f"- **Período coberto**: 01/11/2025 a 02/11/2026 (1 ano completo)",
        f"- **Total de tweets coletados**: {len(sorted_tweets)}",
        f"- **Imagens de tweets transcritas**: {transcribed_imgs} / {total_imgs} (Total no acervo: {len(transcriptions)})",
        f"- **Última atualização**: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        "",
        "---",
        "",
    ]

    for idx, t in enumerate(sorted_tweets, start=1):
        tid = t.get("id", "")
        url = t.get("url", f"https://x.com/mentalhedgebr/status/{tid}")
        dt_iso = t.get("created_at_iso", "")
        dt_display = dt_iso
        try:
            dt_obj = datetime.datetime.fromisoformat(dt_iso)
            dt_display = dt_obj.strftime("%d/%m/%Y %H:%M:%S UTC")
        except Exception:
            pass

        text = t.get("text", "").strip()
        quoted_author = t.get("quoted_author", "")
        quoted_text = t.get("quoted_text", "").strip()
        metrics = t.get("metrics", {})
        local_images = t.get("local_images", [])

        md_lines.append(f"## {idx}. Tweet `{tid}` — {dt_display}")
        md_lines.append(f"- **Link**: [{url}]({url})")
        if metrics:
            likes = metrics.get("likes", 0)
            rts = metrics.get("retweets", 0)
            replies = metrics.get("replies", 0)
            bookmarks = metrics.get("bookmarks", 0)
            views = metrics.get("views", "N/A")
            md_lines.append(
                f"- **Métricas**: ❤️ {likes} | 🔁 {rts} | 💬 {replies} | 🔖 {bookmarks} | 👁️ {views}"
            )
        md_lines.append("")
        md_lines.append("### Texto do Post")
        md_lines.append(text if text else "*(Sem texto)*")
        md_lines.append("")

        if quoted_text:
            md_lines.append(f"> **Post citado (@{quoted_author})**:")
            for qline in quoted_text.splitlines():
                md_lines.append(f"> {qline}")
            md_lines.append("")

        tweet_transcriptions = []
        if local_images:
            md_lines.append("### Imagens e Transcrição / Análise Visual")
            for img in local_images:
                lpath = img.get("local_path", "").replace("\\", "/")
                fname = Path(lpath).name
                desc = transcriptions.get(fname) or transcriptions.get(lpath) or ""
                tweet_transcriptions.append(
                    {
                        "image": lpath,
                        "transcription": desc,
                    }
                )
                md_lines.append(f"- **Arquivo de Imagem**: `{lpath}`")
                if desc:
                    md_lines.append(f"  - **Transcrição / Interpretação da Imagem**:\n")
                    for dline in desc.splitlines():
                        md_lines.append(f"    {dline}")
                else:
                    md_lines.append("  - **Transcrição / Interpretação da Imagem**: *(Aguardando processamento visual)*")
                md_lines.append("")

        md_lines.append("---")
        md_lines.append("")

        t_copy = dict(t)
        t_copy["image_transcriptions"] = tweet_transcriptions
        enriched_list.append(t_copy)

    tmp_md = OUTPUT_MD_PATH.with_suffix(f".md.{os.getpid()}.tmp")
    with open(tmp_md, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    os.replace(tmp_md, OUTPUT_MD_PATH)

    tmp_json = OUTPUT_JSON_PATH.with_suffix(f".json.{os.getpid()}.tmp")
    with open(tmp_json, "w", encoding="utf-8") as f:
        json.dump(enriched_list, f, ensure_ascii=False, indent=2)
    os.replace(tmp_json, OUTPUT_JSON_PATH)

    print(f"[OK] Exportados {len(sorted_tweets)} tweets ({transcribed_imgs}/{total_imgs} imagens de tweets do ano transcritas, {len(transcriptions)} total)")


if __name__ == "__main__":
    build_exports()

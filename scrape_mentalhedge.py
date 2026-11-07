import asyncio
import datetime
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from playwright.async_api import async_playwright
from export_markdown import build_exports

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).parent.resolve()
IMAGES_DIR = BASE_DIR / "images"
RAW_JSON_PATH = BASE_DIR / "tweets_raw.json"
USER_DATA_DIR = BASE_DIR / "browser_session"
CDP_URL = "http://127.0.0.1:9222"

TARGET_USER = "mentalhedgebr"


def log(msg: str):
    print(msg, flush=True)


def load_saved_tweets() -> dict:
    if RAW_JSON_PATH.exists():
        try:
            with open(RAW_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception as e:
            log(f"[WARN] Erro ao ler {RAW_JSON_PATH}: {e}")
    return {}


def save_tweets(tweets_dict: dict):
    sorted_items = dict(
        sorted(
            tweets_dict.items(),
            key=lambda item: item[1].get("created_at_iso", ""),
            reverse=True,
        )
    )
    tmp_path = RAW_JSON_PATH.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(sorted_items, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, RAW_JSON_PATH)
    try:
        build_exports()
    except Exception as e:
        log(f"[WARN] Erro ao atualizar export markdown: {e}")


def download_image(url: str, tweet_id: str, idx: int) -> str | None:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    clean_url = url
    ext = "jpg"
    if "format=png" in url or url.endswith(".png"):
        ext = "png"
    if "pbs.twimg.com/media/" in url:
        base_part = url.split("?")[0]
        if "." in base_part.split("/")[-1]:
            ext = base_part.split(".")[-1]
            base_part = base_part.rsplit(".", 1)[0]
        clean_url = f"{base_part}?format={ext}&name=large"

    filename = f"{tweet_id}_{idx}.{ext}"
    filepath = IMAGES_DIR / filename
    if filepath.exists() and filepath.stat().st_size > 0:
        return str(filepath.relative_to(BASE_DIR))

    try:
        req = urllib.request.Request(
            clean_url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
            },
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
            if data:
                with open(filepath, "wb") as out:
                    out.write(data)
                return str(filepath.relative_to(BASE_DIR))
    except Exception as e:
        log(f"[WARN] Falha ao baixar imagem {clean_url}: {e}")
    return None


def parse_twitter_date(date_str: str) -> str:
    try:
        dt = datetime.datetime.strptime(date_str, "%a %b %d %H:%M:%S %z %Y")
        return dt.isoformat()
    except Exception:
        return date_str


def extract_tweet_from_result(result: dict, tweets_dict: dict, min_date: datetime.date | None = None):
    if not isinstance(result, dict):
        return
    typename = result.get("__typename")
    if typename == "TweetWithVisibilityResults" and "tweet" in result:
        result = result["tweet"]

    legacy = result.get("legacy")
    core = result.get("core")
    if not legacy or not isinstance(legacy, dict):
        return

    screen_name = ""
    try:
        user_results = core.get("user_results", {}).get("result", {})
        screen_name = (
            user_results.get("legacy", {}).get("screen_name")
            or user_results.get("core", {}).get("screen_name")
            or ""
        )
    except Exception:
        pass

    if screen_name and screen_name.lower() != TARGET_USER.lower():
        return

    tweet_id = legacy.get("id_str") or result.get("rest_id")
    if not tweet_id:
        return

    is_retweet = "retweeted_status_result" in legacy

    full_text = ""
    try:
        note_text = (
            result.get("note_tweet", {})
            .get("note_tweet_results", {})
            .get("result", {})
            .get("text")
        )
        if note_text:
            full_text = note_text
    except Exception:
        pass

    if not full_text:
        full_text = legacy.get("full_text", "")

    created_at_raw = legacy.get("created_at", "")
    created_at_iso = parse_twitter_date(created_at_raw)

    if min_date and created_at_iso:
        try:
            dt_date = datetime.datetime.fromisoformat(created_at_iso).date()
            if dt_date < (min_date - datetime.timedelta(days=2)):
                return
        except Exception:
            pass

    media_list = []
    extended_media = legacy.get("extended_entities", {}).get("media", [])
    if not extended_media:
        extended_media = legacy.get("entities", {}).get("media", [])

    for m in extended_media:
        m_type = m.get("type", "photo")
        m_url = m.get("media_url_https") or m.get("media_url")
        if m_url:
            media_list.append({"type": m_type, "url": m_url})

    quoted_text = ""
    quoted_author = ""
    try:
        q_res = result.get("quoted_status_result", {}).get("result", {})
        if q_res.get("__typename") == "TweetWithVisibilityResults":
            q_res = q_res.get("tweet", {})
        q_legacy = q_res.get("legacy", {})
        quoted_text = q_legacy.get("full_text", "")
        q_user = q_res.get("core", {}).get("user_results", {}).get("result", {})
        quoted_author = (
            q_user.get("legacy", {}).get("screen_name")
            or q_user.get("core", {}).get("screen_name")
            or ""
        )
        q_media = q_legacy.get("extended_entities", {}).get("media", [])
        for m in q_media:
            m_type = m.get("type", "photo")
            m_url = m.get("media_url_https") or m.get("media_url")
            if m_url and not any(x["url"] == m_url for x in media_list):
                media_list.append({"type": f"quoted_{m_type}", "url": m_url})
    except Exception:
        pass

    views_count = None
    try:
        views_count = result.get("views", {}).get("count")
    except Exception:
        pass

    existing = tweets_dict.get(tweet_id, {})
    if existing and len(existing.get("text", "")) > len(full_text):
        full_text = existing["text"]

    local_images = existing.get("local_images", [])
    if media_list and len(local_images) < len(media_list):
        local_images = []
        for idx, m_item in enumerate(media_list, start=1):
            local_rel = download_image(m_item["url"], tweet_id, idx)
            if local_rel:
                local_images.append(
                    {
                        "index": idx,
                        "type": m_item["type"],
                        "remote_url": m_item["url"],
                        "local_path": local_rel,
                    }
                )

    tweets_dict[tweet_id] = {
        "id": tweet_id,
        "url": f"https://x.com/{TARGET_USER}/status/{tweet_id}",
        "created_at_raw": created_at_raw,
        "created_at_iso": created_at_iso,
        "text": full_text,
        "is_retweet": is_retweet,
        "in_reply_to_status_id": legacy.get("in_reply_to_status_id_str"),
        "in_reply_to_screen_name": legacy.get("in_reply_to_screen_name"),
        "conversation_id": legacy.get("conversation_id_str"),
        "quoted_author": quoted_author,
        "quoted_text": quoted_text,
        "metrics": {
            "likes": legacy.get("favorite_count", 0),
            "retweets": legacy.get("retweet_count", 0),
            "replies": legacy.get("reply_count", 0),
            "quotes": legacy.get("quote_count", 0),
            "bookmarks": legacy.get("bookmark_count", 0),
            "views": views_count,
        },
        "media": media_list,
        "local_images": local_images,
        "source": "graphql",
    }


def walk_graphql_json(obj, tweets_dict: dict, min_date: datetime.date | None = None):
    if isinstance(obj, dict):
        if (
            obj.get("__typename") in ("Tweet", "TweetWithVisibilityResults")
            or ("legacy" in obj and "rest_id" in obj)
        ):
            extract_tweet_from_result(obj, tweets_dict, min_date=min_date)
        for v in obj.values():
            walk_graphql_json(v, tweets_dict, min_date=min_date)
    elif isinstance(obj, list):
        for item in obj:
            walk_graphql_json(item, tweets_dict, min_date=min_date)


async def extract_dom_tweets(page, tweets_dict: dict):
    try:
        articles = await page.query_selector_all('article[data-testid="tweet"]')
        for art in articles:
            try:
                links = await art.query_selector_all('a[href*="/status/"]')
                tweet_id = None
                for lnk in links:
                    href = await lnk.get_attribute("href")
                    if href and "/status/" in href:
                        m = re.search(r"/([^/]+)/status/(\d+)", href)
                        if m:
                            u, tid = m.group(1), m.group(2)
                            if u.lower() == TARGET_USER.lower():
                                tweet_id = tid
                                break
                if not tweet_id:
                    continue

                if tweet_id in tweets_dict and tweets_dict[tweet_id].get("source") == "graphql":
                    continue

                time_el = await art.query_selector("time")
                dt_iso = await time_el.get_attribute("datetime") if time_el else ""

                text_el = await art.query_selector('div[data-testid="tweetText"]')
                text_val = await text_el.inner_text() if text_el else ""

                img_els = await art.query_selector_all('div[data-testid="tweetPhoto"] img')
                media_list = []
                local_images = []
                for idx, img_el in enumerate(img_els, start=1):
                    src = await img_el.get_attribute("src")
                    if src and "pbs.twimg.com/media/" in src:
                        media_list.append({"type": "photo", "url": src})
                        local_rel = download_image(src, tweet_id, idx)
                        if local_rel:
                            local_images.append(
                                {
                                    "index": idx,
                                    "type": "photo",
                                    "remote_url": src,
                                    "local_path": local_rel,
                                }
                            )

                tweets_dict[tweet_id] = {
                    "id": tweet_id,
                    "url": f"https://x.com/{TARGET_USER}/status/{tweet_id}",
                    "created_at_raw": dt_iso,
                    "created_at_iso": dt_iso,
                    "text": text_val,
                    "is_retweet": False,
                    "in_reply_to_status_id": None,
                    "in_reply_to_screen_name": None,
                    "conversation_id": tweet_id,
                    "quoted_author": "",
                    "quoted_text": "",
                    "metrics": {},
                    "media": media_list,
                    "local_images": local_images,
                    "source": "dom",
                }
            except Exception:
                continue
    except Exception:
        pass


async def scroll_until_exhausted(page, tweets_dict: dict, label: str, max_scrolls: int = 80):
    no_new_count = 0
    last_count = len(tweets_dict)
    last_height = 0

    for step in range(1, max_scrolls + 1):
        await extract_dom_tweets(page, tweets_dict)
        current_count = len(tweets_dict)
        if current_count > last_count:
            log(f"  [{label}] Scroll {step}: {current_count} tweets totais (+{current_count - last_count} novos)")
            save_tweets(tweets_dict)
            last_count = current_count
            no_new_count = 0
        else:
            no_new_count += 1

        empty_el = await page.query_selector('div[data-testid="emptyState"]')
        if empty_el:
            log(f"  [{label}] Sem mais resultados nesta janela.")
            break

        retry_btn = await page.query_selector('button:has-text("Retry"), button:has-text("Tentar novamente")')
        if retry_btn:
            log(f"  [{label}] Rate limit temporário (Retry). Aguardando 20s...")
            await asyncio.sleep(20)
            try:
                await retry_btn.click()
            except Exception:
                pass

        await page.evaluate("window.scrollBy(0, 1600)")
        await asyncio.sleep(1.8)

        new_height = await page.evaluate("document.body.scrollHeight")
        if new_height == last_height and no_new_count >= 6:
            log(f"  [{label}] Fim da página alcançado no scroll {step}.")
            break
        last_height = new_height


def get_reference_end_date(tweets_dict: dict) -> datetime.date:
    dates = []
    for t in tweets_dict.values():
        iso = t.get("created_at_iso", "")
        if iso:
            try:
                dates.append(datetime.datetime.fromisoformat(iso).date())
            except Exception:
                pass
    if dates:
        return max(dates)
    return datetime.date.today()


def is_cdp_ready() -> bool:
    try:
        with urllib.request.urlopen(f"{CDP_URL}/json/version", timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


async def main():
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    tweets_dict = load_saved_tweets()
    log(f"[INFO] Tweets já salvos anteriormente: {len(tweets_dict)}")

    min_date_filter = None

    log("[AGUARDANDO NAVEGADOR] Aguardando o navegador abrir na porta 9222 (execute ./1_abrir_navegador_login.sh no Linux ou 1_abrir_edge_login.bat no Windows)...")
    for w in range(300):
        if is_cdp_ready():
            log("[OK] Conexão com o navegador detectada na porta 9222!")
            break
        await asyncio.sleep(2)
    else:
        log("[ERRO] Porta 9222 não respondeu após 10 minutos.")
        return

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP_URL)
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        page = context.pages[0] if context.pages else await context.new_page()

        async def handle_response(response):
            url = response.url
            if "/graphql/" in url and any(
                ep in url
                for ep in (
                    "UserTweets",
                    "SearchTimeline",
                    "TweetDetail",
                    "UserMedia",
                )
            ):
                try:
                    data = await response.json()
                    before = len(tweets_dict)
                    walk_graphql_json(data, tweets_dict, min_date=min_date_filter)
                    after = len(tweets_dict)
                    if after > before:
                        log(f"  [GraphQL] +{after - before} tweets capturados (Total: {after})")
                        save_tweets(tweets_dict)
                except Exception:
                    pass

        page.on("response", handle_response)

        if "x.com" not in page.url:
            await page.goto(f"https://x.com/{TARGET_USER}", wait_until="domcontentloaded")
            await asyncio.sleep(3)

        log("[INFO] Verificando se você está logado no X...")
        logged_in = False
        for wait_idx in range(300):
            switcher = await page.query_selector(
                '[data-testid="SideNav_AccountSwitcher_Button"], [data-testid="AppTabBar_Home_Link"]'
            )
            if switcher:
                logged_in = True
                break
            if wait_idx % 5 == 0:
                log(
                    f"[AGUARDANDO LOGIN] Faça login na janela do Edge aberta ({wait_idx*2}s)..."
                )
            await asyncio.sleep(2)

        if logged_in:
            log("[OK] Login confirmado! Iniciando varredura completa de 1 ano do @mentalhedgebr...")
        else:
            log("[AVISO] Continuando sem confirmação de login...")

        await page.goto(f"https://x.com/{TARGET_USER}", wait_until="domcontentloaded")
        await asyncio.sleep(5)
        await extract_dom_tweets(page, tweets_dict)
        save_tweets(tweets_dict)

        ref_end_date = get_reference_end_date(tweets_dict)
        ref_start_date = ref_end_date - datetime.timedelta(days=366)
        min_date_filter = ref_start_date
        log(f"[DATA DE REFERÊNCIA] Último tweet detectado em: {ref_end_date.isoformat()}")
        log(f"[JANELA DE 1 ANO] Coletando de {ref_start_date.isoformat()} até {ref_end_date.isoformat()}")

        for tab_name, tab_url in [
            ("Perfil Principal", f"https://x.com/{TARGET_USER}"),
            ("Aba Mídia (Fotos/Gráficos)", f"https://x.com/{TARGET_USER}/media"),
            ("Aba Com Respostas/Threads", f"https://x.com/{TARGET_USER}/with_replies"),
        ]:
            log(f"\n=== Etapa 1: Varrendo {tab_name} ({tab_url}) ===")
            await page.goto(tab_url, wait_until="domcontentloaded")
            await asyncio.sleep(4)
            await scroll_until_exhausted(page, tweets_dict, tab_name, max_scrolls=60)
            save_tweets(tweets_dict)

        ref_end_date = get_reference_end_date(tweets_dict)
        ref_start_date = ref_end_date - datetime.timedelta(days=366)
        min_date_filter = ref_start_date

        log(f"\n=== Etapa 2: Busca Fatiada por Período ({ref_start_date} a {ref_end_date}) ===")
        cursor_end = ref_end_date + datetime.timedelta(days=2)
        window_days = 15

        while cursor_end > ref_start_date:
            cursor_start = max(ref_start_date, cursor_end - datetime.timedelta(days=window_days))
            q = f"from:{TARGET_USER} since:{cursor_start.isoformat()} until:{cursor_end.isoformat()}"
            encoded_q = urllib.parse.quote(q)
            search_url = f"https://x.com/search?q={encoded_q}&src=typed_query&f=live"
            label = f"{cursor_start.isoformat()}..{cursor_end.isoformat()}"
            log(f"\n---> Janela de busca: {label}")
            await page.goto(search_url, wait_until="domcontentloaded")
            await asyncio.sleep(4)
            await scroll_until_exhausted(page, tweets_dict, label, max_scrolls=45)
            save_tweets(tweets_dict)
            cursor_end = cursor_start

        filtered = {}
        for tid, t in tweets_dict.items():
            iso = t.get("created_at_iso", "")
            keep = True
            if iso:
                try:
                    dt_d = datetime.datetime.fromisoformat(iso).date()
                    if dt_d < ref_start_date:
                        keep = False
                except Exception:
                    pass
            if keep:
                filtered[tid] = t

        save_tweets(filtered)
        log(f"\n[CONCLUÍDO] Coleta finalizada com sucesso! Total de tweets de 1 ano salvos: {len(filtered)}")


if __name__ == "__main__":
    asyncio.run(main())

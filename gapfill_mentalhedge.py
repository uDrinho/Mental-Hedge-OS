"""Recoleta lacunas: varre janelas de 3 dias nos períodos com poucos tweets,
com pausas longas quando o X aplica rate limit.

Uso: execute 1_abrir_edge_login.bat, faça login, depois rode este script.
"""
import asyncio
import datetime
import json
import sys
import urllib.parse
from collections import Counter

from playwright.async_api import async_playwright

import scrape_mentalhedge as sm

WINDOW_DAYS = 3
MIN_TWEETS_PER_WINDOW = 6  # janelas abaixo disso são recoletadas


def daily_counts(tweets):
    c = Counter()
    for t in tweets.values():
        iso = t.get("created_at_iso", "")
        if iso:
            try:
                c[datetime.datetime.fromisoformat(iso.replace("Z", "+00:00")).date()] += 1
            except Exception:
                pass
    return c


def find_gap_windows(tweets, start, end):
    counts = daily_counts(tweets)
    windows = []
    cur = start
    while cur < end:
        nxt = min(end, cur + datetime.timedelta(days=WINDOW_DAYS))
        total = sum(counts.get(cur + datetime.timedelta(days=i), 0) for i in range((nxt - cur).days))
        if total < MIN_TWEETS_PER_WINDOW:
            windows.append((cur, nxt, total))
        cur = nxt
    return windows


async def wait_rate_limit(page, label):
    """Se aparecer o botão Retry, espera progressivamente mais e tenta de novo."""
    for attempt, wait in enumerate([60, 120, 240, 480], start=1):
        btn = await page.query_selector('button:has-text("Retry"), button:has-text("Tentar novamente")')
        if not btn:
            return True
        sm.log(f"  [{label}] Rate limit. Pausa de {wait}s (tentativa {attempt})...")
        await asyncio.sleep(wait)
        try:
            await btn.click()
        except Exception:
            pass
        await asyncio.sleep(5)
    return await page.query_selector('button:has-text("Retry"), button:has-text("Tentar novamente")') is None


async def main():
    tweets = sm.load_saved_tweets()
    # remove registros-lixo (cards de link sem data)
    junk = [k for k, v in tweets.items() if not v.get("created_at_iso")]
    for k in junk:
        tweets.pop(k)
    sm.log(f"[INFO] {len(tweets)} tweets carregados ({len(junk)} registros-lixo removidos)")

    end = datetime.date(2026, 11, 3)
    start = datetime.date(2025, 11, 1)
    windows = find_gap_windows(tweets, start, end)
    sm.log(f"[INFO] {len(windows)} janelas de {WINDOW_DAYS} dias com menos de {MIN_TWEETS_PER_WINDOW} tweets:")
    for a, b, n in windows:
        sm.log(f"   {a} .. {b}: {n} tweets")

    sm.log("[AGUARDANDO] Execute ./1_abrir_navegador_login.sh (ou 1_abrir_edge_login.bat no Windows) na porta 9222...")
    for _ in range(900):
        if sm.is_cdp_ready():
            break
        await asyncio.sleep(2)
    else:
        sm.log("[ERRO] Navegador na porta 9222 não respondeu em 30 min.")
        return

    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(sm.CDP_URL)
        context = browser.contexts[0]
        page = context.pages[0] if context.pages else await context.new_page()

        async def on_response(response):
            if "/graphql/" in response.url and "SearchTimeline" in response.url:
                try:
                    data = await response.json()
                    before = len(tweets)
                    sm.walk_graphql_json(data, tweets, min_date=start)
                    if len(tweets) > before:
                        sm.log(f"  [GraphQL] +{len(tweets) - before} (total {len(tweets)})")
                        sm.save_tweets(tweets)
                except Exception:
                    pass

        page.on("response", on_response)

        for a, b, n in windows:
            q = f"from:{sm.TARGET_USER} since:{a.isoformat()} until:{b.isoformat()}"
            url = f"https://x.com/search?q={urllib.parse.quote(q)}&src=typed_query&f=live"
            label = f"{a}..{b}"
            sm.log(f"\n---> {label} (tinha {n})")
            await page.goto(url, wait_until="domcontentloaded")
            await asyncio.sleep(6)
            if not await wait_rate_limit(page, label):
                sm.log(f"  [{label}] Rate limit persistente. Pausa de 15 min antes de seguir.")
                await asyncio.sleep(900)
                await page.reload(wait_until="domcontentloaded")
                await asyncio.sleep(6)
            stale = 0
            last = len(tweets)
            for _ in range(40):
                await page.evaluate("window.scrollBy(0, 1600)")
                await asyncio.sleep(2.5)
                await wait_rate_limit(page, label)
                if await page.query_selector('div[data-testid="emptyState"]'):
                    break
                if len(tweets) == last:
                    stale += 1
                    if stale >= 6:
                        break
                else:
                    stale, last = 0, len(tweets)
            sm.save_tweets(tweets)
            await asyncio.sleep(8)  # respiro entre janelas

        sm.save_tweets(tweets)
        remaining = find_gap_windows(tweets, start, end)
        sm.log(f"\n[CONCLUÍDO] Total: {len(tweets)} tweets. Janelas ainda baixas: {len(remaining)}")
        for a, b, n in remaining:
            sm.log(f"   {a} .. {b}: {n}")


if __name__ == "__main__":
    asyncio.run(main())

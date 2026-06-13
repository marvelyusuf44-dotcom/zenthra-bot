from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import aiohttp
import asyncio
from datetime import datetime

def _back_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Back to Menu", callback_data="main_menu")]
    ])

async def fetch_with_retry(url, retry=2):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    for attempt in range(retry):
        try:
            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as s:
                async with s.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as r:
                    if r.status == 200:
                        return await r.json()
        except:
            await asyncio.sleep(1)
    return None

async def fetch_fear_greed():
    try:
        data = await fetch_with_retry("https://api.alternative.me/fng/?limit=1")
        if data:
            return int(data["data"][0]["value"])
    except:
        pass
    return None

async def fetch_long_short():
    try:
        url = "https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol=BTCUSDT&period=1h&limit=1"
        data = await fetch_with_retry(url)
        if data and len(data) > 0:
            return float(data[0]["longShortRatio"]), float(data[0]["longAccount"]), float(data[0]["shortAccount"])
    except:
        pass
    return None, None, None

async def fetch_funding_rate():
    try:
        url = "https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT"
        data = await fetch_with_retry(url)
        if data:
            return float(data["lastFundingRate"]) * 100
    except:
        pass
    return None

async def fetch_btc_dominance():
    try:
        url = "https://api.coingecko.com/api/v3/global"
        data = await fetch_with_retry(url)
        if data:
            return float(data["data"]["market_cap_percentage"]["btc"])
    except:
        pass
    return None

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔄 Fetching market sentiment...")

    now = datetime.now().strftime("%d %b %Y · %H:%M UTC")

    # Fetch all data concurrently
    fng, ls, fr, btc_dom = await asyncio.gather(
        fetch_fear_greed(),
        fetch_long_short(),
        fetch_funding_rate(),
        fetch_btc_dominance()
    )

    # Fear & Greed interpretation
    if fng:
        if fng <= 20:
            fng_text = "😱 EXTREME FEAR"
            fng_score = f"[{fng}/100]"
        elif fng <= 40:
            fng_text = "😨 FEAR"
            fng_score = f"[{fng}/100]"
        elif fng <= 60:
            fng_text = "😐 NEUTRAL"
            fng_score = f"[{fng}/100]"
        elif fng <= 80:
            fng_text = "😊 GREED"
            fng_score = f"[{fng}/100]"
        else:
            fng_text = "🤑 EXTREME GREED"
            fng_score = f"[{fng}/100]"
    else:
        fng_text = "N/A"
        fng_score = ""

    # Build text
    lines = [f"🧠 <b>MARKET SENTIMENT</b>", "──────────────────────", ""]

    if fng:
        lines.append(f"{fng_text} {fng_score}")
        lines.append("")

        # Progress bar
        bar_len = 20
        filled = int(fng / 100 * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)
        lines.append(f"<pre>{bar}</pre>")
        lines.append("")
    else:
        lines.append("⚠️ Fear & Greed: N/A")
        lines.append("")

    if ls and len(ls) == 3:
        lr, long_pct, short_pct = ls
        lines.append(f"⚖️ Long/Short     : {lr:.2f}")
        lines.append(f"   └ Longs {long_pct:.1f}%  Shorts {short_pct:.1f}%")
    else:
        lines.append(f"⚖️ Long/Short     : N/A")

    if fr:
        lines.append(f"💸 Funding Rate   : {fr:.4f}%")
    else:
        lines.append(f"💸 Funding Rate   : N/A")

    if btc_dom:
        lines.append(f"₿  BTC Dominance  : {btc_dom:.1f}%")
    else:
        lines.append(f"₿  BTC Dominance  : N/A")

    lines.extend([
        "",
        "──────────────────────",
        f"📅 {now}"
    ])

    text = "\n".join(lines)
    await query.edit_message_text(text, reply_markup=_back_kb(), parse_mode="HTML")

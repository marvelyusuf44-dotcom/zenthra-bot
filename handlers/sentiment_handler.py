from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import aiohttp
from datetime import datetime

def _back_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Back to Menu", callback_data="main_menu")]
    ])

async def fetch_fear_greed():
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("https://api.alternative.me/fng/?limit=1", timeout=aiohttp.ClientTimeout(total=8)) as r:
                if r.status == 200:
                    data = await r.json()
                    return int(data["data"][0]["value"])
    except:
        pass
    return None

async def fetch_long_short():
    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as s:
            async with s.get("https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol=BTCUSDT&period=1h&limit=1", timeout=aiohttp.ClientTimeout(total=8)) as r:
                if r.status == 200:
                    data = await r.json()
                    return float(data[0]["longShortRatio"]), float(data[0]["longAccount"]), float(data[0]["shortAccount"])
    except:
        pass
    return None, None, None

async def fetch_funding_rate():
    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as s:
            async with s.get("https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT", timeout=aiohttp.ClientTimeout(total=8)) as r:
                if r.status == 200:
                    data = await r.json()
                    return float(data["lastFundingRate"]) * 100
    except:
        pass
    return None

async def fetch_btc_dominance():
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("https://api.coingecko.com/api/v3/global", timeout=aiohttp.ClientTimeout(total=8)) as r:
                if r.status == 200:
                    data = await r.json()
                    return round(data["data"]["market_cap_percentage"]["btc"], 1)
    except:
        pass
    return None

def calc_zenthra_score(fg, ls_ratio, funding, dominance):
    score = 0
    total_weight = 0

    # Fear & Greed (weight 30%)
    if fg is not None:
        score += fg * 0.30
        total_weight += 0.30

    # Long/Short Ratio (weight 30%)
    # ratio > 1 = more longs = bullish, scale 0-100
    if ls_ratio is not None:
        ls_score = min(ls_ratio / 2 * 100, 100)
        score += ls_score * 0.30
        total_weight += 0.30

    # Funding Rate (weight 25%)
    # positive funding = bullish, negative = bearish
    if funding is not None:
        funding_score = min(max((funding + 0.1) / 0.2 * 100, 0), 100)
        score += funding_score * 0.25
        total_weight += 0.25

    # BTC Dominance (weight 15%)
    # lower dominance = altseason = risk-on = bullish overall
    if dominance is not None:
        dom_score = max(0, 100 - dominance * 1.5)
        score += dom_score * 0.15
        total_weight += 0.15

    if total_weight == 0:
        return 50
    return round(score / total_weight)

def score_label(score):
    if score >= 75: return "🤑", "EXTREME GREED"
    if score >= 60: return "😄", "GREED"
    if score >= 45: return "😐", "NEUTRAL"
    if score >= 30: return "😨", "FEAR"
    return "😱", "EXTREME FEAR"

def score_bias(score):
    if score >= 70: return "⚠️ Extremely greedy — watch for reversal"
    if score >= 55: return "📈 Bullish bias — avoid FOMO entries"
    if score >= 45: return "↔️ Balanced — wait for confirmation"
    if score >= 30: return "📉 Bearish pressure — seek reversal signals"
    return "💎 Potential BOTTOM — smart money zone"

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔄 Loading sentiment data...")

    fg, (ls_ratio, long_pct, short_pct), funding, dominance = (
        await fetch_fear_greed(),
        await fetch_long_short(),
        await fetch_funding_rate(),
        await fetch_btc_dominance(),
    )

    now = datetime.now().strftime("%d %b %Y · %H:%M UTC")
    zenthra_score = calc_zenthra_score(fg, ls_ratio, funding, dominance)
    emoji, level = score_label(zenthra_score)
    bias = score_bias(zenthra_score)

    filled = round(zenthra_score / 5)
    bar = "█" * filled + "░" * (20 - filled)

    # Format each indicator
    fg_str = f"{fg}/100" if fg is not None else "N/A"

    if ls_ratio is not None:
        ls_bias = "Longs dominant" if ls_ratio > 1 else "Shorts dominant"
        ls_str = f"{ls_ratio:.2f} ({ls_bias})"
        long_str = f"{float(long_pct)*100:.1f}%"
        short_str = f"{float(short_pct)*100:.1f}%"
    else:
        ls_str = "N/A"
        long_str = "N/A"
        short_str = "N/A"

    if funding is not None:
        fund_bias = "Bullish 🟢" if funding > 0 else "Bearish 🔴"
        fund_str = f"{funding:+.4f}% ({fund_bias})"
    else:
        fund_str = "N/A"

    dom_str = f"{dominance}%" if dominance is not None else "N/A"

    text = (
        f"🧠 <b>MARKET SENTIMENT</b>\n"
        f"{'─'*22}\n\n"
        f"{emoji}  <b>{level}</b>\n\n"
        f"ZENTHRA Score\n"
        f"<code>[{bar}]</code>\n"
        f"<code>  {zenthra_score}/100</code>\n\n"
        f"{'─'*22}\n"
        f"😨 <b>Fear & Greed</b>   : {fg_str}\n"
        f"⚖️ <b>Long/Short</b>     : {ls_str}\n"
        f"   └ Longs {long_str}  Shorts {short_str}\n"
        f"💸 <b>Funding Rate</b>   : {fund_str}\n"
        f"₿  <b>BTC Dominance</b>  : {dom_str}\n"
        f"{'─'*22}\n"
        f"{bias}\n"
        f"{'─'*22}\n"
        f"<i>📅 {now}</i>"
    )

    await query.edit_message_text(text, reply_markup=_back_kb(), parse_mode="HTML")

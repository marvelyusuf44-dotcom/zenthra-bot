from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import aiohttp
import asyncio
from datetime import datetime
from config import BASE_REST

SCAN_PAIRS = [
    "BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT",
    "ADAUSDT","DOGEUSDT","AVAXUSDT","DOTUSDT","LINKUSDT",
    "LTCUSDT","UNIUSDT","ATOMUSDT","APTUSDT","ARBUSDT",
    "OPUSDT","INJUSDT","SUIUSDT","NEARUSDT","FETUSDT",
    "WIFUSDT","JUPUSDT","TIAUSDT","RENDERUSDT","LDOUSDT",
]

def _back_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Back to Menu", callback_data="main_menu")]
    ])

def fmt_vol(v):
    if v >= 1_000_000_000: return f"${v/1_000_000_000:.2f}B"
    if v >= 1_000_000:     return f"${v/1_000_000:.1f}M"
    if v >= 1_000:         return f"${v/1_000:.0f}K"
    return f"${v:.0f}"

async def fetch(session, url, params=None):
    try:
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status == 200:
                return await r.json()
    except:
        pass
    return None

async def get_oi_data(session, symbol):
    try:
        # OI sekarang
        oi_now = await fetch(session, f"{BASE_REST}/fapi/v1/openInterest", params={"symbol": symbol})
        if not oi_now:
            return None

        # OI history (1h interval, 2 data point untuk hitung perubahan)
        oi_hist = await fetch(session, f"{BASE_REST}/futures/data/openInterestHist",
                             params={"symbol": symbol, "period": "1h", "limit": 5})
        if not oi_hist or len(oi_hist) < 2:
            return None

        # Harga sekarang
        ticker = await fetch(session, f"{BASE_REST}/fapi/v1/ticker/price", params={"symbol": symbol})
        if not ticker:
            return None

        price     = float(ticker["price"])
        oi_usd    = float(oi_now["openInterest"]) * price
        oi_old    = float(oi_hist[-5]["sumOpenInterest"]) * price if len(oi_hist) >= 5 else oi_usd
        oi_change = ((oi_usd - oi_old) / oi_old * 100) if oi_old > 0 else 0

        # Price change 1h
        klines = await fetch(session, f"{BASE_REST}/fapi/v1/klines",
                            params={"symbol": symbol, "interval": "1h", "limit": 2})
        price_change = 0
        if klines and len(klines) >= 2:
            prev_close = float(klines[-2][4])
            price_change = (price - prev_close) / prev_close * 100

        return {
            "symbol": symbol.replace("USDT", ""),
            "price": price,
            "oi_usd": oi_usd,
            "oi_change": oi_change,
            "price_change": price_change,
        }
    except:
        return None

def interpret_oi(oi_change, price_change):
    """
    OI naik + Price naik = Long buildup (bullish)
    OI naik + Price turun = Short buildup (bearish)
    OI turun + Price naik = Short covering (bullish)
    OI turun + Price turun = Long liquidation (bearish)
    """
    if oi_change > 0 and price_change > 0:
        return "🟢 Long Buildup", "Bulls accumulating longs"
    elif oi_change > 0 and price_change < 0:
        return "🔴 Short Buildup", "Bears accumulating shorts"
    elif oi_change < 0 and price_change > 0:
        return "🟡 Short Covering", "Shorts being squeezed"
    else:
        return "🟠 Long Liquidation", "Longs being liquidated"

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔄 Scanning open interest data...")

    now = datetime.now().strftime("%d %b %Y · %H:%M UTC")

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        tasks = [get_oi_data(session, sym) for sym in SCAN_PAIRS]
        results = await asyncio.gather(*tasks)

    results = [r for r in results if r is not None]

    # Sort by absolute OI change
    results.sort(key=lambda x: abs(x["oi_change"]), reverse=True)
    top = results[:8]

    if not top:
        text = (
            f"📊 <b>OPEN INTEREST</b>\n"
            f"──────────────────────\n\n"
            f"⚠️ Unable to fetch OI data.\n"
            f"Please try again later.\n\n"
            f"<i>📅 {now}</i>"
        )
    else:
        lines = []
        for r in top:
            signal, desc = interpret_oi(r["oi_change"], r["price_change"])
            oi_arrow  = "▲" if r["oi_change"] >= 0 else "▼"
            oi_sign   = "+" if r["oi_change"] >= 0 else ""
            p_arrow   = "▲" if r["price_change"] >= 0 else "▼"
            p_sign    = "+" if r["price_change"] >= 0 else ""

            lines.append(
                f"{signal}\n"
                f"   <b>Pair</b>     : #{r['symbol']}USDT\n"
                f"   <b>OI Value</b> : {fmt_vol(r['oi_usd'])}\n"
                f"   <b>OI Change</b>: {oi_arrow}{oi_sign}{r['oi_change']:.1f}% (5H)\n"
                f"   <b>Price</b>    : {p_arrow}{p_sign}{r['price_change']:.2f}% (1H)\n"
                f"   <i>{desc}</i>"
            )

        text = (
            f"📊 <b>OPEN INTEREST SCANNER</b>\n"
            f"<i>Biggest OI moves — top pairs</i>\n"
            f"──────────────────────\n\n"
            + "\n\n".join(lines) +
            f"\n\n──────────────────────\n"
            f"🟢 Long Buildup  — bulls adding\n"
            f"🔴 Short Buildup — bears adding\n"
            f"🟡 Short Covering — squeeze up\n"
            f"🟠 Long Liquidation — squeeze down\n"
            f"──────────────────────\n"
            f"<i>📅 {now}</i>"
        )

    await query.edit_message_text(text, reply_markup=_back_kb(), parse_mode="HTML")

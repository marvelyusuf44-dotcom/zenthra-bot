from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import aiohttp

RANK_ICONS = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
LOSER_ICONS = ["💀","🔴","🔴","🟠","🟠","🟡","🟡","⬇️","⬇️","⬇️"]

MAJOR_COINS = {
    "BTC","ETH","SOL","BNB","XRP","ADA","DOGE","AVAX",
    "DOT","LINK","LTC","UNI","ATOM","FIL","APT","ARB",
    "OP","INJ","SUI","TIA","SEI","JUP","WIF","BONK",
    "PEPE","SHIB","FTM","NEAR","SAND","MANA","AXS",
    "MATIC","FET","RENDER","GRT","LDO","RUNE","AAVE",
    "MKR","SNX","CRV","1INCH","SUSHI","COMP","YFI",
}

def _back_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Back to Menu", callback_data="main_menu")]
    ])

def fmt_vol(v):
    if v >= 1_000_000_000: return f"${v/1_000_000_000:.1f}B"
    if v >= 1_000_000:     return f"${v/1_000_000:.0f}M"
    if v >= 1_000:         return f"${v/1_000:.0f}K"
    return f"${v:.0f}"

def fmt_price(p):
    if p >= 10000: return f"{p:,.0f}"
    if p >= 100:   return f"{p:,.2f}"
    if p >= 1:     return f"{p:,.3f}"
    if p >= 0.01:  return f"{p:.4f}"
    return f"{p:.6f}"

async def fetch_all_tickers():
    url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 200:
                    return await r.json()
    except:
        pass
    return None

def filter_major(tickers, min_vol=0):
    return [
        t for t in tickers
        if t["symbol"].endswith("USDT")
        and float(t["quoteVolume"]) >= min_vol
    ]

async def handle_trending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔄 Loading trending pairs...")
    tickers = await fetch_all_tickers()
    lines = []
    if tickers:
        data = []
        for t in filter_major(tickers, min_vol=50_000_000):
            pct = float(t["priceChangePercent"])
            vol = float(t["quoteVolume"])
            data.append((t["symbol"].replace("USDT",""), float(t["lastPrice"]), pct, vol, abs(pct)*vol))
        data.sort(key=lambda x: x[4], reverse=True)
        for i, (sym, price, pct, vol, _) in enumerate(data[:10]):
            arrow = "🔺" if pct >= 0 else "🔻"
            sign = "+" if pct >= 0 else ""
            lines.append(f"{RANK_ICONS[i]} <b>{sym}</b>  {arrow}<b>{sign}{pct:.1f}%</b>\n   💲 {fmt_price(price)}  •  Vol {fmt_vol(vol)}")
        status = "<i>Binance Futures • 24H</i>"
    else:
        status = "⚠️ <i>API unavailable</i>"
    text = (
        f"🚀 <b>TRENDING PAIRS</b>\n"
        f"<i>Volume × Momentum — Major coins only</i>\n"
        f"{'─'*22}\n\n"
        + ("\n\n".join(lines) if lines else "No data available")
        + f"\n\n{'─'*22}\n{status}"
    )
    await query.edit_message_text(text, reply_markup=_back_kb(), parse_mode="HTML")

async def handle_gainers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔄 Loading top gainers...")
    tickers = await fetch_all_tickers()
    lines = []
    if tickers:
        data = [(t["symbol"].replace("USDT",""), float(t["lastPrice"]), float(t["priceChangePercent"]), float(t["quoteVolume"])) for t in filter_major(tickers, min_vol=10_000_000)]
        data.sort(key=lambda x: x[2], reverse=True)
        for i, (sym, price, pct, vol) in enumerate(data[:10]):
            lines.append(f"{RANK_ICONS[i]} <b>{sym}</b>  🔺 <b>+{pct:.2f}%</b>\n   💲 {fmt_price(price)}  •  Vol {fmt_vol(vol)}")
        status = "<i>Binance Futures • 24H</i>"
    else:
        status = "⚠️ <i>API unavailable</i>"
    text = (
        f"📈 <b>TOP GAINERS 24H</b>\n"
        f"<i>Major coins — Min volume $10M</i>\n"
        f"{'─'*22}\n\n"
        + ("\n\n".join(lines) if lines else "No data available")
        + f"\n\n{'─'*22}\n{status}"
    )
    await query.edit_message_text(text, reply_markup=_back_kb(), parse_mode="HTML")

async def handle_losers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔄 Loading top losers...")
    tickers = await fetch_all_tickers()
    lines = []
    if tickers:
        data = [(t["symbol"].replace("USDT",""), float(t["lastPrice"]), float(t["priceChangePercent"]), float(t["quoteVolume"])) for t in filter_major(tickers, min_vol=10_000_000)]
        data.sort(key=lambda x: x[2])
        for i, (sym, price, pct, vol) in enumerate(data[:10]):
            lines.append(f"{LOSER_ICONS[i]} <b>{sym}</b>  🔻 <b>{pct:.2f}%</b>\n   💲 {fmt_price(price)}  •  Vol {fmt_vol(vol)}")
        status = "<i>Binance Futures • 24H</i>"
    else:
        status = "⚠️ <i>API unavailable</i>"
    text = (
        f"📉 <b>TOP LOSERS 24H</b>\n"
        f"<i>Major coins — Min volume $10M</i>\n"
        f"{'─'*22}\n\n"
        + ("\n\n".join(lines) if lines else "No data available")
        + f"\n\n{'─'*22}\n{status}"
    )
    await query.edit_message_text(text, reply_markup=_back_kb(), parse_mode="HTML")

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔄 Loading market data...")
    tickers = await fetch_all_tickers()
    if tickers:
        ticker_map = {t["symbol"]: t for t in tickers}
        def get_coin(sym):
            t = ticker_map.get(sym+"USDT", {})
            return float(t.get("lastPrice",0)), float(t.get("priceChangePercent",0)), float(t.get("quoteVolume",0))
        btc_p,btc_c,btc_v = get_coin("BTC")
        eth_p,eth_c,eth_v = get_coin("ETH")
        sol_p,sol_c,sol_v = get_coin("SOL")
        bnb_p,bnb_c,bnb_v = get_coin("BNB")
        total_vol = sum(float(t["quoteVolume"]) for t in tickers if t["symbol"].endswith("USDT"))
        def row(e, name, p, c, v):
            arrow = "▲" if c >= 0 else "▼"
            sign = "+" if c >= 0 else ""
            return (
                f"{e} <b>{name}</b>\n"
                f"   <b>Price</b>     : {fmt_price(p)} ({arrow}{sign}{c:.2f}%)\n"
                f"   <b>Volume</b>    : {fmt_vol(v)}"
            )
        bias = "🟢 BULLISH" if btc_c>2 else ("🔴 BEARISH" if btc_c<-2 else ("🟡 SIDEWAYS ↑" if btc_c>0 else "🟠 SIDEWAYS ↓"))
        vola = "🔥 EXTREME" if abs(btc_c)>5 else ("⚡ HIGH" if abs(btc_c)>3 else ("📊 NORMAL" if abs(btc_c)>1 else "😴 LOW"))
        btc_dom = f"{(btc_v/total_vol*100):.1f}%" if total_vol > 0 else "N/A"
        eth_dom = f"{(eth_v/total_vol*100):.1f}%" if total_vol > 0 else "N/A"
        text = (
            f"📊 <b>MARKET OVERVIEW</b>\n{'─'*22}\n\n"
            + row("₿","BITCOIN",btc_p,btc_c,btc_v)
            + f"\n   <b>Dominance</b> : {btc_dom}\n\n"
            + row("🔷","ETHEREUM",eth_p,eth_c,eth_v)
            + f"\n   <b>Dominance</b> : {eth_dom}\n\n"
            + row("◎","SOLANA",sol_p,sol_c,sol_v) + "\n\n"
            + row("🟡","BNB",bnb_p,bnb_c,bnb_v)
            + f"\n\n{'─'*22}\n"
            + f"🌐 <b>Bias</b>       : {bias}\n"
            + f"📊 <b>Volatility</b> : {vola}\n"
            + f"📦 <b>Total Vol</b>  : {fmt_vol(total_vol)}\n"
            + f"{'─'*22}\n"
            + f"<i>Binance Futures • Realtime</i>"
        )
    else:
        text = "⚠️ Unable to fetch market data. Please try again."
    await query.edit_message_text(text, reply_markup=_back_kb(), parse_mode="HTML")

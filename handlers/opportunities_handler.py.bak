from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import aiohttp
import asyncio
from datetime import datetime
from config import BASE_REST

def _back_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Back to Menu", callback_data="main_menu")]
    ])

async def fetch(session, url, params=None):
    try:
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status == 200:
                return await r.json()
    except:
        pass
    return None

def ema_list(values, period):
    if len(values) < period:
        return [values[-1]] * len(values)
    k = 2 / (period + 1)
    result = [values[0]]
    for v in values[1:]:
        result.append(v * k + result[-1] * (1 - k))
    return result

def calc_macd(closes):
    e12 = ema_list(closes, 12)
    e26 = ema_list(closes, 26)
    ml = [a - b for a, b in zip(e12, e26)]
    sl = ema_list(ml, 9)
    return [a - b for a, b in zip(ml, sl)]

def calc_adx(highs, lows, closes, period=14):
    try:
        pdm = [max(highs[i]-highs[i-1], 0) if highs[i]-highs[i-1] > lows[i-1]-lows[i] else 0 for i in range(1, len(closes))]
        mdm = [max(lows[i-1]-lows[i], 0) if lows[i-1]-lows[i] > highs[i]-highs[i-1] else 0 for i in range(1, len(closes))]
        trs = [max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])) for i in range(1, len(closes))]
        def sm(d):
            s = sum(d[:period]); r = [s]
            for x in d[period:]: s = s - s/period + x; r.append(s)
            return r
        at = sm(trs)
        pdi = [100*a/b if b else 0 for a, b in zip(sm(pdm), at)]
        mdi = [100*a/b if b else 0 for a, b in zip(sm(mdm), at)]
        dx = [100*abs(a-b)/(a+b) if a+b else 0 for a, b in zip(pdi, mdi)]
        adx_val = sum(dx[-period:])/period if len(dx) >= period else 0
        return adx_val, pdi[-1] if pdi else 0, mdi[-1] if mdi else 0
    except:
        return 0, 50, 50

def calc_wr(highs, lows, closes, period=14):
    wr = []
    for i in range(len(closes)):
        if i < period - 1:
            wr.append(-50)
            continue
        hh = max(highs[i-period+1:i+1])
        ll = min(lows[i-period+1:i+1])
        wr.append(-50 if hh == ll else ((hh - closes[i]) / (hh - ll)) * -100)
    return wr

def detect_swing_points(highs, lows, lookback=5):
    sh, sl = [], []
    for i in range(lookback, len(highs) - lookback):
        if highs[i] == max(highs[i-lookback:i+lookback+1]):
            sh.append((i, highs[i]))
        if lows[i] == min(lows[i-lookback:i+lookback+1]):
            sl.append((i, lows[i]))
    return sh, sl

def detect_fvg(opens, closes, highs, lows):
    for i in range(len(closes)-1, 1, -1):
        if lows[i] > highs[i-2]:
            return "bullish", highs[i-2], lows[i]
        elif highs[i] < lows[i-2]:
            return "bearish", highs[i], lows[i-2]
    return None, None, None

def detect_liq_sweep(highs, lows, closes):
    if len(highs) < 20:
        return None, None
    recent_high = max(highs[-20:-1])
    recent_low  = min(lows[-20:-1])
    if highs[-1] > recent_high and closes[-1] < recent_high:
        return "high", recent_high
    if lows[-1] < recent_low and closes[-1] > recent_low:
        return "low", recent_low
    return None, None

def detect_bos(closes, highs, lows):
    sh, sl = detect_swing_points(highs, lows)
    if len(sh) < 2 or len(sl) < 2:
        return None
    last_sh, prev_sh = sh[-1][1], sh[-2][1]
    last_sl, prev_sl = sl[-1][1], sl[-2][1]
    price = closes[-1]
    if last_sh > prev_sh and last_sl > prev_sl and price > last_sh:
        return "bullish"
    if last_sh < prev_sh and last_sl < prev_sl and price < last_sl:
        return "bearish"
    return None

def build_narrative(direction, pair, price, score, adx, hist, wr,
                    fvg_type, fvg_low, fvg_high, liq_side, liq_level, bos, vol_ratio):
    fmt = lambda x: f"{x:,.4f}" if x < 10 else (f"{x:,.2f}" if x < 1000 else f"{x:,.0f}")
    parts = []

    # Liquidity sweep
    if liq_side == "low":
        parts.append(f"Price swept liquidity below {fmt(liq_level)}, then reclaimed structure.")
    elif liq_side == "high":
        parts.append(f"Price swept liquidity above {fmt(liq_level)}, then rejected sharply.")

    # FVG
    if fvg_type == "bullish" and direction == "LONG":
        parts.append(f"Bullish FVG unfilled at {fmt(fvg_low)}–{fmt(fvg_high)} acting as support.")
    elif fvg_type == "bearish" and direction == "SHORT":
        parts.append(f"Bearish FVG unfilled at {fmt(fvg_low)}–{fmt(fvg_high)} acting as resistance.")

    # BOS
    if bos == "bullish" and direction == "LONG":
        parts.append(f"BOS confirmed bullish on 1H — higher high structure intact.")
    elif bos == "bearish" and direction == "SHORT":
        parts.append(f"BOS confirmed bearish on 1H — lower low structure forming.")

    # Momentum
    if direction == "LONG":
        if hist[-1] > 0 and hist[-1] > hist[-2]:
            parts.append(f"MACD momentum accelerating to the upside.")
        if wr[-1] < -70:
            parts.append(f"Williams %R oversold — reversal pressure building.")
    else:
        if hist[-1] < 0 and hist[-1] < hist[-2]:
            parts.append(f"MACD momentum accelerating to the downside.")
        if wr[-1] > -30:
            parts.append(f"Williams %R overbought — sell pressure increasing.")

    # Volume
    if vol_ratio > 1.5:
        parts.append(f"Volume spike {vol_ratio:.1f}x average confirms move.")

    # ADX
    if adx > 30:
        parts.append(f"Strong trend momentum — ADX at {adx:.0f}.")

    # Conclusion
    if score >= 6:
        parts.append(f"High probability {direction.lower()} setup.")
    elif score >= 4:
        parts.append(f"Moderate confidence {direction.lower()} setup — wait for confirmation.")
    else:
        parts.append(f"Early stage setup — proceed with caution.")

    return " ".join(parts[:4])  # max 4 kalimat biar tidak terlalu panjang

async def analyze_pair(session, symbol):
    try:
        data = await fetch(session, f"{BASE_REST}/fapi/v1/klines",
                          params={'symbol': symbol, 'interval': '1h', 'limit': 100})
        if not data or len(data) < 60:
            return None

        o = [float(x[1]) for x in data]
        h = [float(x[2]) for x in data]
        l = [float(x[3]) for x in data]
        c = [float(x[4]) for x in data]
        v = [float(x[5]) for x in data]

        price = c[-1]
        e9  = ema_list(c, 9)
        e21 = ema_list(c, 21)
        e50 = ema_list(c, 50)
        hist = calc_macd(c)
        adx_val, pdi, mdi = calc_adx(h, l, c)
        wr = calc_wr(h, l, c)
        avg_vol = sum(v[-20:]) / 20 if len(v) >= 20 else 1
        vol_ratio = v[-1] / avg_vol

        if adx_val < 18:
            return None

        long_score = sum([
            e9[-1] > e21[-1],
            e21[-1] > e50[-1],
            hist[-1] > 0,
            hist[-1] > hist[-2] if len(hist) >= 2 else False,
            wr[-1] < -55,
            vol_ratio > 1.0,
            pdi > mdi,
        ])
        short_score = sum([
            e9[-1] < e21[-1],
            e21[-1] < e50[-1],
            hist[-1] < 0,
            hist[-1] < hist[-2] if len(hist) >= 2 else False,
            wr[-1] > -45,
            vol_ratio > 1.0,
            mdi > pdi,
        ])

        if long_score < 3 and short_score < 3:
            return None

        direction = "LONG" if long_score >= short_score else "SHORT"
        score = max(long_score, short_score)

        fvg_type, fvg_low, fvg_high = detect_fvg(o, c, h, l)
        liq_side, liq_level = detect_liq_sweep(h, l, c)
        bos = detect_bos(c, h, l)

        narrative = build_narrative(
            direction, symbol, price, score, adx_val, hist, wr,
            fvg_type, fvg_low, fvg_high, liq_side, liq_level, bos, vol_ratio
        )

        return {
            "pair": symbol.replace("USDT", ""),
            "direction": direction,
            "score": score,
            "price": price,
            "adx": adx_val,
            "narrative": narrative,
        }
    except:
        return None

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔄 Scanning opportunities...")

    now = datetime.now().strftime("%d %b %Y · %H:%M UTC")

    # Ambil semua USDT futures pairs dengan volume cukup
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        tickers = await fetch(session, f"{BASE_REST}/fapi/v1/ticker/24hr")
        if tickers:
            symbols = [
                t["symbol"] for t in tickers
                if t["symbol"].endswith("USDT")
                and float(t["quoteVolume"]) >= 20_000_000
            ]
        else:
            symbols = ["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT","XRPUSDT",
                      "ADAUSDT","DOGEUSDT","AVAXUSDT","APTUSDT","ARBUSDT"]

        # Shuffle supaya tidak selalu coin yang sama
        import random
        random.shuffle(symbols)
        symbols = symbols[:40]  # scan 40 pair random

        tasks = [analyze_pair(session, sym) for sym in symbols]
        analyzed = await asyncio.gather(*tasks)

    results = [r for r in analyzed if r is not None]
    results.sort(key=lambda x: x["score"], reverse=True)
    top = results[:5]

    if not top:
        text = (
            f"🔥 <b>OPPORTUNITIES</b>\n"
            f"──────────────────────\n\n"
            f"⚠️ No strong setup detected.\n\n"
            f"Market may be consolidating.\n"
            f"Check back in 1-2 hours.\n\n"
            f"<i>📅 {now}</i>"
        )
    else:
        rank_icons = ["🥇","🥈","🥉","4️⃣","5️⃣"]
        lines = []
        for i, r in enumerate(top):
            emoji = "🟢" if r["direction"] == "LONG" else "🔴"
            fmt_price = lambda x: f"{x:,.4f}" if x < 10 else (f"{x:,.2f}" if x < 1000 else f"{x:,.0f}")
            lines.append(
                f"{rank_icons[i]} <b>#{r['pair']}USDT</b>  {emoji} <b>{r['direction']}</b>  "
                f"│  <b>Score</b>: {r['score']}/7\n"
                f"   <b>Price</b>: {fmt_price(r['price'])}  │  <b>ADX</b>: {r['adx']:.0f}\n"
                f"   {r['narrative']}"
            )

        text = (
            f"🔥 <b>OPPORTUNITIES</b>\n"
            f"<i>Top setups — 1H timeframe</i>\n"
            f"──────────────────────\n\n"
            + "\n\n".join(lines) +
            f"\n\n──────────────────────\n"
            f"⚠️ Always DYOR before entering.\n"
            f"<i>📅 {now}</i>"
        )

    await query.edit_message_text(text, reply_markup=_back_kb(), parse_mode="HTML")

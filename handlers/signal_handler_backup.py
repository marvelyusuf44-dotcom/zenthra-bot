import asyncio
import random
import aiohttp
import time
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from handlers.auth import is_allowed
from config import MIN_VOLUME_USD, BASE_REST, SIGNALS_FILE, POSITIONS_FILE
import json
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s', datefmt='%H:%M:%S')
log = logging.getLogger(__name__)

user_last_signal = {}

def load_signals():
    if os.path.exists(SIGNALS_FILE):
        with open(SIGNALS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_signals(signals):
    with open(SIGNALS_FILE, 'w') as f:
        json.dump(signals, f, indent=2)

def add_signal(user_id, pair, direction, entry, sl, tp1, tp2, tp3, lev):
    signals = load_signals()
    signals.append({
        "user_id": user_id,
        "pair": pair,
        "direction": direction,
        "entry": entry,
        "sl": sl,
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "leverage": lev,
        "status": "pending",
        "timestamp": datetime.now().isoformat()
    })
    save_signals(signals)

def load_positions():
    if os.path.exists(POSITIONS_FILE):
        with open(POSITIONS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_positions(positions):
    with open(POSITIONS_FILE, 'w') as f:
        json.dump(positions, f, indent=2)

async def fetch(session, url, params=None, retries=3):
    for attempt in range(retries):
        try:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 200:
                    return await r.json()
        except:
            pass
        await asyncio.sleep(2 ** attempt)
    return None

async def get_all_symbols(session):
    try:
        tickers = await fetch(session, f"{BASE_REST}/fapi/v1/ticker/24hr")
        if not tickers:
            return []
        symbols = [t['symbol'] for t in tickers if t['symbol'].endswith('USDT') and float(t['quoteVolume']) >= MIN_VOLUME_USD]
        random.shuffle(symbols)
        return symbols[:120]
    except:
        return ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT']

async def get_klines(session, symbol, interval='15m', limit=150):
    try:
        data = await fetch(session, f"{BASE_REST}/fapi/v1/klines", params={'symbol': symbol, 'interval': interval, 'limit': limit})
        if not data:
            return None
        c = [float(x[4]) for x in data]
        h = [float(x[2]) for x in data]
        l = [float(x[3]) for x in data]
        v = [float(x[5]) for x in data]
        return (c, h, l, v) if len(c) >= 60 else None
    except:
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
    hist = [a - b for a, b in zip(ml, sl)]
    return hist

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

def calculate_atr(highs, lows, closes, period=14):
    if len(closes) < period + 1:
        return 0.01
    tr = []
    for i in range(1, len(closes)):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i-1])
        lc = abs(lows[i] - closes[i-1])
        tr.append(max(hl, hc, lc))
    return sum(tr[-period:]) / period

async def generate_signal(session, symbol):
    try:
        data = await get_klines(session, symbol, '15m', 150)
        if not data:
            return None
        c, h, l, v = data
        if len(c) < 60:
            return None

        price = c[-1]
        atr = calculate_atr(h, l, c, 14)
        if atr == 0:
            atr = price * 0.01

        e9_list = ema_list(c, 9)
        e21_list = ema_list(c, 21)
        e50_list = ema_list(c, 50)
        e9 = e9_list[-1]
        e21 = e21_list[-1]
        e50 = e50_list[-1]

        slope_e21 = e21_list[-1] - e21_list[-5] if len(e21_list) >= 5 else 0

        hist = calc_macd(c)
        wr = calc_wr(h, l, c)
        adx_val, pdi, mdi = calc_adx(h, l, c)

        avg_vol = sum(v[-20:]) / 20 if len(v) >= 20 else 1

        if adx_val < 22:
            return None

        long_conditions = [
            e9 > e21,
            e21 > e50,
            hist[-1] > 0,
            hist[-2] < 0 < hist[-1] if len(hist) >= 2 else False,
            wr[-1] < -55,
            v[-1] > avg_vol * 1.1,
            pdi > mdi,
            slope_e21 > 0,
        ]
        short_conditions = [
            e9 < e21,
            e21 < e50,
            hist[-1] < 0,
            hist[-2] > 0 > hist[-1] if len(hist) >= 2 else False,
            wr[-1] > -45,
            v[-1] > avg_vol * 1.1,
            mdi > pdi,
            slope_e21 < 0,
        ]

        long_score = sum(long_conditions)
        short_score = sum(short_conditions)

        if long_score < 5 and short_score < 5:
            return None

        direction = 'LONG' if long_score >= 5 else 'SHORT'

        data1h = await get_klines(session, symbol, '1h', 60)
        if data1h:
            c1h, h1h, l1h, v1h = data1h
            e9_1h = ema_list(c1h, 9)[-1]
            e21_1h = ema_list(c1h, 21)[-1]
            hist1h = calc_macd(c1h)
            adx1h, pdi1h, mdi1h = calc_adx(h1h, l1h, c1h)
            if direction == 'LONG':
                if not (e9_1h > e21_1h and hist1h[-1] > 0 and pdi1h > mdi1h):
                    return None
            else:
                if not (e9_1h < e21_1h and hist1h[-1] < 0 and mdi1h > pdi1h):
                    return None

        if price >= 1000: dc = 1
        elif price >= 100: dc = 2
        elif price >= 10: dc = 3
        elif price >= 1: dc = 4
        elif price >= 0.1: dc = 5
        else: dc = 6
        fmt = lambda x: f'{x:,.{dc}f}'

        sp = price * 0.00015
        if direction == 'LONG':
            entry_low = price - sp
            entry_high = price + sp
            sl = price - atr * 2.2
            tp1 = price + atr * 2.0
            tp2 = price + atr * 3.5
            tp3 = price + atr * 5.5
        else:
            entry_low = price - sp
            entry_high = price + sp
            sl = price + atr * 2.2
            tp1 = price - atr * 2.0
            tp2 = price - atr * 3.5
            tp3 = price - atr * 5.5

        pair_clean = symbol.replace('USDT', '')
        emoji = '🟢' if direction == 'LONG' else '🔴'

        total_score = max(long_score, short_score)
        if total_score >= 8:
            lev = random.choice([50, 75, 100])
        elif total_score >= 6:
            lev = random.choice([30, 40, 50])
        else:
            lev = random.choice([15, 20, 25])

        msg = (f"📌 <b>Pair</b>      : #{pair_clean}USDT\n"
               f"📊 <b>Direction</b> : {emoji} {direction}\n"
               f"⚡ <b>Leverage</b>  : {lev}x\n\n"
               f"🎯 <b>Entry Zone</b>: {fmt(entry_low)} - {fmt(entry_high)}\n"
               f"🛑 <b>Stop Loss</b> : {fmt(sl)}\n\n"
               f"💰 <b>Take Profit</b>:\n"
               f"   <b>TP1</b> : {fmt(tp1)}\n"
               f"   <b>TP2</b> : {fmt(tp2)}\n"
               f"   <b>TP3</b> : {fmt(tp3)}\n\n"
               f"⚠️ Risk 1-3% per trade")

        return msg, direction, pair_clean, entry_low, entry_high, sl, tp1, tp2, tp3, lev, dc
    except Exception as e:
        log.debug(f"signal {symbol}: {e}")
        return None

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    
    if not is_allowed(user_id):
        await query.edit_message_text("❌ Access denied. Contact admin.")
        return
    
    await query.edit_message_text("🔄 Generating signal...")
    
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        symbols = await get_all_symbols(session)
        if symbols:
            random.shuffle(symbols)
            for sym in symbols[:60]:
                result = await generate_signal(session, sym)
                if result:
                    msg, direction, pair_clean, entry_low, entry_high, sl, tp1, tp2, tp3, lev, dc = result
                    entry = (entry_low + entry_high) / 2
                    user_last_signal[user_id] = {
                        "pair": f"{pair_clean}USDT",
                        "direction": direction,
                        "entry": entry,
                        "sl": sl,
                        "tp1": tp1,
                        "tp2": tp2,
                        "tp3": tp3,
                        "leverage": lev,
                        "dc": dc
                    }
                    # Simpan sinyal ke database
                    add_signal(user_id, pair_clean, direction, entry, sl, tp1, tp2, tp3, lev)
                    keyboard = [
                        [InlineKeyboardButton("✅ ENTER POSITION", callback_data=f"enter_{user_id}_{pair_clean}")],
                        [InlineKeyboardButton("◀️ BACK TO MENU", callback_data="main_menu")]
                    ]
                    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
                    return
        await query.edit_message_text("❌ No signal at this moment.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ BACK", callback_data="main_menu")]]))

async def handle_enter(update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
    query = update.callback_query
    user_id = update.effective_user.id
    
    parts = data.split("_")
    if len(parts) >= 3:
        uid = int(parts[1])
        pair_clean = parts[2]
    else:
        uid = int(parts[1])
        pair_clean = None
    
    if uid != user_id:
        await query.edit_message_text("❌ Invalid action.")
        return
    
    sig = user_last_signal.get(user_id)
    if not sig:
        await query.edit_message_text("❌ No signal to enter. Please request SIGNAL first.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ BACK", callback_data="main_menu")]]))
        return
    
    # Simpan posisi ke database
    positions = load_positions()
    pos_key = f"{user_id}_{sig['pair']}"
    positions[pos_key] = {
        "user_id": user_id,
        "pair": sig['pair'],
        "direction": sig['direction'],
        "entry": sig['entry'],
        "sl": sig['sl'],
        "tp1": sig['tp1'],
        "tp2": sig['tp2'],
        "tp3": sig['tp3'],
        "leverage": sig['leverage'],
        "dc": sig['dc'],
        "tp1_hit": False,
        "tp2_hit": False,
        "created_at": datetime.now().isoformat()
    }
    save_positions(positions)
    
    await query.edit_message_text(
        f"✅ <b>POSITION RECORDED</b>\n\n"
        f"📌 <b>Pair</b>      : #{sig['pair'].replace('USDT', '')}USDT\n"
        f"📊 <b>Direction</b> : {'🟢 LONG' if sig['direction'] == 'LONG' else '🔴 SHORT'}\n"
        f"🎯 <b>Entry</b>     : {sig['entry']:.4f}\n"
        f"🛑 <b>Stop Loss</b> : {sig['sl']:.4f}\n"
        f"💰 <b>TP1</b>       : {sig['tp1']:.4f}\n"
        f"💰 <b>TP2</b>       : {sig['tp2']:.4f}\n"
        f"💰 <b>TP3</b>       : {sig['tp3']:.4f}\n"
        f"⚡ <b>Leverage</b>  : {sig['leverage']}x\n\n"
        f"✅ Position saved. Bot will monitor price.\n"
        f"🔔 You will be notified when TP/SL is hit.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ BACK TO MENU", callback_data="main_menu")]])
    )

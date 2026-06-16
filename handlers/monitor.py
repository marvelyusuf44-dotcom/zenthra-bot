import asyncio
import aiohttp
import json
import os
from config import BASE_REST, POSITIONS_FILE, SIGNALS_FILE
from handlers.auth import load_users

async def fetch(session, url, params=None):
    try:
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=8)) as r:
            if r.status == 200:
                return await r.json()
    except:
        pass
    return None

def load_positions():
    if os.path.exists(POSITIONS_FILE):
        with open(POSITIONS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_positions(positions):
    with open(POSITIONS_FILE, 'w') as f:
        json.dump(positions, f, indent=2)

def load_signals():
    if os.path.exists(SIGNALS_FILE):
        with open(SIGNALS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_signals(signals):
    with open(SIGNALS_FILE, 'w') as f:
        json.dump(signals, f, indent=2)

def update_signal_status(pair, tp_hit=None, sl_hit=False, be_hit=False):
    signals = load_signals()
    for s in signals:
        if s.get("pair") == pair and s.get("status") in ["pending", "tp1_hit", "tp2_hit"]:
            if tp_hit:
                s["status"] = f"tp{tp_hit}_hit"
            elif sl_hit:
                s["status"] = "sl_hit"
            elif be_hit:
                s["status"] = "be_hit"
            break
    save_signals(signals)

def tp1_msg(pair_clean, emoji, direction, tp1, profit_lev, lev, fmt):
    return (
        f"🎯 <b>TP1 HIT!</b>\n\n"
        f"📌 <b>Pair</b>      : #{pair_clean}USDT\n"
        f"📊 <b>Direction</b> : {emoji} {direction}\n"
        f"✅ <b>TP1</b>       : {fmt(tp1)}\n"
        f"📈 <b>Profit</b>    : +{profit_lev:.2f}%\n"
        f"⚡ <b>Leverage</b>  : {lev}x\n\n"
        f"⚡ Move SL to breakeven."
    )

def tp2_msg(pair_clean, emoji, direction, tp2, profit_lev, lev, fmt):
    return (
        f"🎯 <b>TP2 HIT!</b>\n\n"
        f"📌 <b>Pair</b>      : #{pair_clean}USDT\n"
        f"📊 <b>Direction</b> : {emoji} {direction}\n"
        f"✅ <b>TP2</b>       : {fmt(tp2)}\n"
        f"📈 <b>Profit</b>    : +{profit_lev:.2f}%\n"
        f"⚡ <b>Leverage</b>  : {lev}x\n\n"
        f"🔥 Ride the wave!"
    )

def tp3_msg(pair_clean, emoji, direction, tp3, profit_lev, lev, fmt):
    return (
        f"🎯 <b>TP3 HIT!</b>\n\n"
        f"📌 <b>Pair</b>      : #{pair_clean}USDT\n"
        f"📊 <b>Direction</b> : {emoji} {direction}\n"
        f"✅ <b>TP3</b>       : {fmt(tp3)}\n"
        f"📈 <b>Profit</b>    : +{profit_lev:.2f}%\n"
        f"⚡ <b>Leverage</b>  : {lev}x\n\n"
        f"🎉 Full target reached!"
    )

def be_msg(pair_clean, emoji, direction, sl, lev, fmt):
    return (
        f"🟡 <b>BREAKEVEN HIT!</b>\n\n"
        f"📌 <b>Pair</b>      : #{pair_clean}USDT\n"
        f"📊 <b>Direction</b> : {emoji} {direction}\n"
        f"🎯 <b>Exit</b>      : {fmt(sl)}\n"
        f"📊 <b>Result</b>    : 0.00%\n"
        f"⚡ <b>Leverage</b>  : {lev}x\n\n"
        f"✅ Capital secured."
    )

def sl_msg(pair_clean, emoji, direction, sl, loss_lev, lev, fmt):
    return (
        f"🛑 <b>STOP LOSS HIT!</b>\n\n"
        f"📌 <b>Pair</b>      : #{pair_clean}USDT\n"
        f"📊 <b>Direction</b> : {emoji} {direction}\n"
        f"❌ <b>SL</b>        : {fmt(sl)}\n"
        f"📉 <b>Loss</b>      : -{loss_lev:.2f}%\n"
        f"⚡ <b>Leverage</b>  : {lev}x\n\n"
        f"💪 Stay disciplined."
    )

async def monitor_positions(app):
    while True:
        try:
            positions = load_positions()
            to_remove = []

            for key, pos in positions.items():
                user_id = pos.get("user_id")
                pair = pos.get("pair")
                direction = pos.get("direction")
                entry = pos.get("entry")
                sl = pos.get("sl")
                tp1 = pos.get("tp1")
                tp2 = pos.get("tp2")
                tp3 = pos.get("tp3")
                lev = pos.get("leverage", 10)
                dc = pos.get("dc", 4)
                # Reload dari file supaya status selalu fresh
                positions = load_positions()
                pos = positions.get(key, pos)
                tp1_hit = pos.get("tp1_hit", False)
                tp2_hit = pos.get("tp2_hit", False)

                async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
                    ticker = await fetch(session, f"{BASE_REST}/fapi/v1/ticker/price", params={'symbol': pair})
                    if not ticker:
                        continue
                    current_price = float(ticker['price'])
                    fmt = lambda x: f'{x:,.{dc}f}'
                    pair_clean = pair.replace('USDT', '')
                    emoji = '🟢' if direction == 'LONG' else '🔴'

                    if direction == 'LONG':
                        if not tp1_hit and not pos.get("tp1_hit", False) and current_price >= tp1:
                            pos["tp1_hit"] = True
                            pos["sl"] = entry  # Move SL to breakeven
                            save_positions(positions)
                            profit_lev = (tp1 - entry) / entry * 100 * lev
                            update_signal_status(pair_clean, tp_hit=1)
                            await app.bot.send_message(user_id, tp1_msg(pair_clean, emoji, direction, tp1, profit_lev, lev, fmt), parse_mode="HTML")
                        elif not tp2_hit and not pos.get("tp2_hit", False) and current_price >= tp2:
                            pos["tp2_hit"] = True
                            save_positions(positions)
                            profit_lev = (tp2 - entry) / entry * 100 * lev
                            update_signal_status(pair_clean, tp_hit=2)
                            await app.bot.send_message(user_id, tp2_msg(pair_clean, emoji, direction, tp2, profit_lev, lev, fmt), parse_mode="HTML")
                        elif current_price >= tp3:
                            profit_lev = (tp3 - entry) / entry * 100 * lev
                            update_signal_status(pair_clean, tp_hit=3)
                            await app.bot.send_message(user_id, tp3_msg(pair_clean, emoji, direction, tp3, profit_lev, lev, fmt), parse_mode="HTML")
                            to_remove.append(key)
                        elif current_price <= sl and key not in to_remove:
                            loss_lev = (entry - sl) / entry * 100 * lev
                            is_be = abs(sl - entry) / entry < 0.0005
                            if is_be:
                                update_signal_status(pair_clean, be_hit=True)
                                await app.bot.send_message(user_id, be_msg(pair_clean, emoji, direction, sl, lev, fmt), parse_mode="HTML")
                            else:
                                update_signal_status(pair_clean, sl_hit=True)
                                await app.bot.send_message(user_id, sl_msg(pair_clean, emoji, direction, sl, loss_lev, lev, fmt), parse_mode="HTML")
                            to_remove.append(key)
                    else:
                        if not tp1_hit and not pos.get("tp1_hit", False) and current_price <= tp1:
                            pos["tp1_hit"] = True
                            pos["sl"] = entry  # Move SL to breakeven
                            save_positions(positions)
                            profit_lev = (entry - tp1) / entry * 100 * lev
                            update_signal_status(pair_clean, tp_hit=1)
                            await app.bot.send_message(user_id, tp1_msg(pair_clean, emoji, direction, tp1, profit_lev, lev, fmt), parse_mode="HTML")
                        elif not tp2_hit and not pos.get("tp2_hit", False) and current_price <= tp2:
                            pos["tp2_hit"] = True
                            save_positions(positions)
                            profit_lev = (entry - tp2) / entry * 100 * lev
                            update_signal_status(pair_clean, tp_hit=2)
                            await app.bot.send_message(user_id, tp2_msg(pair_clean, emoji, direction, tp2, profit_lev, lev, fmt), parse_mode="HTML")
                        elif current_price <= tp3:
                            profit_lev = (entry - tp3) / entry * 100 * lev
                            update_signal_status(pair_clean, tp_hit=3)
                            await app.bot.send_message(user_id, tp3_msg(pair_clean, emoji, direction, tp3, profit_lev, lev, fmt), parse_mode="HTML")
                            to_remove.append(key)
                        elif current_price >= sl and key not in to_remove:
                            loss_lev = (sl - entry) / entry * 100 * lev
                            is_be = abs(sl - entry) / entry < 0.0005
                            if is_be:
                                update_signal_status(pair_clean, be_hit=True)
                                await app.bot.send_message(user_id, be_msg(pair_clean, emoji, direction, sl, lev, fmt), parse_mode="HTML")
                            else:
                                update_signal_status(pair_clean, sl_hit=True)
                                await app.bot.send_message(user_id, sl_msg(pair_clean, emoji, direction, sl, loss_lev, lev, fmt), parse_mode="HTML")
                            to_remove.append(key)

            for key in to_remove:
                positions.pop(key, None)
            if to_remove:
                save_positions(positions)

            await asyncio.sleep(30)
        except Exception as e:
            print(f"Monitor error: {e}")
            await asyncio.sleep(30)

# ─── NEW LISTING TRACKER ───────────────────────────────────────────────────────

known_symbols = set()
LISTINGS_FILE = "database/new_listings.json"

def load_listings():
    import json, os
    if os.path.exists(LISTINGS_FILE):
        with open(LISTINGS_FILE) as f:
            return json.load(f)
    return []

def save_listings(listings):
    import json
    with open(LISTINGS_FILE, "w") as f:
        json.dump(listings, f, indent=2)

async def track_new_listings(app):
    global known_symbols
    
    # Inisialisasi daftar awal
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        try:
            async with session.get(f"{BASE_REST}/fapi/v1/ticker/24hr", timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 200:
                    tickers = await r.json()
                    known_symbols = {t["symbol"] for t in tickers if t["symbol"].endswith("USDT")}
        except:
            pass

    while True:
        try:
            await asyncio.sleep(300)  # cek setiap 5 menit

            async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
                async with session.get(f"{BASE_REST}/fapi/v1/ticker/24hr", timeout=aiohttp.ClientTimeout(total=10)) as r:
                    if r.status != 200:
                        continue
                    tickers = await r.json()

                current_symbols = {t["symbol"] for t in tickers if t["symbol"].endswith("USDT")}
                new_symbols = current_symbols - known_symbols

                if new_symbols:
                    ticker_map = {t["symbol"]: t for t in tickers}

                    for symbol in new_symbols:
                        t = ticker_map.get(symbol, {})
                        price  = float(t.get("lastPrice", 0))
                        change = float(t.get("priceChangePercent", 0))
                        vol    = float(t.get("quoteVolume", 0))
                        pair_clean = symbol.replace("USDT", "")

                        def fmt_vol(v):
                            if v >= 1_000_000_000: return f"${v/1_000_000_000:.1f}B"
                            if v >= 1_000_000:     return f"${v/1_000_000:.0f}M"
                            if v >= 1_000:         return f"${v/1_000:.0f}K"
                            return f"${v:.0f}"

                        def fmt_price(p):
                            if p >= 10000: return f"{p:,.0f}"
                            if p >= 100:   return f"{p:,.2f}"
                            if p >= 1:     return f"{p:,.4f}"
                            if p >= 0.01:  return f"{p:.5f}"
                            return f"{p:.8f}"

                        arrow = "▲" if change >= 0 else "▼"
                        sign  = "+" if change >= 0 else ""

                        from datetime import datetime
                        now = datetime.now().strftime("%d %b %Y · %H:%M UTC")

                        msg = (
                            f"🆕 <b>NEW LISTING DETECTED</b>\n"
                            f"──────────────────────\n\n"
                            f"📌 <b>Pair</b>    : #{pair_clean}USDT\n"
                            f"💲 <b>Price</b>   : {fmt_price(price)}\n"
                            f"📦 <b>Volume</b>  : {fmt_vol(vol)}\n"
                            f"📈 <b>Change</b>  : {arrow}{sign}{change:.2f}%\n\n"
                            f"──────────────────────\n"
                            f"⚡ Early entry window — trade with caution.\n"
                            f"<i>📅 {now}</i>"
                        )

                        # Simpan ke JSON
                        from datetime import datetime as dt
                        listings = load_listings()
                        listings.append({
                            "pair": pair_clean,
                            "price": price,
                            "change": change,
                            "volume": vol,
                            "time": dt.now().strftime("%d %b · %H:%M UTC")
                        })
                        # Simpan max 50 listing terakhir
                        if len(listings) > 50:
                            listings = listings[-50:]
                        save_listings(listings)

                        # Kirim ke semua user aktif
                        users = load_users()
                        for uid in users:
                            try:
                                await app.bot.send_message(int(uid), msg, parse_mode="HTML")
                            except:
                                pass

                known_symbols = current_symbols

        except Exception as e:
            print(f"New listing tracker error: {e}")
            await asyncio.sleep(60)

import json
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import SIGNALS_FILE, POSITIONS_FILE
from handlers.auth import is_allowed

def _back_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Back to Menu", callback_data="main_menu")]
    ])

def load_signals():
    if os.path.exists(SIGNALS_FILE):
        with open(SIGNALS_FILE, 'r') as f:
            return json.load(f)
    return []

def load_positions():
    if os.path.exists(POSITIONS_FILE):
        with open(POSITIONS_FILE, 'r') as f:
            return json.load(f)
    return {}

def get_user_stats(user_id):
    signals = load_signals()
    user_signals = [s for s in signals if s.get('user_id') == user_id]

    total = len(user_signals)
    tp_hit = sum(1 for s in user_signals if s.get('status') in ['tp1_hit', 'tp2_hit', 'tp3_hit'])
    sl_hit = sum(1 for s in user_signals if s.get('status') == 'sl_hit')
    be_hit = sum(1 for s in user_signals if s.get('status') == 'be_hit')
    win_rate = (tp_hit / total * 100) if total > 0 else 0

    pair_stats = {}
    for s in user_signals:
        p = s.get('pair', '')
        if p:
            if p not in pair_stats:
                pair_stats[p] = {'total': 0, 'win': 0}
            pair_stats[p]['total'] += 1
            if s.get('status') in ['tp1_hit', 'tp2_hit', 'tp3_hit']:
                pair_stats[p]['win'] += 1

    best_pair = "-"
    best_win_rate = -1
    for p, stats in pair_stats.items():
        if stats['total'] > 0:
            wr = (stats['win'] / stats['total']) * 100
            if wr > best_win_rate:
                best_win_rate = wr
                best_pair = p

    pair_count = {}
    for s in user_signals:
        p = s.get('pair', '')
        if p:
            pair_count[p] = pair_count.get(p, 0) + 1
    most_signal = max(pair_count.items(), key=lambda x: x[1])[0] if pair_count else "-"

    positions = load_positions()
    active_signals = sum(1 for k, pos in positions.items() if pos.get('user_id') == user_id)

    return total, tp_hit, sl_hit, win_rate, best_pair, most_signal, active_signals

def win_rate_bar(wr):
    filled = round(wr / 10)
    empty = 10 - filled
    return "█" * filled + "░" * empty

def win_rate_label(wr):
    if wr >= 70: return "🔥 Excellent"
    if wr >= 55: return "✅ Good"
    if wr >= 40: return "🟡 Average"
    return "🔴 Needs improvement"

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id

    if not is_allowed(user_id):
        await query.edit_message_text("❌ Access denied.")
        return

    total, tp_hit, sl_hit, win_rate, best_pair, most_signal, active_signals = get_user_stats(user_id)
    today = datetime.now().strftime("%d %b %Y")

    best_pair_display = f"#{best_pair}" if best_pair != "-" else "-"
    most_signal_display = f"#{most_signal}" if most_signal != "-" else "-"

    bar = win_rate_bar(win_rate)
    label = win_rate_label(win_rate)

    pending = total - tp_hit - sl_hit

    msg = (
        f"📊 <b>ZENTHRA STATISTICS</b>\n"
        f"──────────────────────\n"
        f"📅 <i>{today}</i>\n\n"

        f"📋 <b>Signal Summary</b>\n"
        f"┌ Total Signals  : <b>{total}</b>\n"
        f"├ 🎯 TP Hit      : <b>{tp_hit}</b>\n"
        f"├ 🛑 SL Hit      : <b>{sl_hit}</b>\n"
        f"├ 🟡 Breakeven   : <b>{be_hit}</b>\n"
        f"└ ⏳ Pending     : <b>{pending}</b>\n\n"

        f"📈 <b>Win Rate</b>\n"
        f"<code>[{bar}] {win_rate:.1f}%</code>\n"
        f"{label}\n\n"

        f"──────────────────────\n"
        f"🏆 Best Pair     : <b>{best_pair_display}</b>\n"
        f"🔥 Most Active   : <b>{most_signal_display}</b>\n"
        f"📡 Active Now    : <b>{active_signals}</b>\n"
        f"──────────────────────\n"
        f"<i>Stats update every new signal.</i>"
    )

    await query.edit_message_text(msg, reply_markup=_back_kb(), parse_mode="HTML")

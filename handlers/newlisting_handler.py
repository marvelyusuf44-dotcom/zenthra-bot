from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime
import json, os

LISTINGS_FILE = "database/new_listings.json"

def _back_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Back to Menu", callback_data="main_menu")]
    ])

def load_listings():
    if os.path.exists(LISTINGS_FILE):
        with open(LISTINGS_FILE) as f:
            return json.load(f)
    return []

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔄 Loading new listings...")

    listings = load_listings()
    now = datetime.now().strftime("%d %b %Y · %H:%M UTC")

    if not listings:
        text = (
            f"🆕 <b>NEW LISTINGS</b>\n"
            f"──────────────────────\n\n"
            f"No new listings detected yet.\n\n"
            f"Bot is actively monitoring Binance Futures\n"
            f"every 5 minutes for new pairs.\n\n"
            f"<i>📅 {now}</i>"
        )
    else:
        lines = []
        for r in reversed(listings[-10:]):
            arrow = "▲" if r["change"] >= 0 else "▼"
            sign  = "+" if r["change"] >= 0 else ""

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

            lines.append(
                f"🆕 <b>#{r['pair']}USDT</b>\n"
                f"   <b>Price</b>  : {fmt_price(r['price'])}\n"
                f"   <b>Change</b> : {arrow}{sign}{r['change']:.2f}%\n"
                f"   <b>Volume</b> : {fmt_vol(r['volume'])}\n"
                f"   <b>Time</b>   : {r['time']}"
            )

        text = (
            f"🆕 <b>NEW LISTINGS</b>\n"
            f"<i>Recently listed on Binance Futures</i>\n"
            f"──────────────────────\n\n"
            + "\n\n".join(lines) +
            f"\n\n──────────────────────\n"
            f"⚡ Bot monitors every 5 minutes.\n"
            f"<i>📅 {now}</i>"
        )

    await query.edit_message_text(text, reply_markup=_back_kb(), parse_mode="HTML")

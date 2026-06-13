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

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔄 Fetching market sentiment...")

    now = datetime.now().strftime("%d %b %Y · %H:%M UTC")
    fng = await fetch_fear_greed()

    if fng:
        if fng <= 20:
            fng_text = "😱 EXTREME FEAR"
            bar_len = 20
            filled = int(fng / 100 * bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)
        elif fng <= 40:
            fng_text = "😨 FEAR"
            bar_len = 20
            filled = int(fng / 100 * bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)
        elif fng <= 60:
            fng_text = "😐 NEUTRAL"
            bar_len = 20
            filled = int(fng / 100 * bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)
        elif fng <= 80:
            fng_text = "😊 GREED"
            bar_len = 20
            filled = int(fng / 100 * bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)
        else:
            fng_text = "🤑 EXTREME GREED"
            bar_len = 20
            filled = int(fng / 100 * bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)

        text = (
            f"🧠 <b>MARKET SENTIMENT</b>\n"
            f"──────────────────────\n\n"
            f"{fng_text} [{fng}/100]\n\n"
            f"<pre>{bar}</pre>\n\n"
            f"──────────────────────\n"
            f"📅 {now}"
        )
    else:
        text = (
            f"🧠 <b>MARKET SENTIMENT</b>\n"
            f"──────────────────────\n\n"
            f"⚠️ Unable to fetch sentiment data.\n\n"
            f"──────────────────────\n"
            f"📅 {now}"
        )

    await query.edit_message_text(text, reply_markup=_back_kb(), parse_mode="HTML")

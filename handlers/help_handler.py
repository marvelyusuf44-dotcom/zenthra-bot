from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_USERNAME, COMMUNITY_CHANNEL

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    msg = (
        "❓ <b>HELP MENU</b>\n"
        "──────────────────────\n\n"
        "📋 <b>Available Commands</b>\n\n"
        "<b>/start</b>          — Show main menu\n"
        "<b>/signal</b>         — Get trading signal\n"
        "<b>/opportunities</b>  — Top market setups\n"
        "<b>/trending</b>       — Trending pairs\n"
        "<b>/gainers</b>        — Top gainers 24H\n"
        "<b>/losers</b>         — Top losers 24H\n"
        "<b>/market</b>         — Market overview\n"
        "<b>/sentiment</b>      — Market sentiment\n"
        "<b>/stats</b>          — Signal statistics\n"
        "<b>/news</b>           — Latest crypto news\n"
        "<b>/account</b>        — Your account info\n"
        "<b>/calc</b>           — Trade calculator\n"
        "<b>/newlisting</b>     — New listings detected\n"
        "<b>/calendar</b>       — Economic calendar\n"
        "<b>/oi</b>             — Open interest scanner\n\n"
        "──────────────────────\n\n"
        "💡 Quick start:\n"
        "1. Click SIGNAL to get trading signal\n"
        "2. Click ENTER POSITION to record and monitor\n"
        "3. Bot will notify when TP/SL is hit\n\n"
        f"📢 Join our community: {COMMUNITY_CHANNEL}\n\n"
        f"Need more help? Contact admin: @{ADMIN_USERNAME}\n\n"
        "⚠️ We have no control over ads shown by Telegram in this bot.\n"
        "Do not be scammed by fake airdrops or login pages."
    )
    
    keyboard = [
        [InlineKeyboardButton("📩 CONTACT ADMIN", url=f"https://t.me/{ADMIN_USERNAME}")],
        [InlineKeyboardButton("📢 JOIN COMMUNITY", url=COMMUNITY_CHANNEL)],
        [InlineKeyboardButton("◀️ BACK TO MENU", callback_data="main_menu")]
    ]
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

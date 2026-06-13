from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

def _back_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Back to Menu", callback_data="main_menu")]
    ])

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = (
        "🧮 <b>TRADE CALCULATOR</b>\n"
        "──────────────────────\n\n"
        "Plan your trade before you enter.\n"
        "Know your profit, loss & liquidation\n"
        "price <b>before</b> risking real money.\n\n"
        "──────────────────────\n"
        "📌 <b>Command:</b>\n"
        "<code>/calc entry exit size leverage</code>\n\n"
        "📌 <b>Example:</b>\n"
        "<code>/calc 60000 62000 100 10</code>\n\n"
        "──────────────────────\n"
        "📖 <b>Parameters:</b>\n"
        "┌ <code>entry</code>    — Entry price\n"
        "├ <code>exit</code>     — Target / TP price\n"
        "├ <code>size</code>     — Capital in USD\n"
        "└ <code>leverage</code> — Leverage multiplier\n\n"
        "──────────────────────\n"
        "<i>⚠️ Always plan your risk.\n"
        "Never risk more than you can afford to lose.</i>"
    )

    await query.edit_message_text(text, reply_markup=_back_kb(), parse_mode="HTML")

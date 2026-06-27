#!/usr/bin/env python3
import asyncio
import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from config import BOT_TOKEN
from handlers.auth import is_allowed
from handlers.admin import adduser_command, removeuser_command, listusers_command
from handlers.menu import show_main_menu, back_to_menu
from handlers.signal_handler import handle as signal_handle, handle_enter
from handlers.opportunities_handler import handle as opportunities_handle
from handlers.market_handler import (
    handle_trending,
    handle_gainers,
    handle_losers,
    handle,
)
from handlers.sentiment_handler import handle as sentiment_handle
from handlers.stats_handler import handle as stats_handle
from handlers.news_handler import handle as news_handle
from handlers.calculator_handler import handle as calculator_handle
from handlers.account_handler import handle as account_handle
from handlers.help_handler import handle as help_handle
from handlers.monitor import monitor_positions, track_new_listings
from handlers.newlisting_handler import handle as newlisting_handle
from handlers.calendar_handler import handle as calendar_handle
from handlers.oi_handler import handle as oi_handle

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await show_main_menu(update, context, edit=False)

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "main_menu":
        await show_main_menu(update, context, edit=True)
    elif data == "signal":
        await signal_handle(update, context)
    elif data.startswith("enter_"):
        await handle_enter(update, context, data)
    elif data == "opportunities":
        await opportunities_handle(update, context)
    elif data == "trending":
        await handle_trending(update, context)
    elif data == "gainers":
        await handle_gainers(update, context)
    elif data == "losers":
        await handle_losers(update, context)
    elif data == "market":
        await handle(update, context)
    elif data == "sentiment":
        await sentiment_handle(update, context)
    elif data == "stats":
        await stats_handle(update, context)
    elif data == "news":
        await news_handle(update, context)
    elif data == "calculator":
        await calculator_handle(update, context)
    elif data == "account":
        await account_handle(update, context)
    elif data == "help":
        await help_handle(update, context)
    elif data == "newlisting":
        await newlisting_handle(update, context)
    elif data == "calendar":
        await calendar_handle(update, context)
    elif data == "openinterest":
        await oi_handle(update, context)
    else:
        await query.edit_message_text("⚠️ Menu not recognized.", reply_markup=None)

async def calc_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 4:
        await update.message.reply_text(
            "<b>TRADE CALCULATOR</b>\n\n"
            "Usage:\n"
            "<code>/calc entry exit size leverage</code>\n\n"
            "Example:\n"
            "<code>/calc 60000 62000 100 10</code>\n\n"
            "<i>entry   = entry price\n"
            "exit    = target / TP price\n"
            "size    = capital in USD\n"
            "leverage = multiplier</i>",
            parse_mode="HTML"
        )
        return
    try:
        entry  = float(args[0])
        exit_p = float(args[1])
        size   = float(args[2])
        lev    = float(args[3])
        direction = "LONG" if exit_p > entry else "SHORT"
        dir_icon  = "📈" if exit_p > entry else "📉"
        roi     = (exit_p - entry) / entry * 100
        roi_lev = roi * lev
        pnl     = size * (roi / 100)
        pnl_lev = size * (roi_lev / 100)
        liq     = entry * (1 - 1/lev) if exit_p > entry else entry * (1 + 1/lev)
        pnl_icon = "🟢" if pnl_lev >= 0 else "🔴"
        msg = (
            f"<b>TRADE CALCULATOR</b>\n"
            f"<code>{'─'*22}</code>\n\n"
            f"{dir_icon} <b>{direction}</b>  x{lev:.0f} Leverage\n\n"
            f"📌 Entry      : <code>${entry:,.2f}</code>\n"
            f"🎯 Exit / TP  : <code>${exit_p:,.2f}</code>\n"
            f"💰 Capital    : <code>${size:,.2f}</code>\n"
            f"<code>{'─'*22}</code>\n"
            f"📊 ROI        : <b>{roi:+.2f}%</b>\n"
            f"📊 ROI {lev:.0f}x    : <b>{roi_lev:+.2f}%</b>\n"
            f"{pnl_icon} P&L        : <b>${pnl:+,.2f}</b>\n"
            f"{pnl_icon} P&L {lev:.0f}x    : <b>${pnl_lev:+,.2f}</b>\n"
            f"<code>{'─'*22}</code>\n"
            f"💀 Liq. Price : <code>${liq:,.2f}</code>\n"
            f"<code>{'─'*22}</code>\n"
            f"<i>Always use stop loss. Manage your risk.</i>"
        )
        await update.message.reply_text(msg, parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def broadcast_command(update, context):
    from config import ADMIN_ID
    import json

    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("Gunakan: /broadcast [pesan kamu]")
        return

    message = " ".join(context.args)

    with open("database/users.json", "r") as f:
        users = json.load(f)

    sent = 0
    failed = 0
    for user_id in users.keys():
        try:
            await context.bot.send_message(int(user_id), message, parse_mode="HTML")
            sent += 1
        except Exception as e:
            failed += 1

    await update.message.reply_text(f"✅ Broadcast selesai.\nTerkirim: {sent}\nGagal: {failed}")


async def main():
    os.makedirs("database", exist_ok=True)
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("calc", calc_command))
    app.add_handler(CommandHandler("newlisting", lambda u,c: newlisting_handle(u,c)))
    app.add_handler(CommandHandler("calendar", lambda u,c: calendar_handle(u,c)))
    app.add_handler(CommandHandler("oi", lambda u,c: oi_handle(u,c)))
    
    # Admin commands
    app.add_handler(CommandHandler("adduser", adduser_command))
    app.add_handler(CommandHandler("removeuser", removeuser_command))
    app.add_handler(CommandHandler("listusers", listusers_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    
    # Callback handler untuk tombol
    app.add_handler(CallbackQueryHandler(menu_callback))
    
    # Start monitoring positions (create task after app starts)
    loop = asyncio.get_event_loop()
    loop.create_task(monitor_positions(app))
    loop.create_task(track_new_listings(app))
    
    logger.info("🚀 ZENTHRA Bot v1.0 STARTED!")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())

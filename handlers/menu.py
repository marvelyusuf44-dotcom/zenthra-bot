from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from handlers.auth import is_allowed
from config import ADMIN_USERNAME, COMMUNITY_CHANNEL

def build_main_menu():
    keyboard = [
        [
            InlineKeyboardButton("📡 SIGNAL", callback_data="signal"),
            InlineKeyboardButton("🔥 OPPORTUNITIES", callback_data="opportunities"),
        ],
        [
            InlineKeyboardButton("🚀 TRENDING", callback_data="trending"),
            InlineKeyboardButton("📈 GAINERS", callback_data="gainers"),
            InlineKeyboardButton("📉 LOSERS", callback_data="losers"),
        ],
        [
            InlineKeyboardButton("📊 MARKET", callback_data="market"),
            InlineKeyboardButton("🧠 SENTIMENT", callback_data="sentiment"),
            InlineKeyboardButton("📊 OI SCAN", callback_data="openinterest"),
        ],
        [
            InlineKeyboardButton("🆕 NEW LISTING", callback_data="newlisting"),
            InlineKeyboardButton("📅 CALENDAR", callback_data="calendar"),
            InlineKeyboardButton("📰 NEWS", callback_data="news"),
        ],
        [
            InlineKeyboardButton("📈 STATS", callback_data="stats"),
            InlineKeyboardButton("🧮 CALCULATOR", callback_data="calculator"),
        ],
        [
            InlineKeyboardButton("👤 ACCOUNT", callback_data="account"),
            InlineKeyboardButton("❓ HELP", callback_data="help"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    user_id = update.effective_user.id
    username = update.effective_user.username or "User"
    
    if not is_allowed(user_id):
        keyboard = [[InlineKeyboardButton("📩 CONTACT ADMIN", url=f"https://t.me/{ADMIN_USERNAME}")]]
        text = "❌ ACCESS DENIED\n\nYour ID is not registered.\nContact admin for access."
        if edit:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    menu_text = (
        f"⚙ ZENTHRA · Futures Signal Bot\n\n"
        f"👤 Username: @{username}\n"
        f"🆔 User ID: {user_id}\n\n"
        f"Click on the REFRESH button to update your current status.\n\n"
        f"Join our Telegram: {COMMUNITY_CHANNEL}\n\n"
        f"⚠️ We have no control over ads shown by Telegram in this bot.\n"
        f"Do not be scammed by fake airdrops or login pages.\n\n"
        f"Welcome to ZENTHRA — the most advanced bot for futures trading signals.\n\n"
        f"📡 Your trading session is ready. Click SIGNAL below to get started.\n\n"
        f"For more info on your account and to manage your subscription, tap ACCOUNT below."
    )
    
    if edit:
        await update.callback_query.edit_message_text(menu_text, reply_markup=build_main_menu())
    else:
        await update.message.reply_text(menu_text, reply_markup=build_main_menu())

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await show_main_menu(update, context, edit=True)

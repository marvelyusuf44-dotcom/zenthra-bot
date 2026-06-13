import json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_ID, USERS_FILE
from handlers.auth import load_users, save_users, is_admin

async def adduser_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ You are not authorized.")
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /adduser <telegram_id> <days>\nExample: /adduser 123456789 30")
        return
    
    try:
        new_id = str(args[0])
        days = int(args[1])
        expired = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%dT23:59:59")
        
        users = load_users()
        users[new_id] = {"expired": expired}
        save_users(users)
        
        await update.message.reply_text(f"✅ User {new_id} added.\n📅 Expires: {expired}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def removeuser_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ You are not authorized.")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /removeuser <telegram_id>")
        return
    
    try:
        remove_id = str(args[0])
        users = load_users()
        
        if remove_id in users:
            del users[remove_id]
            save_users(users)
            await update.message.reply_text(f"✅ User {remove_id} removed.")
        else:
            await update.message.reply_text(f"❌ User {remove_id} not found.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def listusers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ You are not authorized.")
        return
    
    users = load_users()
    if not users:
        await update.message.reply_text("📭 No users registered.")
        return
    
    msg = "📋 REGISTERED USERS\n━━━━━━━━━━━━━━━━━━━━\n"
    for uid, data in users.items():
        expired = data.get("expired", "N/A")
        msg += f"🆔 {uid}\n   ⏰ Expires: {expired}\n\n"
    
    await update.message.reply_text(msg)

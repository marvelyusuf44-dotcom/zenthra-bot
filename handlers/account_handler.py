from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime
from handlers.auth import is_allowed
from config import ADMIN_USERNAME, COMMUNITY_CHANNEL

def _back_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Back to Menu", callback_data="main_menu")]
    ])

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = update.effective_user.id
    username = update.effective_user.username
    username_display = f"@{username}" if username else "N/A"

    if not is_allowed(user_id):
        await query.edit_message_text("❌ Access denied.")
        return

    # Hitung expired date dan remaining days
    try:
        import json, os
        from config import USERS_FILE
        users = {}
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE) as f:
                users = json.load(f)
        user_data = users.get(str(user_id), {})
        expired_str = user_data.get("expired", "2030-12-31T23:59:59")
        expired_dt = datetime.fromisoformat(expired_str)
        remaining = (expired_dt - datetime.now()).days
        expired_display = expired_dt.strftime("%d %b %Y")
        remaining_display = f"{remaining:,} days"
        status = "✅ Active" if remaining > 0 else "❌ Expired"
    except:
        expired_display = "N/A"
        remaining_display = "N/A"
        status = "✅ Active"

    community = COMMUNITY_CHANNEL.replace("https://", "")

    text = (
        f"👤 <b>ACCOUNT INFO</b>\n"
        f"{'─'*22}\n"
        f"🆔 <b>User ID</b>   : {user_id}\n"
        f"📛 <b>Username</b>  : {username_display}\n"
        f"{'─'*22}\n"
        f"📡 <b>Status</b>    : {status}\n"
        f"📅 <b>Expires</b>   : {expired_display}\n"
        f"⏳ <b>Remaining</b> : {remaining_display}\n"
        f"{'─'*22}\n"
        f"🔓 <b>Access</b>    : Full Access\n"
        f"🔔 <b>Monitor</b>   : Enabled\n"
        f"📊 <b>Signals</b>   : Unlimited\n"
        f"{'─'*22}\n"
        f"📢 <b>Community</b>\n"
        f"{community}\n\n"
        f"💬 <b>Support</b>\n"
        f"@{ADMIN_USERNAME}\n"
        f"{'─'*22}\n"
        f"⚠️ <b>Security Notice</b>\n"
        f"We will NEVER ask for your\n"
        f"seed phrase or private keys.\n"
        f"Do not share your account\n"
        f"info with anyone."
    )

    await query.edit_message_text(text, reply_markup=_back_kb(), parse_mode="HTML")

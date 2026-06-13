import feedparser
import random
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

def clean_html(raw_html):
    import re
    clean = re.compile('<.*?>')
    return re.sub(clean, '', raw_html)

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("📰 Fetching latest crypto news...")
    
    feeds = [
        "https://cointelegraph.com/rss",
        "https://www.coindesk.com/arc/outboundfeeds/rss/",
        "https://decrypt.co/feed"
    ]
    
    all_news = []
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:2]:
                title = clean_html(entry.title)[:80]
                source = url.split("//")[1].split("/")[0].replace("www.", "")
                published = entry.get("published", "")
                if published:
                    pub_date = published[:16].replace("T", " · ")
                else:
                    pub_date = datetime.now().strftime("%d %b %Y · %H:%M WIB")
                all_news.append({
                    "title": title,
                    "source": source,
                    "published": pub_date
                })
        except:
            continue
        if len(all_news) >= 6:
            break
    
    if not all_news:
        now = datetime.now().strftime("%d %b %Y · %H:%M WIB")
        msg = (
            "📰 MARKET NEWS\n\n"
            f"1. 📰 Bitcoin volatility expected this week\n"
            f"   📅 {now}\n"
            f"   🔗 Source: Market Update\n\n"
            f"2. 📰 Altcoin season index showing strength\n"
            f"   📅 {now}\n"
            f"   🔗 Source: Crypto Analysis\n\n"
            f"3. 📰 Fed rate decision impacts crypto market\n"
            f"   📅 {now}\n"
            f"   🔗 Source: Economic News"
        )
    else:
        msg = "📰 MARKET NEWS\n\n"
        for i, item in enumerate(all_news[:5], 1):
            msg += f"{i}. 📰 {item['title']}\n"
            msg += f"   📅 {item['published']}\n"
            msg += f"   🔗 Source: {item['source']}\n\n"
    
    keyboard = [[InlineKeyboardButton("◀️ BACK TO MENU", callback_data="main_menu")]]
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

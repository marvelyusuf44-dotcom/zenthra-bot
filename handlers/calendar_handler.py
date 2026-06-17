from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from datetime import datetime, timedelta

def _back_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("◀️ Back to Menu", callback_data="main_menu")]
    ])

# ─── JADWAL EVENT ─────────────────────────────────────────────────────────────
# Update tanggal di sini kalau ada perubahan jadwal resmi
EVENTS = [
    # Format: (nama, tanggal YYYY-MM-DD, kategori, dampak, deskripsi)
    ("FOMC Meeting", "2026-06-17", "Fed", "🔴", "Federal Reserve interest rate decision"),
    ("FOMC Meeting", "2026-07-29", "Fed", "🔴", "Federal Reserve interest rate decision"),
    ("FOMC Meeting", "2026-09-16", "Fed", "🔴", "Federal Reserve interest rate decision"),
    ("FOMC Meeting", "2026-11-04", "Fed", "🔴", "Federal Reserve interest rate decision"),
    ("FOMC Meeting", "2026-12-16", "Fed", "🔴", "Federal Reserve interest rate decision"),

    ("US CPI Data", "2026-06-10", "Macro", "🟠", "US inflation data — high market impact"),
    ("US CPI Data", "2026-07-15", "Macro", "🟠", "US inflation data — high market impact"),
    ("US CPI Data", "2026-08-12", "Macro", "🟠", "US inflation data — high market impact"),
    ("US CPI Data", "2026-09-09", "Macro", "🟠", "US inflation data — high market impact"),

    ("US NFP Jobs", "2026-07-02", "Macro", "🟠", "Non-Farm Payroll — employment data"),
    ("US NFP Jobs", "2026-08-06", "Macro", "🟠", "Non-Farm Payroll — employment data"),
    ("US NFP Jobs", "2026-09-03", "Macro", "🟠", "Non-Farm Payroll — employment data"),

    ("Coinbase Earnings", "2026-08-05", "Crypto", "🟡", "COIN quarterly earnings report"),
    ("MicroStrategy Earnings", "2026-08-06", "Crypto", "🟡", "MSTR quarterly earnings report"),

    ("Bitcoin Halving", "2028-04-15", "Crypto", "🔴", "Next BTC halving — supply cut 50%"),
]

def get_upcoming_events(days_ahead=60):
    now = datetime.now()
    upcoming = []

    for name, date_str, category, impact, desc in EVENTS:
        try:
            event_dt = datetime.strptime(date_str, "%Y-%m-%d")
            days_left = (event_dt - now).days

            if days_left < 0:  # skip event yang sudah lewat (termasuk hari ini kalau sudah lewat jam)
                continue
            if days_left > days_ahead:  # skip event terlalu jauh
                continue

            if days_left == 0:
                time_label = "🔥 TODAY"
            elif days_left == 1:
                time_label = "Tomorrow"
            elif days_left <= 7:
                time_label = f"In {days_left} days ⚡"
            else:
                time_label = f"In {days_left} days"

            upcoming.append({
                "name": name,
                "date": event_dt.strftime("%d %b %Y"),
                "category": category,
                "impact": impact,
                "desc": desc,
                "days_left": days_left,
                "time_label": time_label,
            })
        except:
            continue

    # Sort by date
    upcoming.sort(key=lambda x: x["days_left"])
    return upcoming

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔄 Loading economic calendar...")

    now = datetime.now().strftime("%d %b %Y · %H:%M UTC")
    events = get_upcoming_events(days_ahead=60)

    if not events:
        # Expand to 365 days if nothing in 60 days
        events = get_upcoming_events(days_ahead=365)

    if events:
        lines = []
        for e in events[:8]:
            lines.append(
                f"{e['impact']} <b>{e['name']}</b>\n"
                f"   <b>Date</b>     : {e['date']}\n"
                f"   <b>Countdown</b>: {e['time_label']}\n"
                f"   <b>Category</b> : {e['category']}\n"
                f"   <i>{e['desc']}</i>"
            )

        # Tambah countdown BTC Halving selalu di bawah
        halving_dt = datetime(2028, 4, 15)
        days_to_halving = (halving_dt - datetime.now()).days
        months = days_to_halving // 30
        remaining_days = days_to_halving % 30

        text = (
            f"📅 <b>ECONOMIC CALENDAR</b>\n"
            f"<i>Upcoming events — next 60 days</i>\n"
            f"──────────────────────\n\n"
            + "\n\n".join(lines) +
            f"\n\n──────────────────────\n"
            f"₿ <b>BTC Halving Countdown</b>\n"
            f"   ~{months} months {remaining_days} days remaining\n"
            f"──────────────────────\n"
            f"🔴 High  🟠 Medium  🟡 Low impact\n"
            f"<i>📅 {now}</i>"
        )
    else:
        text = (
            f"📅 <b>ECONOMIC CALENDAR</b>\n"
            f"──────────────────────\n\n"
            f"No upcoming events in next 60 days.\n\n"
            f"<i>📅 {now}</i>"
        )

    await query.edit_message_text(text, reply_markup=_back_kb(), parse_mode="HTML")

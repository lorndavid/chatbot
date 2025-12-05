import logging
import sqlite3
import csv
import io
import re
from datetime import datetime, time, date
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# --------------------------------------------------------------------------------
# ⚙️ SYSTEM CONFIGURATION (ENTERPRISE SETTINGS)
# --------------------------------------------------------------------------------
# REPLACE WITH YOUR NEW TOKEN IF YOU REVOKED THE OLD ONE
BOT_TOKEN = "8420582565:AAHM4qR-nN6iheHTO20TnEYFfJqngb5mVco"
ADMIN_GROUP_ID = -1003238857423 

# ⏰ Business Hours (24h format)
WORK_START = time(7, 30)  # 7:30 AM
WORK_END = time(17, 30)   # 5:30 PM

# --------------------------------------------------------------------------------
# 🇰🇭 PROFESSIONAL LANGUAGE PACK (KHMER ENTERPRISE)
# --------------------------------------------------------------------------------
LANG = {
    # --- HEADERS ---
    "brand_header": "🏢 <b>ប្រព័ន្ធជំនួយនិស្សិតហាត់ការគ្រប់ជំនាន់</b>",
    "ticket_header": "📨 <b>សារថ្មីពីនិស្សិតហាត់ការគ្រប់ជំនាន់ </b>",
    "reply_header": "👨‍💼 <b>ចម្លើយតបពីភ្នាក់ងារ</b>",
    "reply_footer": "\n\n🙏 អរគុណ {name} ដែលបានប្រើប្រាស់ Chat_Bot របស់យើង!",
    "broadcast_header": "📢 <b>សេចក្តីជូនដំណឹងផ្លូវការ (OFFICIAL ANNOUNCEMENT)</b>",
    "report_header": "📊 <b>របាយការណ៍សង្ខេប (DAILY REPORT)</b>",
    "userlist_header": "👥 <b>បញ្ជីអ្នកប្រើប្រាស់ (USER DIRECTORY)</b>",
    "history_header": "📜 <b>ប្រវត្តិការសន្ទនា (CONVERSATION HISTORY)</b>",
    
    # --- ADMIN MENU (KHMER) ---
    "admin_help_text": (
        "🛠 <b>មជ្ឈមណ្ឌលបញ្ជា (ADMIN COMMAND CENTER)</b>\n"
        "─────────────────────────────\n"
        "• <code>/iduser</code> : មើលបញ្ជីអ្នកប្រើប្រាស់ទាំងអស់ (List Users)\n"
        "• <code>/DI-xxx</code> : មើលប្រវត្តិសន្ទនារបស់អតិថិជន (View History)\n"
        "• <code>/report</code> : មើលរបាយការណ៍សង្ខេបប្រចាំថ្ងៃ (Daily Stats)\n"
        "• <code>/report all</code> : ទាញយកឯកសារ Excel ពេញលេញ (Download CSV)\n"
        "• <code>/broadcast [msg]</code> : ផ្ញើសារជូនដំណឹងទៅកាន់អ្នកទាំងអស់គ្នា\n"
        "• <code>/help</code> : បង្ហាញបញ្ជីនេះម្តងទៀត"
    ),

    # --- MENUS ---
    "menu_main_text": (
        "សួស្តី <b>{name}</b>! 👋\n"
        "សូមស្វាគមន៍មកកាន់ប្រព័ន្ធជំនួយការឆ្លាតវៃ។\n\n"
        "🆔 លេខសម្គាល់របស់អ្នក: <code>{display_id}</code>\n\n"
        "យើងខ្ញុំត្រៀមខ្លួនជាស្រេចដើម្បីជួយសម្រួលការងាររបស់លោកអ្នក។\n"
        "សូមជ្រើសរើសប្រតិបត្តិការខាងក្រោម៖"
    ),
    "menu_btn_support": "💬 សន្ទនាជាមួយភ្នាក់ងារ",
    "menu_btn_info": "🏢 ម៉ោងធ្វើការ",
    "menu_btn_profile": "👤 គណនីរបស់ខ្ញុំ",
    "menu_btn_discipline": "📜 វិន័យក្នុង DI",
    
    # --- MESSAGES ---
    "contact_intro": (
        "💬 <b>សេវាកម្មអតិថិជន </b>\n"
        "─────────────────────────────\n"
        "📝 សូមសរសេររៀបរាប់ពីបញ្ហា ឬសំណួររបស់អ្នកនៅទីនេះ។\n"
        "📎 <i>(ប្រព័ន្ធទទួល: អក្សរ, រូបភាព, ឯកសារ PDF/Word, និង សំឡេង)</i>"
    ),
    "ticket_queued": (
        "📥 <b>បានទទួលសារជោគជ័យ!</b>\n"
        "─────────────────────────────\n"
        "🆔 ID: <code>{display_id}</code>\n"
        "⏳ ស្ថានភាព: <b>កំពុងបញ្ជូនទៅកាន់ក្រុមការងារ...</b>\n"
        "─────────────────────────────\n"
        "<i>យើងខ្ញុំនឹងឆ្លើយតបជូនលោកអ្នកក្នុងពេលបន្តិចទៀតនេះ។</i>"
    ),
    "ticket_queued_offline": (
        "\n\n🌙 <b>ក្រៅម៉ោងធ្វើការ</b>\n"
        "បច្ចុប្បន្នយើងស្ថិតនៅក្រៅម៉ោងធ្វើការ។ សំណើរបស់អ្នកត្រូវបានរក្សាទុក ហើយយើងនឹងឆ្លើយតបទៅតាមលទ្ធភាព។"
    ),
    "session_cleared": "♻️ <b>ការសន្ទនាត្រូវបានបិទបញ្ចប់។</b>",
    
    # --- INFO SECTIONS ---
    "info_company": (
        "🏢 <b>ព័ត៌មានក្រុមហ៊ុន (COMPANY PROFILE)</b>\n"
        "─────────────────────────────\n"
        "យើងប្តេជ្ញាផ្តល់ជូននូវបរិយាកាសការងារប្រកបដោយវិជ្ជាជីវៈ និងប្រសិទ្ធភាពខ្ពស់។\n\n"
        "⏰ <b>កាលវិភាគការងារ:</b>\n"
        "🟢 <b>ម៉ោងចូល:</b> 07:30 ព្រឹក\n"
        "☕ <b>សម្រាកពេលព្រឹក:</b> 09:30 - 09:45 ព្រឹក\n"
        "🍽️ <b>សម្រាកអាហារថ្ងៃត្រង់:</b> 11:30 - 12:30 ថ្ងៃត្រង់\n"
        "☕ <b>សម្រាកពេលរសៀល:</b> 02:30 - 02:45 រសៀល\n"
        "🔴 <b>ម៉ោងចេញ:</b> 05:30 ល្ងាច\n\n"
        "📍 <b>ទីតាំង:</b> ភូមិត្រពាំងស្លា ឃំុព្រះនិពាន្ធ ស្រុកកងពិសី ខេត្តកំពង់ស្ពឺ"
    ),
    "info_discipline": (
        "📜 <b>វិន័យ និងគោលការណ៍ការងារក្នុង DI</b>\n"
        "─────────────────────────────\n"
        "ដើម្បីរក្សាបាននូវស្តង់ដារការងារខ្ពស់ និងវប្បធម៌ល្អប្រសើរ យើងសូមណែនាំនូវចំណុចសំខាន់ៗ៖\n\n"
        "1️⃣ <b>ឥរិយាបថ និងសីលធម៌ (Attitude):</b>\n"
        "• ត្រូវមានភាពស្មោះត្រង់ (Honesty) និងការគោរពគ្នាទៅវិញទៅមក។\n"
        "• រក្សាទំនាក់ទំនងល្អជាមួយសហការី និងអតិថិជន។\n"
        "• មានស្មារតីសហការជាក្រុម (Teamwork) និងជួយគ្នាទៅវិញទៅមក។\n\n"
        "2️⃣ <b>ការបំពេញការងារ (Work Ethics):</b>\n"
        "• ត្រូវមកធ្វើការឱ្យទាន់ពេលវេលាដែលបានកំណត់ (07:30 ព្រឹក)។\n"
        "• ទទួលខុសត្រូវខ្ពស់លើភារកិច្ចដែលបានប្រគល់ជូន។\n"
        "• ព្យាយាមអភិវឌ្ឍសមត្ថភាពខ្លួនឯងជាប្រចាំ។\n\n"
        "3️⃣ <b>វិន័យទូទៅ (General Discipline):</b>\n"
        "• គោរពតាមបទបញ្ជាផ្ទៃក្នុងរបស់ក្រុមហ៊ុនយ៉ាងម៉ឺងម៉ាត់។\n"
        "• ចូលរួមថែរក្សាសណ្តាប់ធ្នាប់ និងអនាម័យកន្លែងធ្វើការ។\n"
        "• ប្រើប្រាស់ពេលសម្រាក (Break Time) ឱ្យបានត្រឹមត្រូវ។\n\n"
        "✨ <i>ភាពជោគជ័យរបស់អ្នក គឺជាជោគជ័យរបស់យើងទាំងអស់គ្នា!</i>"
    ),
    "user_profile": (
        "👤 <b>ព័ត៌មានគណនី (MY PROFILE)</b>\n"
        "─────────────────────────────\n"
        "• ឈ្មោះ: <b>{name}</b>\n"
        "• លេខសម្គាល់អចិន្ត្រៃយ៍: <code>{display_id}</code>\n"
        "• ឈ្មោះក្នុងប្រព័ន្ធ: @{username}\n"
        "• ថ្ងៃចុះឈ្មោះ: {date}"
    ),
}

# --------------------------------------------------------------------------------
# 🛠️ LOGGING & DATABASE ENGINE
# --------------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

def init_db():
    conn = sqlite3.connect("relay_bot.db")
    c = conn.cursor()
    
    # 1. Message Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS message_map (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_message_id INTEGER,
            user_id INTEGER,
            user_name TEXT,
            display_id TEXT,
            question_text TEXT,
            created_at TIMESTAMP,
            status TEXT DEFAULT 'PENDING',
            answer_text TEXT,
            admin_responder TEXT
        )
    ''')
    
    # 2. User Directory
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            display_id TEXT, 
            joined_at TIMESTAMP
        )
    ''')
    
    # Indexes for 1000+ Users Performance
    c.execute("CREATE INDEX IF NOT EXISTS idx_users_display_id ON users(display_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_msg_display_id ON message_map(display_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_msg_status ON message_map(status)")
    
    # Migrations
    try: c.execute("ALTER TABLE users ADD COLUMN display_id TEXT")
    except: pass
    try: c.execute("ALTER TABLE message_map ADD COLUMN display_id TEXT")
    except: pass
    try: c.execute("ALTER TABLE message_map ADD COLUMN answer_text TEXT")
    except: pass
        
    conn.commit()
    conn.close()

# --------------------------------------------------------------------------------
# 🧩 DATABASE HELPERS
# --------------------------------------------------------------------------------
def get_or_create_user(user):
    conn = sqlite3.connect("relay_bot.db")
    c = conn.cursor()
    c.execute("SELECT display_id FROM users WHERE user_id=?", (user.id,))
    result = c.fetchone()
    if result and result[0]:
        display_id = result[0]
        c.execute("UPDATE users SET first_name=?, username=? WHERE user_id=?", (user.first_name, user.username, user.id))
    else:
        c.execute("SELECT COUNT(*) FROM users")
        count = c.fetchone()[0]
        new_number = count + 1
        display_id = f"DI-{new_number:03d}"
        c.execute("INSERT OR REPLACE INTO users (user_id, first_name, username, display_id, joined_at) VALUES (?, ?, ?, ?, ?)",
                  (user.id, user.first_name, user.username, display_id, datetime.now()))
    conn.commit()
    conn.close()
    return display_id

def get_user_profile_by_id(user_id):
    conn = sqlite3.connect("relay_bot.db")
    c = conn.cursor()
    c.execute("SELECT first_name, username, joined_at, display_id FROM users WHERE user_id=?", (user_id,))
    return c.fetchone()

def get_user_id_by_display_id(display_id):
    conn = sqlite3.connect("relay_bot.db")
    c = conn.cursor()
    display_id = display_id.upper().replace('_', '-')
    c.execute("SELECT user_id, first_name, username FROM users WHERE display_id=?", (display_id,))
    return c.fetchone()

def get_all_users_details():
    conn = sqlite3.connect("relay_bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id, first_name, username, display_id FROM users")
    data = c.fetchall()
    conn.close()
    return data

def save_message(admin_msg_id, user_id, user_name, display_id, question):
    conn = sqlite3.connect("relay_bot.db")
    c = conn.cursor()
    c.execute("INSERT INTO message_map (admin_message_id, user_id, user_name, display_id, question_text, created_at, status) VALUES (?, ?, ?, ?, ?, ?, ?)", 
              (admin_msg_id, user_id, user_name, display_id, question, datetime.now(), 'PENDING'))
    conn.commit()
    conn.close()

def update_message_answer(admin_msg_id, answer, admin_name):
    conn = sqlite3.connect("relay_bot.db")
    c = conn.cursor()
    c.execute("UPDATE message_map SET status='SOLVED', answer_text=?, admin_responder=? WHERE admin_message_id=?", 
              (answer, admin_name, admin_msg_id))
    conn.commit()
    conn.close()

def get_message_context(admin_msg_id):
    conn = sqlite3.connect("relay_bot.db")
    c = conn.cursor()
    c.execute("SELECT user_id, user_name, display_id FROM message_map WHERE admin_message_id=?", (admin_msg_id,))
    return c.fetchone()

def get_user_history(display_id):
    conn = sqlite3.connect("relay_bot.db")
    c = conn.cursor()
    display_id = display_id.upper().replace('_', '-')
    c.execute("SELECT created_at, question_text, answer_text, admin_responder, status FROM message_map WHERE display_id=? ORDER BY created_at ASC", (display_id,))
    return c.fetchall()

def is_business_hours():
    now = datetime.now().time()
    return WORK_START <= now <= WORK_END

# --------------------------------------------------------------------------------
# 🛡️ ERROR HANDLER (PREVENTS CRASHES)
# --------------------------------------------------------------------------------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and handle it gracefully instead of crashing."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    # Optional: Send a message to admin if needed, but keeping it silent for logs is safer for 24/7 uptime.

# --------------------------------------------------------------------------------
# 👑 ADMIN COMMANDS CENTER
# --------------------------------------------------------------------------------
async def admin_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id != ADMIN_GROUP_ID: return
    await update.message.reply_html(LANG["admin_help_text"])

async def list_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id != ADMIN_GROUP_ID: return
    users = get_all_users_details()
    
    if not users:
        # SAFE SEND: Uses context.bot.send_message instead of reply_text to avoid crashes
        await context.bot.send_message(chat_id=update.effective_chat.id, text="📭 No users yet.")
        return

    msg = f"{LANG['brand_header']}\n{LANG['userlist_header']}\n─────────────────────────────\n"
    for uid, fname, uname, did in users[-30:]:
        u_display = f"@{uname}" if uname else "N/A"
        msg += f"🆔 <b>{did}</b> | 👤 {fname}\n🔗 {u_display} | ID: <code>{uid}</code>\n\n"
    if len(users) > 30: msg += f"<i>(+ {len(users)-30} more users)</i>"
    
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode=ParseMode.HTML)

async def history_lookup_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id != ADMIN_GROUP_ID: return
    try:
        command = update.message.text.split()[0][1:]
        display_id = command.replace('_', '-').upper()
        user_info = get_user_id_by_display_id(display_id)
        if not user_info:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"❌ User ID {display_id} not found.")
            return

        history = get_user_history(display_id)
        msg = (
            f"{LANG['history_header']}\n"
            f"👤 <b>USER: {user_info[1]}</b> ({display_id})\n"
            f"─────────────────────────────\n\n"
        )
        if not history:
            msg += "<i>No message history found.</i>"
        else:
            for row in history[-15:]:
                date_str = row[0].split('.')[0]
                q_text = row[1] or "[Media/File]"
                ans_text = row[2]
                responder = row[3]
                status = row[4]
                status_icon = "🟢" if status == 'SOLVED' else "🟡"
                msg += f"📅 <b>{date_str}</b> {status_icon}\n"
                msg += f"🗣 <b>Q:</b> {q_text}\n"
                if ans_text:
                    msg += f"👨‍💼 <b>A:</b> {ans_text} ({responder})\n"
                msg += "──────────────────\n"
            if len(history) > 15:
                msg += f"\n<i>...and {len(history)-15} older messages.</i>"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode=ParseMode.HTML)
    except Exception as e:
        logger.error(f"Lookup error: {e}")

async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id != ADMIN_GROUP_ID: return
    args = context.args
    
    if args and args[0].lower() in ['all', 'full', 'csv']:
        conn = sqlite3.connect("relay_bot.db")
        c = conn.cursor()
        c.execute("SELECT display_id, user_name, question_text, status, created_at, answer_text, admin_responder FROM message_map ORDER BY created_at DESC")
        data = c.fetchall()
        conn.close()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['User Ref ID', 'Name', 'Question', 'Status', 'Date', 'Admin Response', 'Admin Name'])
        writer.writerows(data)
        
        bio = io.BytesIO(b'\xef\xbb\xbf' + output.getvalue().encode('utf-8'))
        bio.name = f"Report_{date.today()}.csv"
        await context.bot.send_document(chat_id=ADMIN_GROUP_ID, document=bio, caption="📊 <b>Full Export (With Responses)</b>", parse_mode=ParseMode.HTML)
        return

    conn = sqlite3.connect("relay_bot.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*), SUM(CASE WHEN status='PENDING' THEN 1 ELSE 0 END) FROM message_map")
    total, pending = c.fetchone()
    pending = pending or 0
    c.execute("SELECT display_id, user_name, question_text FROM message_map WHERE status='PENDING' ORDER BY created_at DESC LIMIT 5")
    recent = c.fetchall()
    conn.close()

    msg = (
        f"{LANG['report_header']}\n"
        f"─────────────────────────────\n"
        f"📅 <b>{date.today().strftime('%B %d, %Y')}</b>\n"
        f"📈 Total Messages: <b>{total}</b>\n"
        f"⚠️ Pending Action: <b>{pending}</b>\n\n"
        f"📋 <b>URGENT QUEUE (Latest):</b>\n"
    )
    if recent:
        for t in recent:
            q = (t[2][:30] + '..') if t[2] else "[Media]"
            msg += f"• <code>{t[0]}</code> | {t[1]}: {q}\n"
    else:
        msg += "✨ <i>No pending tickets.</i>"
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode=ParseMode.HTML)

# --------------------------------------------------------------------------------
# 👤 USER INTERFACE & MENUS
# --------------------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    display_id = get_or_create_user(user)

    keyboard = [
        [InlineKeyboardButton(LANG["menu_btn_support"], callback_data="btn_support")],
        [InlineKeyboardButton(LANG["menu_btn_info"], callback_data="btn_info"), InlineKeyboardButton(LANG["menu_btn_discipline"], callback_data="btn_discipline")],
        [InlineKeyboardButton(LANG["menu_btn_profile"], callback_data="btn_profile")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_html(
        f"{LANG['brand_header']}\n\n" + 
        LANG['menu_main_text'].format(name=user.first_name, display_id=display_id),
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user
    display_id = get_or_create_user(user)

    if data == "btn_support":
        await query.message.reply_html(LANG["contact_intro"])
    elif data == "btn_info":
        await query.message.reply_html(LANG["info_company"])
    elif data == "btn_discipline":
        await query.message.reply_html(LANG["info_discipline"])
    elif data == "btn_profile":
        profile = get_user_profile_by_id(user.id)
        joined_date = profile[2].split()[0] if profile else "N/A"
        await query.message.reply_html(LANG["user_profile"].format(
            name=user.full_name, display_id=display_id, uid=user.id, username=user.username or "None", date=joined_date
        ))

# --------------------------------------------------------------------------------
# 📨 MESSAGE HANDLER (USER -> ADMIN)
# --------------------------------------------------------------------------------
async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id == ADMIN_GROUP_ID: return

    if update.message.text and update.message.text.upper() == "CLEAR":
        await update.message.reply_html(LANG["session_cleared"])
        return

    user = update.effective_user
    display_id = get_or_create_user(user)
    question_content = update.message.text or "[Media/File]"
    
    admin_text = (
        f"{LANG['ticket_header']} <code>{display_id}</code>\n"
        f"─────────────────────────────\n"
        f"👤 <b>User:</b> {user.full_name}\n"
        f"🔗 <b>Link:</b> @{user.username or 'NoUser'}\n\n"
    )

    sent_msg = None
    try:
        if update.message.text:
            admin_text += f"💬 <b>Question:</b>\n{update.message.text}"
            sent_msg = await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=admin_text, parse_mode=ParseMode.HTML)
        elif update.message.photo:
            admin_text += f"🖼 <b>Photo</b>\n{update.message.caption or ''}"
            sent_msg = await context.bot.send_photo(chat_id=ADMIN_GROUP_ID, photo=update.message.photo[-1].file_id, caption=admin_text, parse_mode=ParseMode.HTML)
        elif update.message.document:
            admin_text += f"📂 <b>File</b>\n{update.message.caption or ''}"
            sent_msg = await context.bot.send_document(chat_id=ADMIN_GROUP_ID, document=update.message.document.file_id, caption=admin_text, parse_mode=ParseMode.HTML)
        elif update.message.voice:
            admin_text += "🎤 <b>Voice</b>"
            sent_msg = await context.bot.send_voice(chat_id=ADMIN_GROUP_ID, voice=update.message.voice.file_id, caption=admin_text, parse_mode=ParseMode.HTML)

        if sent_msg:
            save_message(sent_msg.message_id, user.id, user.full_name, display_id, question_content)
            receipt_msg = LANG["ticket_queued"].format(display_id=display_id)
            if not is_business_hours():
                receipt_msg += LANG["ticket_queued_offline"]
            await update.message.reply_html(receipt_msg)
    except Exception as e:
        logger.error(f"Relay Error: {e}")
        # Silent fail or simple message to avoid loops

# --------------------------------------------------------------------------------
# 👨‍💼 REPLY HANDLER (ADMIN -> USER)
# --------------------------------------------------------------------------------
async def handle_admin_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id != ADMIN_GROUP_ID or not update.message.reply_to_message: return 

    replied_msg_id = update.message.reply_to_message.message_id
    mapping = get_message_context(replied_msg_id)
    
    if mapping:
        user_id, user_name, display_id = mapping
        admin_name = update.effective_user.full_name or "Support Agent"
        answer_content = update.message.text or "[Media/File]"
        
        try:
            # Prepare Reply
            header = f"{LANG['reply_header']}\n─────────────────────────────\n"
            # Add footer with user's name
            footer = LANG["reply_footer"].format(name=user_name)
            
            if update.message.text:
                full_text = f"{header}{update.message.text}{footer}"
                await context.bot.send_message(chat_id=user_id, text=full_text, parse_mode=ParseMode.HTML)
            elif update.message.photo:
                caption = f"{header}{update.message.caption or ''}{footer}"
                await context.bot.send_photo(chat_id=user_id, photo=update.message.photo[-1].file_id, caption=caption, parse_mode=ParseMode.HTML)
            elif update.message.voice:
                caption = f"{header} (Voice Message){footer}"
                await context.bot.send_voice(chat_id=user_id, voice=update.message.voice.file_id, caption=caption, parse_mode=ParseMode.HTML)

            # Update DB (Mark solved)
            update_message_answer(replied_msg_id, answer_content, admin_name)
            await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=f"✅ <b>Sent to {user_name} ({display_id})</b>", parse_mode=ParseMode.HTML)
            
        except Exception as e:
            await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=f"❌ Failed to send: {e}")
    else:
        if not update.message.text.startswith("/"):
            await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text="⚠️ Ticket context lost (Old message).")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id != ADMIN_GROUP_ID: return
    msg = " ".join(context.args)
    if not msg: 
        await update.message.reply_text("Usage: /broadcast [Message]")
        return
    
    users = get_all_users_details()
    ids = [row[0] for row in users]
    count = 0
    formatted = f"{LANG['broadcast_header']}\n─────────────────────────────\n{msg}"
    
    status = await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=f"⏳ Sending to {len(ids)} users...")
    for uid in ids:
        try:
            await context.bot.send_message(chat_id=uid, text=formatted, parse_mode=ParseMode.HTML)
            count += 1
        except: pass
    await context.bot.edit_message_text(chat_id=ADMIN_GROUP_ID, message_id=status.message_id, text=f"✅ Successfully sent to {count} users.")

# --------------------------------------------------------------------------------
# 🚀 MAIN APPLICATION
# --------------------------------------------------------------------------------
def main() -> None:
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()

    # Admin Commands
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("report", report_command))
    application.add_handler(CommandHandler("iduser", list_users_command))
    application.add_handler(CommandHandler("help", admin_help_command))
    
    # Matches /DI-001 or /DI_001
    application.add_handler(MessageHandler(filters.Regex(r'^/DI[-_]\d+'), history_lookup_handler))

    # User Interactions
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("clear", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    # Messages
    application.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & ~filters.COMMAND & (filters.TEXT | filters.PHOTO | filters.Document.ALL | filters.VOICE),
        handle_user_message
    ))

    # Admin Replies
    application.add_handler(MessageHandler(filters.Chat(chat_id=ADMIN_GROUP_ID) & filters.REPLY, handle_admin_reply))

    # REGISTER GLOBAL ERROR HANDLER
    application.add_error_handler(error_handler)

    print("🚀 Enterprise Infinity Bot v5 is ONLINE...")
    application.run_polling()

if __name__ == "__main__":
    main()
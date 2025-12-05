import logging
import sqlite3
import csv
import io
import re
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, time, date
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReactionTypeEmoji, BotCommand
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
BOT_TOKEN = "8420582565:AAFnas6tEcRlgyc-rybb6qcF9BEjeF-3T0k"
ADMIN_GROUP_ID = -1003325498790

# --------------------------------------------------------------------------------
# 🌐 FAKE WEB SERVER (FOR RENDER HOSTING)
# --------------------------------------------------------------------------------
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive and running!")

def start_web_server():
    port = int(os.environ.get('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"🌍 Fake Web Server started on port {port}")
    server.serve_forever()

# --------------------------------------------------------------------------------
# 🇰🇭 PROFESSIONAL LANGUAGE PACK (KHMER ENTERPRISE)
# --------------------------------------------------------------------------------
LANG = {
    "brand_header": "🏢 <b>ប្រព័ន្ធជំនួយនិស្សិតហាត់ការគ្រប់ជំនាន់</b>",
    "reply_header": "👨‍💼 <b>ដំណោះស្រាយពីក្រុមការងារ IT_Support</b>",
    "reply_footer": "\n\n🙏 អរគុណ <b>{name}</b> ដែលបានប្រើប្រាស់ Chat_Bot របស់យើង! បើមានសំណើរឬបញ្ហាផ្សេងទៀត សូមទាក់ទងមកក្រុមការងារយើងវិញ។",
    "broadcast_header": "📢 <b>សេចក្តីជូនដំណឹងផ្លូវការ</b>",
    "report_header": "📊 <b>របាយការណ៍សង្ខេប</b>",
    "userlist_header": "👥 <b>បញ្ជីអ្នកប្រើប្រាស់</b>",
    "history_header": "📜 <b>ប្រវត្តិការសន្ទនា</b>",
    "admin_help_text": (
        "🛠 <b>មជ្ឈមណ្ឌលបញ្ជា</b>\n"
        "───────────────\n"
        "• <code>/iduser</code> : មើលបញ្ជីអ្នកប្រើប្រាស់ទាំងអស់\n"
        "• <code>/DI-xxx</code> : មើលប្រវត្តិសន្ទនារបស់អតិថិជន\n"
        "• <code>/report</code> : មើលរបាយការណ៍ប្រចាំថ្ងៃ\n"
        "• <code>/reportall</code> : ទាញយកឯកសារ Excel\n"
        "• <code>/broadcast [msg]</code> : ផ្ញើសារជូនដំណឹងទៅកាន់អ្នកទាំងអស់គ្នា\n"
        "• <code>/help</code> : បង្ហាញបញ្ជីនេះម្តងទៀត"
    ),
    "menu_main_text": (
        "សួស្តី, <b>{name}</b>! 👋\n"
        "សូមស្វាគមន៍មកកាន់ប្រព័ន្ធដោះស្រាយបញ្ហា។\n\n"
        "🆔 លេខសម្គាល់របស់អ្នក: <code>{display_id}</code>\n\n"
        "យើងខ្ញុំត្រៀមខ្លួនជាស្រេចដើម្បីជួយដោះស្រាយនិងសម្រួលបញ្ហារបស់លោកអ្នក។\n"
        "សូមចុចប៊ូតុងខាងក្រោម👇"
    ),
    "menu_btn_support": "💬 សុំជំនួយពីក្រុមការងារ IT_Support",
    "contact_intro": (
        "💬 <b>ដោះស្រាយបញ្ហាផ្សេងៗតាម Chat_Bot</b>\n"
        "───────────────\n"
        "📝 តើអ្នកមានបញ្ហាអ្វី​? តើអ្នកមានអ្វីឳ្យជួយដោះស្រាយ?\n"
    ),
    "session_cleared": "♻️ <b>ការសន្ទនាត្រូវបានបិទបញ្ចប់។</b>",
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
    
    # 1. Message Table (User Questions)
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

    # 3. Reply Tracking (NEW: Maps Admin Group Message -> User Chat Message for Editing)
    c.execute('''
        CREATE TABLE IF NOT EXISTS reply_tracking (
            admin_msg_id INTEGER PRIMARY KEY,
            user_chat_id INTEGER,
            sent_msg_id INTEGER,
            admin_name TEXT,
            user_name TEXT
        )
    ''')
    
    # Indexes
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

def save_reply_tracking(admin_msg_id, user_chat_id, sent_msg_id, admin_name, user_name):
    """Saves the link between Admin Group Message and User Private Message for editing."""
    conn = sqlite3.connect("relay_bot.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO reply_tracking (admin_msg_id, user_chat_id, sent_msg_id, admin_name, user_name) VALUES (?, ?, ?, ?, ?)",
              (admin_msg_id, user_chat_id, sent_msg_id, admin_name, user_name))
    conn.commit()
    conn.close()

def get_reply_tracking(admin_msg_id):
    conn = sqlite3.connect("relay_bot.db")
    c = conn.cursor()
    c.execute("SELECT user_chat_id, sent_msg_id, admin_name, user_name FROM reply_tracking WHERE admin_msg_id=?", (admin_msg_id,))
    return c.fetchone()

# --------------------------------------------------------------------------------
# 🛡️ ERROR HANDLER
# --------------------------------------------------------------------------------
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

# --------------------------------------------------------------------------------
# 👑 ADMIN COMMANDS
# --------------------------------------------------------------------------------
async def admin_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id != ADMIN_GROUP_ID: return
    await update.message.reply_html(LANG["admin_help_text"])

async def list_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id != ADMIN_GROUP_ID: return
    users = get_all_users_details()
    
    if not users:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="📭 No users yet.")
        return

    msg = f"{LANG['brand_header']}\n{LANG['userlist_header']}\n───────────────\n"
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
            f"───────────────\n\n"
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
    
    if context.args and context.args[0].lower() in ['all', 'full', 'csv']:
        await report_all_command(update, context)
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
        f"───────────────\n"
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

async def report_all_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id != ADMIN_GROUP_ID: return
    
    await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text="⏳ Generating full Excel report...")

    conn = sqlite3.connect("relay_bot.db")
    c = conn.cursor()
    c.execute("SELECT display_id, user_name, question_text, status, created_at, answer_text, admin_responder FROM message_map ORDER BY created_at DESC")
    data = c.fetchall()
    conn.close()

    clean_data = []
    for row in data:
        clean_data.append([str(x) if x is not None else "" for x in row])

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['User ID', 'Name', 'Question', 'Status', 'Date', 'Admin Response', 'Admin Name'])
    writer.writerows(clean_data)
    
    bio = io.BytesIO(b'\xef\xbb\xbf' + output.getvalue().encode('utf-8'))
    bio.name = f"Full_Report_{date.today()}.csv"
    
    await context.bot.send_document(chat_id=ADMIN_GROUP_ID, document=bio, caption="📊 <b>Full Export (Excel/CSV)</b>", parse_mode=ParseMode.HTML)

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.id != ADMIN_GROUP_ID: return
    msg = " ".join(context.args)
    if not msg: 
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Usage: /broadcast [Message]")
        return
    
    users = get_all_users_details()
    ids = [row[0] for row in users]
    count = 0
    formatted = f"{LANG['broadcast_header']}\n───────────────\n{msg}"
    
    status = await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=f"⏳ Sending to {len(ids)} users...")
    for uid in ids:
        try:
            await context.bot.send_message(chat_id=uid, text=formatted, parse_mode=ParseMode.HTML)
            count += 1
        except: pass
    await context.bot.edit_message_text(chat_id=ADMIN_GROUP_ID, message_id=status.message_id, text=f"✅ Successfully sent to {count} users.")

# --------------------------------------------------------------------------------
# 👤 USER INTERFACE & MENUS
# --------------------------------------------------------------------------------
async def post_init(application: Application) -> None:
    """Sets the persistent menu button for users."""
    await application.bot.set_my_commands([
        BotCommand("start", "Start Menu / ប៉ឺម៉ឺនុយដើម"),
        BotCommand("help", "Help / ជំនួយ"),
        BotCommand("clear", "End Chat / បញ្ចប់")
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    display_id = get_or_create_user(user)

    keyboard = [
        [InlineKeyboardButton(LANG["menu_btn_support"], callback_data="btn_support")]
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
    display_id = get_or_create_user(query.from_user)

    if data == "btn_support":
        await query.message.reply_html(LANG["contact_intro"])

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
        f"👤 <b>ឈ្មោះ:</b> {user.full_name}\n"
        f"───────────────\n"
    )

    sent_msg = None
    try:
        if update.message.text:
            admin_text += f"💬 <b>សំណួរ :</b>{update.message.text}"
            sent_msg = await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=admin_text, parse_mode=ParseMode.HTML)
        elif update.message.photo:
            admin_text += f"🖼 <b>រូបភាព</b>\n{update.message.caption or ''}"
            sent_msg = await context.bot.send_photo(chat_id=ADMIN_GROUP_ID, photo=update.message.photo[-1].file_id, caption=admin_text, parse_mode=ParseMode.HTML)
        elif update.message.document:
            admin_text += f"📂 <b>ឯកសារ</b>\n{update.message.caption or ''}"
            sent_msg = await context.bot.send_document(chat_id=ADMIN_GROUP_ID, document=update.message.document.file_id, caption=admin_text, parse_mode=ParseMode.HTML)
        elif update.message.video:
            admin_text += f"🎥 <b>វីដេអូ</b>\n{update.message.caption or ''}"
            sent_msg = await context.bot.send_video(chat_id=ADMIN_GROUP_ID, video=update.message.video.file_id, caption=admin_text, parse_mode=ParseMode.HTML)
        elif update.message.voice:
            admin_text += "🎤 <b>សំឡេង</b>"
            sent_msg = await context.bot.send_voice(chat_id=ADMIN_GROUP_ID, voice=update.message.voice.file_id, caption=admin_text, parse_mode=ParseMode.HTML)

        if sent_msg:
            save_message(sent_msg.message_id, user.id, user.full_name, display_id, question_content)
            try:
                await update.message.set_reaction(reaction=[ReactionTypeEmoji("❤")])
            except Exception:
                pass 
            
    except Exception as e:
        logger.error(f"Relay Error: {e}")

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
        
        sent_user_msg = None
        
        try:
            header = f"{LANG['reply_header']}\n───────────────\n"
            footer = LANG["reply_footer"].format(name=user_name)
            admin_label = f"<b>ឆ្លើយតប :</b> "

            if update.message.text:
                full_text = f"{header}{admin_label}{update.message.text}{footer}"
                sent_user_msg = await context.bot.send_message(chat_id=user_id, text=full_text, parse_mode=ParseMode.HTML)
            
            elif update.message.photo:
                caption_text = update.message.caption or ""
                full_caption = f"{header}{admin_label}{caption_text}{footer}"
                sent_user_msg = await context.bot.send_photo(chat_id=user_id, photo=update.message.photo[-1].file_id, caption=full_caption, parse_mode=ParseMode.HTML)
            
            elif update.message.document:
                caption_text = update.message.caption or ""
                full_caption = f"{header}{admin_label}{caption_text}{footer}"
                sent_user_msg = await context.bot.send_document(chat_id=user_id, document=update.message.document.file_id, caption=full_caption, parse_mode=ParseMode.HTML)

            elif update.message.video:
                caption_text = update.message.caption or ""
                full_caption = f"{header}{admin_label}{caption_text}{footer}"
                sent_user_msg = await context.bot.send_video(chat_id=user_id, video=update.message.video.file_id, caption=full_caption, parse_mode=ParseMode.HTML)

            elif update.message.voice:
                full_caption = f"{header}{admin_label}(Voice Message){footer}"
                sent_user_msg = await context.bot.send_voice(chat_id=user_id, voice=update.message.voice.file_id, caption=full_caption, parse_mode=ParseMode.HTML)

            # Update DB and React
            update_message_answer(replied_msg_id, answer_content, admin_name)
            try: await update.message.set_reaction(reaction=[ReactionTypeEmoji("❤")])
            except: await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text="✅ Sent")
            
            # --- NEW: Save Tracking info for Edits ---
            if sent_user_msg:
                save_reply_tracking(update.message.message_id, user_id, sent_user_msg.message_id, admin_name, user_name)
            
        except Exception as e:
            await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=f"❌ Failed to send: {e}")
    else:
        if not update.message.text.startswith("/"):
            await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text="⚠️ Ticket context lost (Old message).")

# --------------------------------------------------------------------------------
# ✏️ EDIT HANDLER (ADMIN EDITS MESSAGE -> UPDATES USER)
# --------------------------------------------------------------------------------
async def handle_admin_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles edits in the Admin Group and updates the message sent to the user."""
    if update.effective_chat.id != ADMIN_GROUP_ID: return
    
    # Check if the update is an edited message
    edited_msg = update.edited_message
    if not edited_msg: return

    # Look up if this message was sent to a user
    tracking = get_reply_tracking(edited_msg.message_id)
    # tracking: (user_chat_id, sent_msg_id, admin_name, user_name)
    
    if tracking:
        user_chat_id, sent_msg_id, admin_name, user_name = tracking
        
        try:
            # Reconstruct the message
            header = f"{LANG['reply_header']}\n───────────────\n"
            footer = LANG["reply_footer"].format(name=user_name)
            admin_label = f"<b>ឆ្លើយតប :</b> "
            
            if edited_msg.text:
                full_text = f"{header}{admin_label}{edited_msg.text}{footer}"
                await context.bot.edit_message_text(
                    chat_id=user_chat_id,
                    message_id=sent_msg_id,
                    text=full_text,
                    parse_mode=ParseMode.HTML
                )
                
            elif edited_msg.caption:
                # If admin edits caption of media
                full_caption = f"{header}{admin_label}{edited_msg.caption}{footer}"
                await context.bot.edit_message_caption(
                    chat_id=user_chat_id,
                    message_id=sent_msg_id,
                    caption=full_caption,
                    parse_mode=ParseMode.HTML
                )
            
        except Exception as e:
            logger.error(f"Failed to sync edit: {e}")

# --------------------------------------------------------------------------------
# 🚀 MAIN APPLICATION
# --------------------------------------------------------------------------------
def main() -> None:
    # START THE FAKE WEB SERVER FOR RENDER
    threading.Thread(target=start_web_server, daemon=True).start()

    init_db()
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("report", report_command))
    application.add_handler(CommandHandler("reportall", report_all_command))
    application.add_handler(CommandHandler("iduser", list_users_command))
    application.add_handler(CommandHandler("help", admin_help_command))
    
    application.add_handler(MessageHandler(filters.Regex(r'^/DI[-_]\d+'), history_lookup_handler))

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("clear", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    # MESSAGE HANDLER (New messages)
    application.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & ~filters.COMMAND & (filters.TEXT | filters.PHOTO | filters.Document.ALL | filters.VIDEO | filters.VOICE),
        handle_user_message
    ))

    # ADMIN REPLY HANDLER
    application.add_handler(MessageHandler(filters.Chat(chat_id=ADMIN_GROUP_ID) & filters.REPLY & ~filters.UpdateType.EDITED_MESSAGE, handle_admin_reply))

    # --- NEW: ADMIN EDIT HANDLER ---
    application.add_handler(MessageHandler(
        filters.Chat(chat_id=ADMIN_GROUP_ID) & filters.UpdateType.EDITED_MESSAGE,
        handle_admin_edit
    ))

    application.add_error_handler(error_handler)

    print("🚀 Enterprise Infinity Bot v15 (Live Edit Sync) is ONLINE...")
    application.run_polling()

if __name__ == "__main__":
    main()

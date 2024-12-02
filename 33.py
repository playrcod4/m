import sqlite3
from telebot import TeleBot, types
import os

# إعداد البوت
API_TOKEN = "7566941918:AAHr-OD73A7wY_ia0kwGMGdL3NbNDbYC2Oo"  # استبدل برمز البوت الخاص بك
bot = TeleBot(API_TOKEN)

# معرف الأدمن
ADMIN_ID = 1900509620  # استبدل بمعرف الأدمن
ADMINS = [ADMIN_ID]  # تبدأ القائمة بمعرف الأدمن الأساسي فقط    
# مسار حفظ الملفات
FILES_DIR = "bot_files"
if not os.path.exists(FILES_DIR):
    os.mkdir(FILES_DIR)

# إنشاء قاعدة البيانات
def init_db():
    with sqlite3.connect("bot_data.db") as conn:
        cursor = conn.cursor()

        # إنشاء جدول الأقسام
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            parent_id INTEGER DEFAULT NULL
        )
        """)

        # إنشاء جدول الأزرار
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS buttons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_id INTEGER,
            name TEXT NOT NULL UNIQUE,
            FOREIGN KEY (section_id) REFERENCES sections(id)
        )
        """)

        # إنشاء جدول الملفات المرتبطة بالأزرار
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS button_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            button_id INTEGER NOT NULL,
            file_type TEXT NOT NULL,
            file_path TEXT NOT NULL,
            FOREIGN KEY (button_id) REFERENCES buttons(id)
        )
        """)

        # إنشاء جدول الملفات العامة
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            button_id INTEGER,
            file_path TEXT NOT NULL,
            FOREIGN KEY (button_id) REFERENCES buttons(id)
        )
        """)

        # إنشاء جدول النصوص المرتبطة بالأزرار
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS texts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            button_id INTEGER,
            text_content TEXT NOT NULL,
            FOREIGN KEY (button_id) REFERENCES buttons(id)
        )
        """)

        # إنشاء جدول المستخدمين
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            join_date TEXT,
            last_active TEXT
        )
        """)

        conn.commit()

# استدعاء الدالة لإنشاء الجداول عند بدء تشغيل البوت
init_db()
# التحقق من الأدمن
def is_admin(user_id):
    return user_id in ADMINS

# استرجاع ID القسم
def get_section_id(section_name):
    with sqlite3.connect("bot_data.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM sections WHERE name = ?", (section_name,))
        result = cursor.fetchone()
        return result[0] if result else None

# استرجاع parent_id
def get_parent_id(section_id):
    if section_id is None:
        return None
    with sqlite3.connect("bot_data.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT parent_id FROM sections WHERE id = ?", (section_id,))
        result = cursor.fetchone()
        return result[0] if result else None

# حفظ المستخدمين عند إرسال /start
@bot.message_handler(commands=['start'])
def start_message(message):
    with sqlite3.connect("bot_data.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR IGNORE INTO users (user_id, join_date, last_active) 
        VALUES (?, date('now'), date('now'))
        """, (message.chat.id,))
        cursor.execute("""
        UPDATE users SET last_active = date('now') WHERE user_id = ?
        """, (message.chat.id,))
        conn.commit()

    if is_admin(message.chat.id):
        admin_controls(message)
    else:
        send_user_sections_and_buttons(message)
# عرض لوحة التحكم للأدمن
def admin_controls(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(
        types.KeyboardButton("➕ إنشاء قسم"),
        types.KeyboardButton("➕ إنشاء زر"),
        types.KeyboardButton("🗑️ حذف قسم"),
        types.KeyboardButton("🗑️ حذف زر"),
        types.KeyboardButton(" عرض الأقسام والأزرار"),
        types.KeyboardButton("📢 إذاعة"),
        types.KeyboardButton("📊 عدد المستخدمين"),
        types.KeyboardButton("✏️ تعديل محتوى زر"),
        types.KeyboardButton("🗑️ حذف محتوى زر"),
        types.KeyboardButton("➕ إضافة أدمن"),
        types.KeyboardButton("🗑️ حذف أدمن")
    )
    bot.send_message(message.chat.id, "اختر أحد الخيارات:", reply_markup=markup)

# عرض الأقسام والأزرار للمستخدمين
def send_user_sections_and_buttons(message, parent_id=None):
    with sqlite3.connect("bot_data.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM sections WHERE parent_id IS ?", (parent_id,))
        sections = cursor.fetchall()
        cursor.execute("SELECT id, name FROM buttons WHERE section_id IS ?", (parent_id,))
        buttons = cursor.fetchall()

    # إنشاء قائمة الأزرار
    items = [f" {section_name}" for _, section_name in sections] + \
            [f" {button_name}" for _, button_name in buttons]

    # إضافة زر العودة وزر القائمة الرئيسية
    if parent_id is not None:
        items.append("⬅️ العودة")
    if parent_id is not None or sections or buttons:
        items.append("🏠 القائمة الرئيسية")

    # التحقق من وجود خيارات للعرض
    if not items:
        items.append(" لا توجد أقسام أو أزرار للعرض.")

    # إنشاء لوحة المفاتيح
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(*items)

    bot.send_message(message.chat.id, "اختر من الأقسام أو الأزرار المتاحة:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_user_input, parent_id)
# التعامل مع تنقل المستخدم بين الأقسام والأزرار
def handle_user_input(message, parent_id):
    text = message.text

    if text.startswith(" "):  # اختيار قسم
        section_name = text.replace(" ", "").strip()
        new_parent_id = get_section_id(section_name)
        if new_parent_id is not None:
            send_user_sections_and_buttons(message, new_parent_id)
        else:
            bot.send_message(message.chat.id, " القسم غير موجود.")
    elif text == "⬅️ العودة":  # العودة للقسم السابق
        parent_section_id = get_parent_id(parent_id)
        send_user_sections_and_buttons(message, parent_section_id)
    elif text == "🏠 القائمة الرئيسية":  # العودة للقائمة الرئيسية
        send_user_sections_and_buttons(message, None)
    elif text.startswith(" "):  # زر
        button_name = text.replace(" ", "").strip()
        with sqlite3.connect("bot_data.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT id FROM buttons WHERE name = ?
            """, (button_name,))
            button_id = cursor.fetchone()
        
        if button_id:
            button_id = button_id[0]
            cursor.execute("""
            SELECT file_type, file_path FROM button_files WHERE button_id = ?
            """, (button_id,))
            files = cursor.fetchall()

            # إرسال جميع الملفات المرتبطة بالزر
            for file_type, file_path in files:
                if file_type == "document":
                    with open(file_path, "rb") as f:
                        bot.send_document(message.chat.id, f)
                elif file_type == "image":
                    with open(file_path, "rb") as f:
                        bot.send_photo(message.chat.id, f)
                elif file_type == "audio":
                    with open(file_path, "rb") as f:
                        bot.send_audio(message.chat.id, f)
                elif file_type == "text":
                    with open(file_path, "r") as f:
                        bot.send_message(message.chat.id, f.read())
        else:
            bot.send_message(message.chat.id, " الزر غير موجود.")
    else:
        bot.send_message(message.chat.id, " خيار غير صحيح. حاول مرة أخرى.")
 # إنشاء قسم        
@bot.message_handler(func=lambda message: message.text == "➕ إنشاء قسم")
def create_section_start(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(types.KeyboardButton(" (رئيسي)"))

    with sqlite3.connect("bot_data.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM sections")
        sections = cursor.fetchall()
    for _, section_name in sections:
        markup.add(types.KeyboardButton(f" {section_name}"))

    bot.send_message(message.chat.id, "اختر القسم الذي تريد إنشاء القسم الجديد داخله، أو اختر (رئيسي):", reply_markup=markup)
    bot.register_next_step_handler(message, save_section_step)

def save_section_step(message):
    section_name = message.text.replace(" ", "").strip()
    parent_id = None if section_name == "(رئيسي)" else get_section_id(section_name)

    if parent_id is None and section_name != "(رئيسي)":
        bot.send_message(message.chat.id, " القسم غير موجود.")
        return

    bot.send_message(message.chat.id, "أرسل اسم القسم الجديد:")
    bot.register_next_step_handler(message, save_section, parent_id)

def save_section(message, parent_id):
    section_name = message.text
    with sqlite3.connect("bot_data.db") as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO sections (name, parent_id) VALUES (?, ?)", (section_name, parent_id))
        conn.commit()
    bot.send_message(message.chat.id, f"✅ تم إنشاء القسم '{section_name}' بنجاح.")
        
# إنشاء زر جديد
@bot.message_handler(func=lambda message: message.text == "➕ إنشاء زر")
def create_button_start(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(types.KeyboardButton(" (رئيسي)"))

    with sqlite3.connect("bot_data.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM sections")
        sections = cursor.fetchall()
    for _, section_name in sections:
        markup.add(types.KeyboardButton(f" {section_name}"))

    bot.send_message(message.chat.id, "اختر القسم الذي تريد إنشاء الزر داخله:", reply_markup=markup)
    bot.register_next_step_handler(message, save_button_step)

def save_button_step(message):
    section_name = message.text.replace(" ", "").strip()
    section_id = None if section_name == "(رئيسي)" else get_section_id(section_name)
    
    if section_id is None and section_name != "(رئيسي)":
        bot.send_message(message.chat.id, " القسم غير موجود.")
        return

    bot.send_message(message.chat.id, "أرسل اسم الزر:")
    bot.register_next_step_handler(message, save_button_name, section_id)

def save_button_name(message, section_id):
    button_name = message.text
    bot.send_message(message.chat.id, "أرسل الملف الذي تريد ربطه بالزر (يمكنك تخطي ذلك).")
    bot.register_next_step_handler(message, save_button_file, section_id, button_name)

def save_button_file(message, section_id, button_name):
    # قائمة لتخزين مسارات الملفات المرفوعة
    file_paths = []

    # إذا كان الملف مرفقًا
    if message.document:
        file_info = bot.get_file(message.document.file_id)
        file_path = os.path.join(FILES_DIR, message.document.file_name)
        downloaded_file = bot.download_file(file_info.file_path)
        with open(file_path, "wb") as file:
            file.write(downloaded_file)
        file_paths.append((file_path, "document"))  # حفظ المسار والنوع

    # إذا كانت صورة مرفقة
    elif message.photo:
        file_info = bot.get_file(message.photo[-1].file_id)
        file_path = os.path.join(FILES_DIR, f"{button_name}.jpg")
        downloaded_file = bot.download_file(file_info.file_path)
        with open(file_path, "wb") as file:
            file.write(downloaded_file)
        file_paths.append((file_path, "image"))  # حفظ المسار والنوع

    # إذا كان الملف الصوتي مرفقًا
    elif message.audio:
        file_info = bot.get_file(message.audio.file_id)
        file_path = os.path.join(FILES_DIR, f"{button_name}.mp3")
        downloaded_file = bot.download_file(file_info.file_path)
        with open(file_path, "wb") as file:
            file.write(downloaded_file)
        file_paths.append((file_path, "audio"))  # حفظ المسار والنوع

    # إضافة النصوص كملفات أيضًا
    elif message.text:
        text_file_path = os.path.join(FILES_DIR, f"{button_name}.txt")
        with open(text_file_path, "w") as file:
            file.write(message.text)
        file_paths.append((text_file_path, "text"))  # حفظ مسار النص
    
    # إضافة الملفات إلى قاعدة البيانات
    with sqlite3.connect("bot_data.db") as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO buttons (section_id, name) VALUES (?, ?)", (section_id, button_name))
        button_id = cursor.lastrowid
        
        # إضافة الملفات المرتبطة بالزر
        for file_path, file_type in file_paths:
            cursor.execute("""
            INSERT INTO button_files (button_id, file_type, file_path)
            VALUES (?, ?, ?)
            """, (button_id, file_type, file_path))
        conn.commit()

    bot.send_message(message.chat.id, f"✅ تم إنشاء الزر: {button_name}")
    admin_controls(message)
# حذف قسم
@bot.message_handler(func=lambda message: message.text == "🗑️ حذف قسم")
def delete_section_start(message):
    with sqlite3.connect("bot_data.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sections WHERE parent_id IS NULL")
        sections = cursor.fetchall()

    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    for section in sections:
        markup.add(types.KeyboardButton(f" {section[0]}"))

    bot.send_message(message.chat.id, "اختر القسم الذي تريد حذفه:", reply_markup=markup)
    bot.register_next_step_handler(message, delete_section)

def delete_section(message):
    section_name = message.text.replace(" ", "").strip()

    with sqlite3.connect("bot_data.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM sections WHERE name = ?", (section_name,))
        section_id = cursor.fetchone()

    if section_id:
        with sqlite3.connect("bot_data.db") as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sections WHERE id = ?", (section_id[0],))
            cursor.execute("DELETE FROM buttons WHERE section_id = ?", (section_id[0],))
            conn.commit()

        bot.send_message(message.chat.id, f"✅ تم حذف القسم '{section_name}' بنجاح.")
    else:
        bot.send_message(message.chat.id, " القسم غير موجود.")
# حذف زر
@bot.message_handler(func=lambda message: message.text == "🗑️ حذف زر")
def delete_button_start(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    with sqlite3.connect("bot_data.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM buttons")
        buttons = cursor.fetchall()

    if not buttons:
        bot.send_message(message.chat.id, " لا توجد أزرار لحذفها.")
        return

    for button_name, in buttons:
        markup.add(types.KeyboardButton(f" {button_name}"))

    bot.send_message(message.chat.id, "اختر الزر الذي تريد حذفه:", reply_markup=markup)
    bot.register_next_step_handler(message, delete_button)

def delete_button(message):
    button_name = message.text.replace(" ", "").strip()
    with sqlite3.connect("bot_data.db") as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM buttons WHERE name = ?", (button_name,))
        conn.commit()

    bot.send_message(message.chat.id, f"✅ تم حذف الزر: {button_name}")
    admin_controls(message)

# تعديل محتوى زر
@bot.message_handler(func=lambda message: message.text == "✏️ تعديل محتوى زر")
def edit_button_start(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    with sqlite3.connect("bot_data.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM buttons")
        buttons = cursor.fetchall()

    if not buttons:
        bot.send_message(message.chat.id, " لا توجد أزرار لتعديلها.")
        return

    for button_name, in buttons:
        markup.add(types.KeyboardButton(f" {button_name}"))

    bot.send_message(message.chat.id, "اختر الزر الذي تريد تعديله:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_edit_button)


def handle_edit_button(message):
    button_name = message.text.replace(" ", "").strip()
    bot.send_message(
        message.chat.id,
        f"🔄 أرسل المحتوى الذي تريد إضافته للزر '{button_name}'.\n\n"
        "✅ يمكنك إرسال:\n"
        "- نصوص (سيتم حفظها كملف )\n"
        "- صور\n"
        "- فيديو\n"
        "- ملفات (PDF، Word، Excel...)\n"
        "- رسائل صوتية\n",
    )
    bot.register_next_step_handler(message, add_content_to_button, button_name)


def add_content_to_button(message, button_name):
    file_paths = []  # قائمة لتخزين الملفات المرفوعة

    # معالجة النصوص (تحويل النص إلى ملف .txt)
    if message.text:
        file_path = os.path.join(FILES_DIR, f"{button_name}.txt")
        with open(file_path, "w") as file:
            file.write(message.text)
        file_paths.append((file_path, "text"))

    # معالجة الملفات
    elif message.document:
        file_info = bot.get_file(message.document.file_id)
        file_path = os.path.join(FILES_DIR, message.document.file_name)
        downloaded_file = bot.download_file(file_info.file_path)
        with open(file_path, "wb") as file:
            file.write(downloaded_file)
        file_paths.append((file_path, "document"))

    # معالجة الصور
    elif message.photo:
        file_info = bot.get_file(message.photo[-1].file_id)
        file_path = os.path.join(FILES_DIR, f"{button_name}_image.jpg")
        downloaded_file = bot.download_file(file_info.file_path)
        with open(file_path, "wb") as file:
            file.write(downloaded_file)
        file_paths.append((file_path, "image"))

    # معالجة الفيديو
    elif message.video:
        file_info = bot.get_file(message.video.file_id)
        file_path = os.path.join(FILES_DIR, f"{button_name}_video.mp4")
        downloaded_file = bot.download_file(file_info.file_path)
        with open(file_path, "wb") as file:
            file.write(downloaded_file)
        file_paths.append((file_path, "video"))

    # معالجة الرسائل الصوتية
    elif message.voice:
        file_info = bot.get_file(message.voice.file_id)
        file_path = os.path.join(FILES_DIR, f"{button_name}_voice.ogg")
        downloaded_file = bot.download_file(file_info.file_path)
        with open(file_path, "wb") as file:
            file.write(downloaded_file)
        file_paths.append((file_path, "audio"))

    # إضافة الملفات إلى قاعدة البيانات
    with sqlite3.connect("bot_data.db") as conn:
        cursor = conn.cursor()
        for file_path, file_type in file_paths:
            cursor.execute("""
            INSERT INTO button_files (button_id, file_type, file_path)
            VALUES ((SELECT id FROM buttons WHERE name = ?), ?, ?)
            """, (button_name, file_type, file_path))
        conn.commit()

    bot.send_message(message.chat.id, f"✅ تم إضافة المحتوى للزر '{button_name}' بنجاح.")
    admin_controls(message)

# حذف محتوى زر
@bot.message_handler(func=lambda message: message.text == "🗑️ حذف محتوى زر")
def delete_button_content_start(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)

    with sqlite3.connect("bot_data.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM buttons")
        buttons = cursor.fetchall()

    if not buttons:
        bot.send_message(message.chat.id, " لا توجد أزرار لحذف محتوياتها.")
        return

    for button_name, in buttons:
        markup.add(types.KeyboardButton(f" {button_name}"))

    bot.send_message(message.chat.id, "اختر الزر الذي تريد حذف محتوياته:", reply_markup=markup)
    bot.register_next_step_handler(message, delete_button_content)


def delete_button_content(message):
    button_name = message.text.replace(" ", "").strip()

    with sqlite3.connect("bot_data.db") as conn:
        cursor = conn.cursor()

        # الحصول على معرف الزر
        cursor.execute("SELECT id FROM buttons WHERE name = ?", (button_name,))
        button = cursor.fetchone()

        if not button:
            bot.send_message(message.chat.id, " الزر غير موجود.")
            return
        
        button_id = button[0]

        # الحصول على مسارات الملفات المرتبطة بالزر
        cursor.execute("SELECT file_path FROM button_files WHERE button_id = ?", (button_id,))
        button_files = cursor.fetchall()

        cursor.execute("SELECT file_path FROM files WHERE button_id = ?", (button_id,))
        general_files = cursor.fetchall()

        # حذف الملفات الفعلية من المجلد
        for file_path, in button_files + general_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as e:
                print(f" خطأ أثناء حذف الملف {file_path}: {e}")

        # حذف الملفات المرتبطة بالزر من قاعدة البيانات
        cursor.execute("DELETE FROM button_files WHERE button_id = ?", (button_id,))
        cursor.execute("DELETE FROM files WHERE button_id = ?", (button_id,))

        # حذف النصوص المرتبطة بالزر
        cursor.execute("DELETE FROM texts WHERE button_id = ?", (button_id,))

        conn.commit()

    bot.send_message(message.chat.id, f"✅ تم حذف محتوى الزر '{button_name}' بنجاح.")
    admin_controls(message)
# إذاعة رسالة لجميع المستخدمين
@bot.message_handler(func=lambda message: message.text == "📢 إذاعة")
def broadcast_message_start(message):
    bot.send_message(message.chat.id, "أرسل الرسالة التي ترغب في إذاعتها لجميع المستخدمين.")
    bot.register_next_step_handler(message, broadcast_message)

def broadcast_message(message):
    broadcast_text = message.text
    with sqlite3.connect("bot_data.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()

    for user_id, in users:
        try:
            bot.send_message(user_id, broadcast_text)
        except Exception as e:
            print(f"خطأ في إرسال الإشعار إلى المستخدم {user_id}: {e}")

    bot.send_message(message.chat.id, "✅ تم إرسال الرسالة لجميع المستخدمين.")

# عرض عدد المستخدمين
@bot.message_handler(func=lambda message: message.text == "📊 عدد المستخدمين")
def user_count(message):
    if is_admin(message.chat.id):
        with sqlite3.connect("bot_data.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]

            cursor.execute("""
            SELECT COUNT(*) FROM users 
            WHERE join_date >= date('now', '-1 month')
            """)
            last_month_users = cursor.fetchone()[0]

            cursor.execute("""
            SELECT COUNT(*) FROM users 
            WHERE join_date >= date('now', '-1 day')
            """)
            last_day_users = cursor.fetchone()[0]

            cursor.execute("""
            SELECT COUNT(*) FROM users 
            WHERE last_active = date('now')
            """)
            active_today = cursor.fetchone()[0]

        bot.send_message(
            message.chat.id,
            f"📊 إحصائيات المستخدمين:\n"
            f"- العدد الكلي: {total_users}\n"
            f"- آخر شهر: {last_month_users}\n"
            f"- آخر 24 ساعة: {last_day_users}\n"
            f"- نشطين اليوم: {active_today}"
        )
@bot.message_handler(func=lambda message: message.text == " عرض الأقسام والأزرار")
def show_sections_and_buttons(message):
    with sqlite3.connect("bot_data.db") as conn:
        cursor = conn.cursor()

        # عرض الأقسام
        cursor.execute("SELECT id, name FROM sections WHERE parent_id IS NULL")
        sections = cursor.fetchall()

        response = " الأقسام والأزرار:\n"
        for section_id, section_name in sections:
            response += f"\n {section_name}"
            response += get_section_buttons(section_id)

        bot.send_message(message.chat.id, response)

def get_section_buttons(section_id, level=1):
    with sqlite3.connect("bot_data.db") as conn:
        cursor = conn.cursor()

        # عرض الأزرار
        cursor.execute("SELECT name FROM buttons WHERE section_id = ?", (section_id,))
        buttons = cursor.fetchall()
        buttons_list = "".join(f"\n{'  ' * level} {button_name}" for button_name, in buttons)

        # عرض الأقسام الفرعية
        cursor.execute("SELECT id, name FROM sections WHERE parent_id = ?", (section_id,))
        subsections = cursor.fetchall()
        subsections_list = "".join(
            f"\n{'  ' * level} {subsection_name}" + get_section_buttons(subsection_id, level + 1)
            for subsection_id, subsection_name in subsections
        )

        return buttons_list + subsections_list    
# ادمن
@bot.message_handler(func=lambda message: message.text == "➕ إضافة أدمن")
def add_admin_start(message):
    if not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية لإضافة أدمن.")
        return

    bot.send_message(message.chat.id, "📩 أرسل معرف المستخدم (User ID) للشخص الذي تريد إضافته كأدمن.")
    bot.register_next_step_handler(message, save_admin)

def save_admin(message):
    try:
        new_admin_id = int(message.text)  # التأكد من أن الإدخال رقم
        if new_admin_id in ADMINS:
            bot.send_message(message.chat.id, f"⚠️ المستخدم {new_admin_id} هو بالفعل أدمن.")
            return

        ADMINS.append(new_admin_id)  # إضافة المعرف إلى القائمة
        bot.send_message(message.chat.id, f"✅ تم إضافة المستخدم {new_admin_id} كأدمن جديد.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ يجب إدخال رقم معرف صحيح.")
        
# دفر ادمن
@bot.message_handler(func=lambda message: message.text == "🗑️ حذف أدمن")
def remove_admin_start(message):
    if not is_admin(message.chat.id):
        bot.send_message(message.chat.id, "❌ ليس لديك صلاحية لحذف أدمن.")
        return

    bot.send_message(message.chat.id, "📩 أرسل معرف المستخدم (User ID) الذي تريد حذفه من قائمة الأدمن.")
    bot.register_next_step_handler(message, remove_admin)

def remove_admin(message):
    try:
        admin_id_to_remove = int(message.text)  # التأكد من أن الإدخال رقم
        if admin_id_to_remove not in ADMINS:
            bot.send_message(message.chat.id, f"⚠️ المستخدم {admin_id_to_remove} ليس موجودًا كأدمن.")
            return

        if admin_id_to_remove == ADMIN_ID:
            bot.send_message(message.chat.id, "❌ لا يمكن حذف الأدمن الأساسي.")
            return

        ADMINS.remove(admin_id_to_remove)  # إزالة المعرف من القائمة
        bot.send_message(message.chat.id, f"✅ تم حذف المستخدم {admin_id_to_remove} من قائمة الأدمن.")
    except ValueError:
        bot.send_message(message.chat.id, "❌ يجب إدخال رقم معرف صحيح.")        
# بدء البوت
bot.polling(none_stop=True)

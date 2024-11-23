import os
from telethon import TelegramClient, events, Button
import re

# الحصول على بيانات API من المتغيرات البيئية
api_id = os.environ.get('API_ID')
api_hash = os.environ.get('API_HASH')
bot_token = os.environ.get('BOT_TOKEN')

# تهيئة العميل (Client)
client = TelegramClient('bot', api_id, api_hash).start(bot_token=bot_token)

# نمط (Regex) لاستخراج معلومات القناة ومعرف الرسالة من الروابط
link_pattern = re.compile(r'https://t\.me/(?P<channel>\w+)/(?P<message_id>\d+)')

# اسم القناة المطلوبة للاشتراك الإجباري
required_channel = 'ir6qe'  # بدون @ أو https://t.me/

# دالة للتحقق من اشتراك المستخدم في القناة باستخدام get_participants
async def is_subscribed(user_id):
    try:
        # الحصول على قائمة المشاركين في القناة
        participants = await client.get_participants(required_channel)
        
        # التحقق مما إذا كان المستخدم موجودًا في قائمة المشاركين
        for participant in participants:
            if participant.id == user_id:
                return True
        return False
    except Exception as e:
        print(f"Error checking subscription: {e}")
        return False

# دالة لمعالجة الأمر /start
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    sender = await event.get_sender()

    # التحقق من اشتراك المستخدم
    if await is_subscribed(sender.id):
        await event.reply(f"مرحبًا {sender.first_name}!\nأرسل لي رابط المنشور الذي تريد سحبه من القناة، وسأقوم بمعالجته لك.")
    else:
        # إرسال رسالة مع زر "تحقق من الاشتراك"
        await event.reply(
            f"مرحبًا {sender.first_name}!\nيرجى الاشتراك في القناة التالية لاستخدام البوت: https://t.me/{required_channel}",
            buttons=[Button.inline("تحقق من الاشتراك", b'check_subscription')]
        )

# دالة للتعامل مع زر "تحقق من الاشتراك"
@client.on(events.CallbackQuery(data=b'check_subscription'))
async def check_subscription(event):
    sender = await event.get_sender()

    # التحقق من اشتراك المستخدم
    if await is_subscribed(sender.id):
        await event.edit(f"شكرًا لاشتراكك! الآن يمكنك استخدام البوت.")
    else:
        await event.edit(f"لم تقم بالاشتراك بعد. يرجى الاشتراك في القناة: https://t.me/{required_channel}")

# دالة لمعالجة الرسائل التي تحتوي على روابط فقط
@client.on(events.NewMessage)
async def handle_message(event):
    sender = await event.get_sender()

    # تجاهل الرد على الرسائل التي أرسلها البوت نفسه
    if event.out:
        return
    
    # تجاهل الأمر '/start' لتجنب تكرار معالجته
    if event.message.message.startswith('/start'):
        return

    # التحقق من اشتراك المستخدم فقط إذا كانت الرسالة تحتوي على رابط
    if not await is_subscribed(sender.id):
        await event.reply(f"يرجى الاشتراك في القناة التالية لاستخدام البوت: https://t.me/{required_channel}",
                          buttons=[Button.inline("تحقق من الاشتراك", b'check_subscription')])
        return

    message = event.message.message

    # التحقق من وجود رابط تليجرام في الرسالة
    match = link_pattern.search(message)
    if match:
        channel = match.group('channel')
        message_id = int(match.group('message_id'))

        await event.reply(f"تم استلام الرابط من القناة: {channel}، معرف الرسالة: {message_id}. جاري معالجة المحتوى...")
        
        # سحب المحتوى من القناة
        await fetch_content(event.sender_id, channel, message_id)
    else:
        # تجاهل الرد على الرسائل التي لا تحتوي على رابط
        return

# دالة لسحب المحتوى من القناة
async def fetch_content(user_id, channel, message_id):
    try:
        message = await client.get_messages(channel, ids=message_id)

        if message:
            # إعداد نص الرسالة للإرسال
            response_text = ""
            if message.text:
                response_text += f"نص الرسالة: {message.text}\n"

            # تحقق من وجود وسائط
            if message.media:
                # إضافة نص لإعلام المستخدم بالوسائط
                response_text += "\n @ir6qe تم السحب بواسطة \n"
                await client.send_file(user_id, message.media)

            # إرسال النص إذا كان موجودًا
            if response_text:
                await client.send_message(user_id, response_text)
        else:
            await client.send_message(user_id, "لم يتم العثور على المحتوى المطلوب.")
    except Exception as e:
        await client.send_message(user_id, f"حدث خطأ أثناء سحب المحتوى: {str(e)}")

# تشغيل البوت
client.start()
print("Bot is running...")
client.run_until_disconnected()

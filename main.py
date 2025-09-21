import os
import asyncio
from telethon import TelegramClient, events, Button, functions, types
from telethon.sessions import StringSession

# ---------- إعدادات عامة ----------
api_id = int(os.environ.get("API_ID", "123456"))
api_hash = os.environ.get("API_HASH", "YOUR_API_HASH")
bot_token = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")

# قناة الاشتراك الإجباري
force_channel = os.environ.get("FORCE_CHANNEL", "Qd3Qd")  # بدون @
# حساب المطور
developer_username = os.environ.get("DEVELOPER_USERNAME", "E2E12")  # بدون @

# بوت التحكم
bot = TelegramClient("bot", api_id, api_hash).start(bot_token=bot_token)

# نخزن حالة المستخدمين
sessions = {}


# ---------- فحص الاشتراك ----------
async def is_subscribed(user_id):
    try:
        result = await bot(functions.channels.GetParticipantRequest(
            channel=force_channel,
            participant=user_id
        ))
        return True if result else False
    except:
        return False


# ---------- الأوامر ----------
@bot.on(events.NewMessage(pattern="/start"))
async def start_handler(event):
    buttons = [
        [Button.inline("➕ إنشاء مجموعات", data="create_groups")],
        [Button.url("👨‍💻 المطور", f"https://t.me/{developer_username}")]
    ]
    text = "👋 أهلاً بك!\n\nفي بوت صنـع كروبات، للتجار."
    await event.respond(text, buttons=buttons)


# ---------- زر إنشاء مجموعات ----------
@bot.on(events.CallbackQuery(data=b"create_groups"))
async def callback_create_groups(event):
    user_id = event.sender_id
    # فحص الاشتراك
    if not await is_subscribed(user_id):
        await event.answe ("اشترك حبيبي وأسرل /start !", alert=True)
        return
    sessions[user_id] = {"step": "phone"}
    await event.respond("📞 أرسل رقم هاتفك (بصيغة +964...)")


# ---------- استقبال رقم الهاتف أو الكود ----------
@bot.on(events.NewMessage)
async def handle_messages(event):
    user_id = event.sender_id
    if user_id not in sessions:
        return

    step = sessions[user_id].get("step")

    # --- الخطوة الأولى: الرقم ---
    if step == "phone":
        phone = event.raw_text.strip()
        client = TelegramClient(StringSession(), api_id, api_hash)
        await client.connect()
        try:
            await client.send_code_request(phone)
            sessions[user_id] = {"step": "code", "phone": phone, "client": client}
            await event.respond("📩 أرسل رمز التأكيد اللي وصلك.")
        except Exception as e:
            await event.respond(f"❌ خطأ: {e}")

    # --- الخطوة الثانية: الكود ---
    elif step == "code":
        code = event.raw_text.strip()
        client = sessions[user_id]["client"]
        phone = sessions[user_id]["phone"]
        try:
            await client.sign_in(phone, code)
            session_string = client.session.save()
            # هنا ممكن تخزن session_string بقاعدة بيانات أو ملف
            await event.respond("✅ تم تسجيل الدخول بنجاح! الآن يمكنني إنشاء المجموعات.")
            sessions[user_id] = {"step": "done", "session": session_string}
        except Exception as e:
            await event.respond(f"❌ رمز غير صحيح أو خطأ: {e}")


# ---------- تشغيل البوت ----------
print("🤖 Bot is running...")
bot.run_until_disconnected()

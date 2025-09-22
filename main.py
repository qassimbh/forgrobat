import os
import asyncio
from telethon import TelegramClient, events, Button, functions, types
from telethon.sessions import StringSession

# ---------- إعدادات ----------
api_id = int(os.environ.get("API_ID"))
api_hash = os.environ.get("API_HASH")
bot_token = os.environ.get("BOT_TOKEN")
force_channel = os.environ.get("FORCE_CHANNEL")  # بدون @
developer_username = os.environ.get("DEVELOPER_USERNAME")  # بدون @
admin_bot_username = os.environ.get("ADMIN_BOT_USERNAME", "czbbbot")

groups_per_user = int(os.environ.get("GROUPS_PER_USER", 2))
delay_between_groups = int(os.environ.get("DELAY_BETWEEN_GROUPS", 5))

# جلسة المستخدم (انت اللي مسجلها مسبقًا)
user_session_string = os.environ.get("SESSION_STRING")

bot = TelegramClient("bot", api_id, api_hash).start(bot_token=bot_token)
user_client = TelegramClient(StringSession(user_session_string), api_id, api_hash)

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
async def create_supergroup(title="AutoGroup"):
    try:
        result = await user_client(functions.channels.CreateChannelRequest(
            title=title,
            about="تم الإنشاء بواسطة البوت",
            megagroup=True
        ))
        return result.chats[0]
    except Exception as e:
        print(f"[FAILED] لم يتم إنشاء المجموعة: {e}")
        return None

# ---------- إضافة البوت كمشرف ----------
async def invite_admin_bot(channel):
    try:
        bot_entity = await user_client.get_entity(f"@{admin_bot_username}")
        await user_client(functions.channels.InviteToChannelRequest(
            channel=channel,
            users=[bot_entity]
        ))
        rights = types.ChannelAdminRights(
            change_info=True, post_messages=True, edit_messages=True,
            delete_messages=True, ban_users=True, invite_users=True,
            pin_messages=True, add_admins=False
        )
        await user_client(functions.channels.EditAdminRequest(
            channel=channel,
            user_id=bot_entity,
            admin_rights=rights,
            rank="Moderator"
        ))
    except Exception as e:
        print(f"[FAILED] ترقية البوت: {e}")

# ---------- إرسال الرسائل داخل كل مجموعة ----------
messages_to_send = [
    "هلوو",
    "شلونكم",
    "شني @e2e12",
    "يلاا",
    "ميخالف"
]

async def send_messages(channel):
    for msg in messages_to_send:
        try:
            await user_client.send_message(channel, msg)
            await asyncio.sleep(1)
        except Exception as e:
            print(f"[FAILED] إرسال {msg}: {e}")

# ---------- /start ----------
@bot.on(events.NewMessage(pattern="/start"))
async def start_handler(event):
    user_id = event.sender_id

    # فحص الاشتراك
    if not await is_subscribed(user_id):
        await event.respond(
            f"اشترك :\n\n👉 https://t.me/{force_channel}\n\nبعدها أرسل /start ."
        )
        return

    # لو مشترك فعلاً → عرض الأزرار
    buttons = [
        [Button.inline("➕💎 إنشاء مجموعات", data="create_groups")],
        [Button.url("👨‍💻 Div", f"https://t.me/{developer_username}")]
    ]
    await event.respond("👋 أهلاً بك!\n\nاختر ما تريد:", buttons=buttons)

# ---------- زر إنشاء مجموعات ----------
@bot.on(events.CallbackQuery(data=b"create_groups"))
async def callback_create_groups(event):
    success_count = 0
    for i in range(groups_per_user):
        title = f"AutoGroup_{event.sender_id}_{i}"
        group = await create_supergroup(title)
        if group:
            success_count += 1
            await invite_admin_bot(group)
            await send_messages(group)
        await asyncio.sleep(delay_between_groups)

    await event.respond(f"😂✅ تم إنشاء {success_count} مجموعة بنجاح!")

print("🤖 Bot is running...")
bot.run_until_disconnected()

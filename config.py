import os

# 🔑 Bot token
BOT_TOKEN = os.getenv("BOT_TOKEN")

# 🗄️ Postgres database URL
DATABASE_URL = os.getenv("DATABASE_URL")

# 👑 Super admin ID
SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", "123456789"))

# 🤖 Bot nomi
BOT_NAME = os.getenv("BOT_NAME", "Kinolar")

# 🌐 Webhook URL
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# 🚪 Port
PORT = int(os.getenv("PORT", "10000"))

# 📦 Storage turi
STORAGE_TYPE = "telegram"

# 🎬 Kino kanali
MOVIES_CHANNEL_ID = os.getenv("MOVIES_CHANNEL_ID")

# 💳 To‘lov ma’lumotlari
PAYMENT_CARD = os.getenv("PAYMENT_CARD", "")
PAYMENT_OWNER = os.getenv("PAYMENT_OWNER", "")

# 🛟 Support username
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "")

# 🔒 Content himoya
PROTECT_CONTENT_DEFAULT = os.getenv("PROTECT_CONTENT_DEFAULT", "0") == "1"

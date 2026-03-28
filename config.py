import os

# 🔑 Bot token
BOT_TOKEN = os.getenv("BOT_TOKEN")

# 👑 Super admin ID
SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", "123456789"))

# 🤖 Bot nomi
BOT_NAME = os.getenv("BOT_NAME", "Kinolar")

# 💾 Database (SQLite)
DB_PATH = os.getenv("DB_PATH", "kinobot.db")

# 🌐 Webhook URL (Render link)
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# 🚪 Port (Render avtomatik beradi)
PORT = int(os.getenv("PORT", "10000"))

# 📦 Storage turi (o‘zgarmaydi)
STORAGE_TYPE = "telegram"

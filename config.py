import os

BOT_TOKEN = os.getenv('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
SUPER_ADMIN_ID = int(os.getenv('SUPER_ADMIN_ID', '123456789'))
STORAGE_TYPE = 'telegram'
BOT_NAME = os.getenv('BOT_NAME', 'Kinolar')
DB_PATH = os.getenv('DB_PATH', 'kinobot.db')

import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from database import init_db
from handlers import start_handler, button_handler, message_handler
from config import BOT_TOKEN

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def post_init(app: Application):
    await init_db()
    logger.info('✅ Database tayyor!')


def main():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler('start', start_handler))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, message_handler))
    logger.info('🚀 Bot ishga tushdi...')
    app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    main()

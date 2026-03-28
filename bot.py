import logging
import os
from aiohttp import web

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from database import init_db
from handlers import start_handler, button_handler, message_handler
from config import BOT_TOKEN, WEBHOOK_URL, PORT


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def post_init(app: Application) -> None:
    await init_db()
    await app.bot.set_webhook(url=WEBHOOK_URL)
    logger.info("✅ Database tayyor!")
    logger.info(f"✅ Webhook o'rnatildi: {WEBHOOK_URL}")


async def healthcheck(request: web.Request) -> web.Response:
    return web.Response(text="Bot ishlayapti ✅")


async def telegram_webhook(request: web.Request) -> web.Response:
    app = request.app["ptb_app"]

    try:
        data = await request.json()
        update = Update.de_json(data, app.bot)
        await app.process_update(update)
        return web.Response(text="OK")
    except Exception as e:
        logger.exception(f"Webhook xatolik: {e}")
        return web.Response(text="ERROR", status=500)


async def on_startup(web_app: web.Application) -> None:
    app: Application = web_app["ptb_app"]

    await app.initialize()
    await post_init(app)
    await app.start()

    logger.info("🚀 Bot webhook rejimida ishga tushdi...")


async def on_cleanup(web_app: web.Application) -> None:
    app: Application = web_app["ptb_app"]

    await app.stop()
    await app.shutdown()

    logger.info("🛑 Bot to'xtatildi.")


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, message_handler))

    web_app = web.Application()
    web_app["ptb_app"] = app

    web_app.router.add_get("/", healthcheck)
    web_app.router.add_post("/", telegram_webhook)

    web_app.on_startup.append(on_startup)
    web_app.on_cleanup.append(on_cleanup)

    logger.info(f"🌐 Server portda ishga tushmoqda: {PORT}")
    web.run_app(web_app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()

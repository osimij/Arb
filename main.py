import logging
from telegram import BotCommand, BotCommandScopeChat
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)
from threading import Thread

import config
import database as db
from handlers import (
    start,
    handle_text,
    add_manager_command,
    delete_manager_command,
    list_managers_command,
)
from keep_alive import keep_alive, ping_self

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """
    Post-initialization function to set bot commands.
    """
    # Commands for regular users
    user_commands = [
        BotCommand("start", "Запустить/перезапустить бота"),
    ]
    await application.bot.set_my_commands(user_commands)

    # Commands for the admin
    admin_commands = [
        BotCommand("start", "Запустить/перезапустить бота"),
        BotCommand("addmanager", "Добавить менеджера"),
        BotCommand("delmanager", "Удалить менеджера"),
        BotCommand("listmanagers", "Показать список менеджеров"),
    ]
    await application.bot.set_my_commands(
        admin_commands, scope=BotCommandScopeChat(chat_id=config.ADMIN_ID)
    )


def main() -> None:
    """Run the bot."""
    # Start the keep-alive server
    keep_alive()
    
    # Start the self-pinging thread
    ping_thread = Thread(target=ping_self)
    ping_thread.daemon = True
    ping_thread.start()
    
    # Initialize the database
    db.init_db()

    # Create the Application and pass it your bot's token.
    application = (
        Application.builder()
        .token(config.TOKEN)
        .connect_timeout(10)
        .read_timeout(10)
        .http_version("1.1")
        .get_updates_http_version("1.1")
        .post_init(post_init)
        .build()
    )

    # --- Register Handlers ---
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addmanager", add_manager_command))
    application.add_handler(CommandHandler("delmanager", delete_manager_command))
    application.add_handler(CommandHandler("listmanagers", list_managers_command))

    # Text handler for reply keyboard
    application.add_handler(
        MessageHandler(
            filters.Regex(r'^(Пополнить игровой баланс|Вывод|Поддержка 24/7|Новостной канал)$'),
            handle_text,
        )
    )

    # --- Start the Bot ---
    logger.info("Starting bot...")
    application.run_polling()


if __name__ == "__main__":
    main() 
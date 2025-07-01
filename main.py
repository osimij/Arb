import logging
from telegram import BotCommand, BotCommandScopeChat
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
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
    receive_manager_username,
    delete_manager_command,
    receive_delete_username,
    cancel_conversation,
    list_managers_command,
    deposit_command,
    withdrawal_command,
    add_manager_api_key,
    list_api_keys_command,
    WAITING_FOR_MANAGER_USERNAME,
    WAITING_FOR_DELETE_USERNAME,
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

    # Commands for the admins
    admin_commands = [
        BotCommand("start", "Запустить/перезапустить бота"),
        BotCommand("addmanager", "Добавить менеджера"),
        BotCommand("delmanager", "Удалить менеджера"),
        BotCommand("listmanagers", "Показать список менеджеров"),
        BotCommand("addkey", "Добавить API ключ менеджеру"),
        BotCommand("listkeys", "Показать менеджеров с API ключами"),
    ]
    # Set commands for all admins
    for admin_id in config.ADMIN_IDS:
        try:
            await application.bot.set_my_commands(
                admin_commands, scope=BotCommandScopeChat(chat_id=admin_id)
            )
        except Exception as e:
            logger.error(f"Could not set commands for admin {admin_id}: {e}")
    
    # Set manager commands for all managers
    managers = db.get_all_managers()
    manager_commands = [
        BotCommand("start", "Запустить/перезапустить бота"),
        BotCommand("deposit", "Создать депозит для пользователя"),
        BotCommand("withdrawal", "Обработать вывод для пользователя"),
    ]
    
    for manager_username in managers:
        try:
            # Get manager's user ID (this would need to be stored or retrieved)
            # For now, we'll skip setting commands for managers via user ID
            # since we don't have their Telegram user IDs stored
            pass
        except Exception as e:
            logger.error(f"Could not set commands for manager {manager_username}: {e}")


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
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .http_version("1.1")
        .get_updates_http_version("1.1")
        .post_init(post_init)
        .build()
    )

    # --- Register Handlers ---
    # Create a filter for the admins
    admin_filter = filters.User(user_id=config.ADMIN_IDS)

    # Conversation handler for adding and deleting managers
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("addmanager", add_manager_command, filters=admin_filter),
            CommandHandler("delmanager", delete_manager_command, filters=admin_filter),
        ],
        states={
            WAITING_FOR_MANAGER_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & admin_filter, receive_manager_username)
            ],
            WAITING_FOR_DELETE_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & admin_filter, receive_delete_username)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation, filters=admin_filter)],
        conversation_timeout=300,  # 5 minutes timeout
    )

    application.add_handler(conv_handler)
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("listmanagers", list_managers_command, filters=admin_filter))
    application.add_handler(CommandHandler("addkey", add_manager_api_key, filters=admin_filter))
    application.add_handler(CommandHandler("listkeys", list_api_keys_command, filters=admin_filter))
    
    # Manager command handlers (available to all users, but internally filtered)
    application.add_handler(CommandHandler("deposit", deposit_command))
    application.add_handler(CommandHandler("withdrawal", withdrawal_command))
    
    # Text handler for all other text messages (including reply keyboard)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # --- Start the Bot ---
    logger.info("Starting bot...")
    application.run_polling()


if __name__ == "__main__":
    main() 
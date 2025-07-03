from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
import database as db
from config import ADMIN_IDS, API_KEY
from api_client import WinAPIClient
import logging

logger = logging.getLogger(__name__)

# Conversation states
WAITING_FOR_MANAGER_USERNAME = 1
WAITING_FOR_DELETE_USERNAME = 2
WAITING_FOR_MANAGER_MESSAGE = 3

# --- Main Keyboard ---
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("Пополнить игровой баланс"), KeyboardButton("Вывод")],
        [KeyboardButton("Поддержка 24/7"), KeyboardButton("Новостной канал")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# --- User Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 Добро пожаловать в официальный бот нашей кассы 1win!\n\n"
        "Здесь вы можете:\n"
        "✅ Пополнить игровой счёт без задержек\n"
        "✅ Получить бонусы при пополнении\n"
        "✅ Быстро выводить средства\n"
        "✅ Следить за новостями и акциями\n\n"
        "💬 Мы работаем 24/7 — всегда на связи!\n"
        "🎁 Бонус при первом пополнении уже ждёт вас!\n\n"
    )
    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard())

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles text messages from the reply keyboard."""
    text = update.message.text

    if text in ["Пополнить игровой баланс", "Вывод"]:
        manager = db.get_next_manager()
        if manager:
            manager_url = f"https://t.me/{manager}"
            inline_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(text="Связаться с менеджером", url=manager_url)]
            ])
            await update.message.reply_text(
                text="Перенаправляю вас к менеджеру.",
                reply_markup=inline_keyboard,
            )
        else:
            await update.message.reply_text(
                text="К сожалению, в данный момент нет доступных менеджеров. Пожалуйста, попробуйте позже.",
            )
    elif text == "Поддержка 24/7":
        # You can replace this with your actual support username
        support_url = "https://t.me/your_support_username"
        await update.message.reply_text(
            f"Для поддержки, пожалуйста, свяжитесь с нами: {support_url}"
        )
    elif text == "Новостной канал":
        news_channel_url = "https://t.me/gpkassa1win_tj"
        await update.message.reply_text(
            f"📢 Наш новостной канал: {news_channel_url}"
        )

# This handler is no longer used by the main keyboard but might be used elsewhere.
# If not, it can be removed. For now, I'll leave it but its logic is replaced by handle_text
async def handle_button_press(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # It's good practice to answer all callbacks
    # The old logic is now in handle_text
    await query.edit_message_text(text="This action is now handled by the main keyboard buttons.")

# --- Admin Handlers ---
def is_admin(update: Update) -> bool:
    """Check if the user sending the command is an admin."""
    return update.effective_user.id in ADMIN_IDS

async def add_manager_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("У вас нет прав для выполнения этой команды.")
        return ConversationHandler.END

    await update.message.reply_text("📝 Пожалуйста, отправьте имя пользователя менеджера (с @ или без):")
    return WAITING_FOR_MANAGER_USERNAME

async def receive_manager_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip()
    if username.startswith('@'):
        username = username[1:]

    # Store the username temporarily
    context.user_data['pending_manager_username'] = username
    
    # Check if manager already exists
    if username in db.get_all_managers():
        await update.message.reply_text(
            f"⚠️ Менеджер @{username} уже существует в списке.\n\n"
            "Пожалуйста, введите другое имя пользователя или используйте /cancel для отмены."
        )
        return WAITING_FOR_MANAGER_USERNAME
    
    await update.message.reply_text(
        f"📝 Теперь попросите менеджера @{username} отправить любое сообщение в этот бот.\n\n"
        f"⚠️ Важно: менеджер должен написать боту СЕЙЧАС, чтобы я мог получить его ID и настроить команды.\n\n"
        f"После того как @{username} напишет боту, я автоматически добавлю его в список менеджеров."
    )
    return WAITING_FOR_MANAGER_MESSAGE

async def receive_manager_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wait for the manager to send a message to capture their user ID."""
    manager_user_id = update.effective_user.id
    manager_username = update.effective_user.username
    pending_username = context.user_data.get('pending_manager_username')
    
    if not manager_username:
        await update.message.reply_text(
            "❌ У вас должен быть установлен username в Telegram.\n"
            "Пожалуйста, установите username и попробуйте снова."
        )
        return WAITING_FOR_MANAGER_MESSAGE
    
    # Remove @ if present
    if manager_username.startswith('@'):
        manager_username = manager_username[1:]
    
    # Check if this is the expected manager
    if manager_username.lower() != pending_username.lower():
        await update.message.reply_text(
            f"❌ Ожидался менеджер @{pending_username}, но сообщение пришло от @{manager_username}.\n\n"
            f"Попросите @{pending_username} отправить сообщение в бот."
        )
        return WAITING_FOR_MANAGER_MESSAGE
    
    # Add manager with user ID
    if db.add_manager(manager_username, manager_user_id):
        # Set commands for this manager
        try:
            from telegram import BotCommand, BotCommandScopeChat
            manager_commands = [
                BotCommand("start", "Запустить/перезапустить бота"),
                BotCommand("deposit", "Создать депозит для пользователя"),
                BotCommand("withdrawal", "Обработать вывод для пользователя"),
            ]
            await context.bot.set_my_commands(
                manager_commands, 
                scope=BotCommandScopeChat(chat_id=manager_user_id)
            )
            
            await update.message.reply_text(
                f"✅ Добро пожаловать, @{manager_username}!\n\n"
                f"Вы успешно добавлены как менеджер. Теперь у вас есть доступ к командам:\n"
                f"• /deposit - создать депозит\n"
                f"• /withdrawal - обработать вывод\n\n"
                f"Команды появятся в вашем меню команд."
            )
            
            # Notify the admin who added the manager
            for admin_id in ADMIN_IDS:
                try:
                    await context.bot.send_message(
                        chat_id=admin_id,
                        text=f"✅ Менеджер @{manager_username} (ID: {manager_user_id}) успешно добавлен и команды настроены!"
                    )
                except:
                    pass  # Admin might have blocked the bot
            
            return ConversationHandler.END
            
        except Exception as e:
            logger.error(f"Error setting commands for manager {manager_username}: {e}")
            await update.message.reply_text(
                f"✅ Менеджер @{manager_username} добавлен, но произошла ошибка при настройке команд.\n"
                f"Обратитесь к администратору."
            )
            return ConversationHandler.END
    else:
        await update.message.reply_text(
            f"❌ Ошибка при добавлении менеджера @{manager_username}.\n"
            f"Возможно, он уже существует в списке."
        )
        return ConversationHandler.END

async def delete_manager_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("У вас нет прав для выполнения этой команды.")
        return ConversationHandler.END

    await update.message.reply_text("🗑️ Пожалуйста, отправьте имя пользователя менеджера для удаления (с @ или без):")
    return WAITING_FOR_DELETE_USERNAME

async def receive_delete_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip()
    if username.startswith('@'):
        username = username[1:]

    if db.delete_manager(username):
        await update.message.reply_text(f"🗑️ Менеджер @{username} успешно удален.")
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            f"⚠️ Менеджер @{username} не найден в списке.\n\n"
            "Пожалуйста, введите другое имя пользователя или используйте /cancel для отмены."
        )
        return WAITING_FOR_DELETE_USERNAME

async def migrate_manager_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allow existing managers to register their user ID"""
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    if not username:
        await update.message.reply_text(
            "❌ У вас должен быть установлен username в Telegram для использования команд менеджера."
        )
        return
    
    # Remove @ if present
    if username.startswith('@'):
        username = username[1:]
    
    # Check if this username exists in managers but without user_id
    all_managers = db.get_all_managers()
    managers_with_ids = [m[0] for m in db.get_all_managers_with_ids()]
    
    if username in all_managers and username not in managers_with_ids:
        # Update the manager with user_id
        if db.update_manager_user_id(username, user_id):
            # Set commands for this manager
            try:
                from telegram import BotCommand, BotCommandScopeChat
                manager_commands = [
                    BotCommand("start", "Запустить/перезапустить бота"),
                    BotCommand("deposit", "Создать депозит для пользователя"),
                    BotCommand("withdrawal", "Обработать вывод для пользователя"),
                ]
                await context.bot.set_my_commands(
                    manager_commands, 
                    scope=BotCommandScopeChat(chat_id=user_id)
                )
                
                await update.message.reply_text(
                    f"✅ Добро пожаловать, @{username}!\n\n"
                    f"Ваш аккаунт менеджера успешно активирован. Теперь у вас есть доступ к командам:\n"
                    f"• /deposit - создать депозит\n"
                    f"• /withdrawal - обработать вывод\n\n"
                    f"Команды появятся в вашем меню команд."
                )
                
                # Notify admins
                for admin_id in ADMIN_IDS:
                    try:
                        await context.bot.send_message(
                            chat_id=admin_id,
                            text=f"✅ Менеджер @{username} (ID: {user_id}) активировал свой аккаунт!"
                        )
                    except:
                        pass
            except Exception as e:
                logger.error(f"Error setting commands for manager {username}: {e}")
                await update.message.reply_text(
                    f"✅ Ваш аккаунт активирован, но произошла ошибка при настройке команд.\n"
                    f"Обратитесь к администратору."
                )
        else:
            await update.message.reply_text("❌ Ошибка при активации аккаунта.")
    elif username in managers_with_ids:
        await update.message.reply_text("✅ Ваш аккаунт менеджера уже активирован!")
    else:
        await update.message.reply_text(
            f"❌ Пользователь @{username} не найден в списке менеджеров.\n"
            f"Обратитесь к администратору для добавления в список."
        )

async def list_managers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("У вас нет прав для выполнения этой команды.")
        return

    managers = db.get_all_managers()
    if not managers:
        await update.message.reply_text("Список менеджеров пуст.")
        return

    message_text = "*Список текущих менеджеров:*\n\n"
    message_text += "\n".join([f"• `@{manager}`" for manager in managers])

    await update.message.reply_text(message_text, parse_mode=ParseMode.MARKDOWN_V2)

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Операция отменена.")
    return ConversationHandler.END


# --- Manager API Commands ---
def is_manager(username: str = None, user_id: int = None) -> bool:
    """Check if the user is a manager by username or user_id."""
    if user_id:
        # Check by user_id first (more reliable)
        return db.is_manager_by_user_id(user_id) is not None
    elif username:
        # Fallback to username check
        managers = db.get_all_managers()
        return username in managers
    return False


async def deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /deposit command for managers."""
    username = update.effective_user.username
    user_id_telegram = update.effective_user.id
    
    # Log the command attempt
    logger.info(f"Deposit command attempted by user: {username} (ID: {user_id_telegram})")
    
    if not username:
        await update.message.reply_text("❌ У вас должен быть установлен username в Telegram для использования этой команды.")
        return
    
    if not is_manager(username=username, user_id=user_id_telegram):
        managers_list = db.get_all_managers()
        logger.warning(f"User {username} (ID: {user_id_telegram}) not found in managers list. Current managers: {managers_list}")
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды. Обратитесь к администратору для добавления в список менеджеров.")
        return
    
    if len(context.args) != 2:
        await update.message.reply_text(
            "❌ Неверный формат команды.\n\n"
            "Использование: `/deposit <user_id> <amount>`\n"
            "Пример: `/deposit 123456 1000`\n\n"
            "user_id - ID пользователя в системе 1win\n"
            "amount - сумма депозита",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        user_id = int(context.args[0])
        amount = float(context.args[1])
        
        if amount <= 0:
            await update.message.reply_text("❌ Сумма должна быть больше 0.")
            return
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат данных. ID пользователя должен быть числом, сумма - числом.")
        return
    
    # Show processing message
    processing_msg = await update.message.reply_text("⏳ Обрабатываю депозит...")
    
    # Log the API call attempt
    logger.info(f"Making API call for deposit: user_id={user_id}, amount={amount}, api_key={'*' * 10 + API_KEY[-10:] if API_KEY else 'NOT_SET'}")
    
    # Make API call
    try:
        client = WinAPIClient(API_KEY)
        result = await client.create_deposit(user_id, amount)
        
        # Update message with result
        await processing_msg.edit_text(result["message"])
        
        # Log the transaction
        logger.info(f"Deposit request by {username}: user_id={user_id}, amount={amount}, success={result['success']}")
        
    except Exception as e:
        logger.error(f"Error in deposit command: {e}")
        await processing_msg.edit_text(f"❌ Произошла ошибка при обработке депозита: {str(e)}")


async def withdrawal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /withdrawal command for managers."""
    username = update.effective_user.username
    user_id_telegram = update.effective_user.id
    
    # Log the command attempt
    logger.info(f"Withdrawal command attempted by user: {username} (ID: {user_id_telegram})")
    
    if not username:
        await update.message.reply_text("❌ У вас должен быть установлен username в Telegram для использования этой команды.")
        return
    
    if not is_manager(username=username, user_id=user_id_telegram):
        managers_list = db.get_all_managers()
        logger.warning(f"User {username} (ID: {user_id_telegram}) not found in managers list. Current managers: {managers_list}")
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды. Обратитесь к администратору для добавления в список менеджеров.")
        return
    
    if len(context.args) != 2:
        await update.message.reply_text(
            "❌ Неверный формат команды.\n\n"
            "Использование: `/withdrawal <user_id> <code>`\n"
            "Пример: `/withdrawal 123456 1234`\n\n"
            "user_id - ID пользователя в системе 1win\n"
            "code - код подтверждения от пользователя",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        user_id = int(context.args[0])
        code = int(context.args[1])
        
        if code < 0:
            await update.message.reply_text("❌ Код должен быть положительным числом.")
            return
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат данных. ID пользователя и код должны быть числами.")
        return
    
    # Show processing message
    processing_msg = await update.message.reply_text("⏳ Обрабатываю вывод...")
    
    # Log the API call attempt
    logger.info(f"Making API call for withdrawal: user_id={user_id}, code={code}, api_key={'*' * 10 + API_KEY[-10:] if API_KEY else 'NOT_SET'}")
    
    # Make API call
    try:
        client = WinAPIClient(API_KEY)
        result = await client.process_withdrawal(user_id, code)
        
        # Update message with result
        await processing_msg.edit_text(result["message"])
        
        # Log the transaction
        logger.info(f"Withdrawal request by {username}: user_id={user_id}, code={code}, success={result['success']}")
        
    except Exception as e:
        logger.error(f"Error in withdrawal command: {e}")
        await processing_msg.edit_text(f"❌ Произошла ошибка при обработке вывода: {str(e)}")


 

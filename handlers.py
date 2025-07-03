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

# --- Main Keyboard ---
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("Пополнить игровой баланс"), KeyboardButton("Вывод")],
        [KeyboardButton("Поддержка 24/7"), KeyboardButton("Новостной канал")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# --- Helper Functions ---
def is_admin(update):
    return update.effective_user.id in ADMIN_IDS

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = user.username or "Unknown"
    
    # Check if user is a manager
    if is_manager(username=username, user_id=user.id):
        # Manager welcome message
        await update.message.reply_text(
            f"🔧 **Добро пожаловать, менеджер {username}!**\n\n"
            f"📋 **Доступные команды:**\n"
            f"• `/deposit <user_id> <amount>` - создать депозит\n"
            f"• `/withdrawal <user_id> <code>` - обработать вывод\n\n"
            f"💡 **Все команды работают сразу, подтверждение не требуется!**",
            reply_markup=get_main_keyboard(),
            parse_mode="Markdown"
        )
    else:
        # Regular user welcome message - restored original detailed version
        await update.message.reply_text(
            "👋 Добро пожаловать в официальный бот нашей кассы 1win!\n\n"
            "Здесь вы можете:\n"
            "✅ Пополнить игровой счёт без задержек\n"
            "✅ Получить бонусы при пополнении\n"
            "✅ Быстро выводить средства\n"
            "✅ Следить за новостями и акциями\n\n"
            "💬 Мы работаем 24/7 — всегда на связи!\n"
            "🎁 Бонус при первом пополнении уже ждёт вас!",
            reply_markup=get_main_keyboard()
        )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "Пополнить игровой баланс":
        await update.message.reply_text(
            "💰 **Пополнение баланса**\n\n"
            "Для пополнения баланса обратитесь к нашему менеджеру:\n"
            "@manager_username\n\n"
            "Менеджер поможет вам с пополнением счета!",
            parse_mode=ParseMode.MARKDOWN
        )
    elif text == "Вывод":
        await update.message.reply_text(
            "💸 **Вывод средств**\n\n"
            "Для вывода средств обратитесь к нашему менеджеру:\n"
            "@manager_username\n\n"
            "Менеджер обработает ваш запрос на вывод!",
            parse_mode=ParseMode.MARKDOWN
        )
    elif text == "Поддержка 24/7":
        await update.message.reply_text(
            "🆘 **Техническая поддержка**\n\n"
            "Наша поддержка работает 24/7!\n"
            "Обращайтесь: @support_username",
            parse_mode=ParseMode.MARKDOWN
        )
    elif text == "Новостной канал":
        await update.message.reply_text(
            "📢 **Новости и обновления**\n\n"
            "Подписывайтесь на наш канал:\n"
            "@news_channel\n\n"
            "Там вы найдете последние новости и акции!",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            "Пожалуйста, используйте кнопки меню для навигации.",
            reply_markup=get_main_keyboard()
        )

# This handler is no longer used by the main keyboard but might be used elsewhere.
# If not, it can be removed. For now, I'll leave it but its logic is replaced by handle_text
async def handle_button_press(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # It's good practice to answer all callbacks
    # The old logic is now in handle_text
    await query.edit_message_text(text="This action is now handled by the main keyboard buttons.")

# --- Admin Handlers ---
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

    # Check if manager already exists
    if username in db.get_all_managers():
        await update.message.reply_text(
            f"⚠️ Менеджер @{username} уже существует в списке.\n\n"
            "Пожалуйста, введите другое имя пользователя или используйте /cancel для отмены."
        )
        return WAITING_FOR_MANAGER_USERNAME
    
    # Automatically add manager without requiring them to message first
    if db.add_manager(username):
        await update.message.reply_text(
            f"✅ Менеджер @{username} успешно добавлен!\n\n"
            f"Теперь @{username} может использовать команды:\n"
            f"• /deposit <user_id> <amount> - создать депозит\n"
            f"• /withdrawal <user_id> <code> - обработать вывод\n\n"
            f"💡 Команды работают сразу, подтверждение не требуется!"
        )
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            f"❌ Ошибка при добавлении менеджера @{username}.\n"
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
        await update.message.reply_text(f"✅ Менеджер @{username} успешно удален из списка.")
    else:
        await update.message.reply_text(f"❌ Менеджер @{username} не найден в списке.")
    
    return ConversationHandler.END

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

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


# --- Manager API Commands ---
def is_manager(username: str = None, user_id: int = None) -> bool:
    """Check if the user is a manager by username."""
    if username:
        # Remove @ if present
        if username.startswith('@'):
            username = username[1:]
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
        await update.message.reply_text(
            "❌ У вас должен быть установлен username в Telegram для использования этой команды.\n\n"
            "💡 Как установить username:\n"
            "1. Откройте настройки Telegram\n"
            "2. Нажмите 'Имя пользователя'\n"
            "3. Введите желаемое имя пользователя"
        )
        return
    
    if not is_manager(username=username, user_id=user_id_telegram):
        await update.message.reply_text(
            "❌ У вас нет прав для выполнения этой команды.\n\n"
            "Обратитесь к администратору для добавления в список менеджеров."
        )
        return
    
    if len(context.args) != 2:
        await update.message.reply_text(
            "❌ Неверный формат команды!\n\n"
            "**Правильное использование:**\n"
            "`/deposit <user_id> <amount>`\n\n"
            "**Примеры:**\n"
            "`/deposit 123456 1000` - депозит 1000 для пользователя 123456\n"
            "`/deposit 789012 500.50` - депозит 500.50 для пользователя 789012\n\n"
            "**Где взять user_id:**\n"
            "• ID пользователя в системе 1win\n"
            "• Обычно это 6-10 цифр\n"
            "• Уточните у пользователя его ID в приложении 1win",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        user_id = int(context.args[0])
        amount = float(context.args[1])
        
        if amount <= 0:
            await update.message.reply_text(
                "❌ Сумма должна быть больше 0!\n\n"
                "Попробуйте ввести положительную сумму, например: `/deposit 123456 1000`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        if amount > 1000000:  # 1 million limit for safety
            await update.message.reply_text(
                "❌ Слишком большая сумма!\n\n"
                "Максимальная сумма депозита: 1,000,000\n"
                "Попробуйте меньшую сумму."
            )
            return
            
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат данных!\n\n"
            "**Проверьте:**\n"
            "• user_id должен быть целым числом (например: 123456)\n"
            "• amount должен быть числом (например: 1000 или 500.50)\n\n"
            "**Правильный пример:**\n"
            "`/deposit 123456 1000`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Show processing message
    processing_msg = await update.message.reply_text(
        f"⏳ **Обрабатываю депозит...**\n\n"
        f"👤 Пользователь: `{user_id}`\n"
        f"💰 Сумма: `{amount}`\n"
        f"🔄 Отправляю запрос в 1win...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Log the API call attempt
    logger.info(f"Making API call for deposit: user_id={user_id}, amount={amount}")
    
    # Make API call
    try:
        client = WinAPIClient(API_KEY)
        result = await client.create_deposit(user_id, amount)
        
        # Update message with result
        await processing_msg.edit_text(result["message"], parse_mode=ParseMode.MARKDOWN)
        
        # Log the transaction
        logger.info(f"Deposit request by {username}: user_id={user_id}, amount={amount}, success={result['success']}")
        
    except Exception as e:
        logger.error(f"Error in deposit command: {e}")
        await processing_msg.edit_text(
            f"❌ **Произошла ошибка при обработке депозита**\n\n"
            f"**Техническая информация:**\n"
            f"`{str(e)}`\n\n"
            f"💡 **Что делать:**\n"
            f"• Попробуйте еще раз через минуту\n"
            f"• Проверьте правильность данных\n"
            f"• Обратитесь к администратору, если проблема повторяется",
            parse_mode=ParseMode.MARKDOWN
        )


async def withdrawal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /withdrawal command for managers."""
    username = update.effective_user.username
    user_id_telegram = update.effective_user.id
    
    # Log the command attempt
    logger.info(f"Withdrawal command attempted by user: {username} (ID: {user_id_telegram})")
    
    if not username:
        await update.message.reply_text(
            "❌ У вас должен быть установлен username в Telegram для использования этой команды.\n\n"
            "💡 Как установить username:\n"
            "1. Откройте настройки Telegram\n"
            "2. Нажмите 'Имя пользователя'\n"
            "3. Введите желаемое имя пользователя"
        )
        return
    
    if not is_manager(username=username, user_id=user_id_telegram):
        await update.message.reply_text(
            "❌ У вас нет прав для выполнения этой команды.\n\n"
            "Обратитесь к администратору для добавления в список менеджеров."
        )
        return
    
    if len(context.args) != 2:
        await update.message.reply_text(
            "❌ Неверный формат команды!\n\n"
            "**Правильное использование:**\n"
            "`/withdrawal <user_id> <code>`\n\n"
            "**Примеры:**\n"
            "`/withdrawal 123456 1234` - вывод для пользователя 123456 с кодом 1234\n"
            "`/withdrawal 789012 5678` - вывод для пользователя 789012 с кодом 5678\n\n"
            "**Что нужно:**\n"
            "• user_id - ID пользователя в системе 1win\n"
            "• code - 4-значный код подтверждения от пользователя\n\n"
            "**Как получить код:**\n"
            "Пользователь должен создать запрос на вывод в приложении 1win и получить код подтверждения.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        user_id = int(context.args[0])
        code = int(context.args[1])
        
        if code < 0:
            await update.message.reply_text(
                "❌ Код должен быть положительным числом!\n\n"
                "Попробуйте ввести код снова, например: `/withdrawal 123456 1234`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
            
        if len(str(code)) != 4:
            await update.message.reply_text(
                "⚠️ Внимание: код обычно состоит из 4 цифр.\n\n"
                "Убедитесь, что код введен правильно.\n"
                f"Ваш код: `{code}`\n\n"
                "Если код правильный, проигнорируйте это сообщение.",
                parse_mode=ParseMode.MARKDOWN
            )
        
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат данных!\n\n"
            "**Проверьте:**\n"
            "• user_id должен быть целым числом (например: 123456)\n"
            "• code должен быть числом (например: 1234)\n\n"
            "**Правильный пример:**\n"
            "`/withdrawal 123456 1234`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Show processing message
    processing_msg = await update.message.reply_text(
        f"⏳ **Обрабатываю вывод...**\n\n"
        f"👤 Пользователь: `{user_id}`\n"
        f"🔐 Код: `{code}`\n"
        f"🔄 Отправляю запрос в 1win...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Log the API call attempt
    logger.info(f"Making API call for withdrawal: user_id={user_id}, code={code}")
    
    # Make API call
    try:
        client = WinAPIClient(API_KEY)
        result = await client.process_withdrawal(user_id, code)
        
        # Update message with result
        await processing_msg.edit_text(result["message"], parse_mode=ParseMode.MARKDOWN)
        
        # Log the transaction
        logger.info(f"Withdrawal request by {username}: user_id={user_id}, code={code}, success={result['success']}")
        
    except Exception as e:
        logger.error(f"Error in withdrawal command: {e}")
        await processing_msg.edit_text(
            f"❌ **Произошла ошибка при обработке вывода**\n\n"
            f"**Техническая информация:**\n"
            f"`{str(e)}`\n\n"
            f"💡 **Что делать:**\n"
            f"• Убедитесь, что пользователь создал запрос на вывод в приложении 1win\n"
            f"• Проверьте правильность кода подтверждения\n"
            f"• Попробуйте еще раз через минуту\n"
            f"• Обратитесь к администратору, если проблема повторяется",
            parse_mode=ParseMode.MARKDOWN
        )


 

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
import database as db
from config import ADMIN_IDS

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

    if db.add_manager(username):
        await update.message.reply_text(f"✅ Менеджер @{username} успешно добавлен.")
    else:
        await update.message.reply_text(f"⚠️ Менеджер @{username} уже существует в списке.")
    
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
    else:
        await update.message.reply_text(f"⚠️ Менеджер @{username} не найден в списке.")
    
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

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Операция отменена.")
    return ConversationHandler.END 

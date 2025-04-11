import os
import asyncpg
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    CallbackContext,
    MessageHandler,
    filters
)
from telegram.constants import ParseMode
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("API_KEY")
TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
YKASSA_SHOP_ID = os.getenv("YKASSA_SHOP_ID")
YKASSA_SECRET_KEY = os.getenv("YKASSA_SECRET_KEY")

ADMINS = [2125819462, 5821566525]

async def connect_db():
    return await asyncpg.create_pool(DATABASE_URL)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    text = f"👋 Привет, {user_name}!\n\nДобро пожаловать в наш сервис! 🚀\n\nВыберите опцию ниже, чтобы начать."

    keyboard = [
        [InlineKeyboardButton("🧰 Услуги", callback_data="services")],
        [InlineKeyboardButton("🛠 Помощь", callback_data="help")]
        
    ]
    if user_id in ADMINS:
        keyboard.append([InlineKeyboardButton("⚙️ Админ-панель", callback_data='admin_panel')])

    if update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def back_to_menu(update: Update, context: CallbackContext):
    context.user_data.clear()
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    text = f"👋 Привет, {user_name}!\n\nДобро пожаловать в наш сервис! 🚀\n\nВыберите опцию ниже, чтобы начать."

    keyboard = [
        [InlineKeyboardButton("🧰 Услуги", callback_data="services")],
        [InlineKeyboardButton("🛠 Помощь", callback_data="help")]
    ]
    if user_id in ADMINS:
        keyboard.append([InlineKeyboardButton("⚙️ Админ-панель", callback_data='admin_panel')])

    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ Добавить привилегию", callback_data="add_privilege")],
        [InlineKeyboardButton("🗑️ Удалить привилегию", callback_data="delete_privilege")],
        [InlineKeyboardButton("⬅️ Назад в меню", callback_data='back_to_menu')],
    ]
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("⚙️ Админ-панель:", reply_markup=InlineKeyboardMarkup(keyboard))

# Обработчики каждой кнопки отдельно
async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Создаем кнопку "Назад в меню"
    keyboard = [
        [InlineKeyboardButton("⬅️ Назад в меню", callback_data='back_to_menu')],
    ]
    
    # Отправляем ответ на callback
    await update.callback_query.answer()

    # Обновляем сообщение с текстом и кнопками
    message = (
        "📞 **Контакты для связи**:\n\n"
        "👨‍💻 Для вопросов или поддержки обращайтесь к @Tak1xgami.\n"
    )
    await update.callback_query.edit_message_text(
        message, 
        parse_mode='Markdown',  # Используем markdown для форматирования текста
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data

    await query.answer()

    if data == "add_privilege":
        context.user_data["state"] = "ADD_PRIVILEGE_TITLE"
        keyboard = [
            [InlineKeyboardButton("⬅️ Назад", callback_data='admin_panel')],
        ]
        await query.edit_message_text("📛 Введите название привилегии:",
        reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "delete_privilege":
        pool = await connect_db()
        async with pool.acquire() as conn:
            privileges = await conn.fetch("SELECT id, title, price FROM privileges")

        keyboard = [
            [InlineKeyboardButton(
                f"🗑️ {i+1}. {priv['title']} — {priv['price']}₽",
                callback_data=f"confirm_delete_{priv['id']}"
            )]
            for i, priv in enumerate(privileges)
        ]
        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_panel")])

        await query.edit_message_text(
            "🗑️ <b>Выберите привилегию для удаления:</b>",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.HTML
        )

    elif data.startswith("confirm_delete_"):
        priv_id = int(data.split("_")[-1])

        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить", callback_data=f"delete_{priv_id}")],
            [InlineKeyboardButton("❌ Отменить", callback_data="delete_privilege")]
        ]
        await query.edit_message_text("🔴 Вы уверены, что хотите удалить эту привилегию?", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("delete_"):
        priv_id = int(data.split("_")[-1])
        pool = await connect_db()
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM privileges WHERE id = $1", priv_id)

        await start(update, context)
        await query.edit_message_text("✅ Привилегия успешно удалена!")

async def handle_text(update: Update, context: CallbackContext):
    state = context.user_data.get("state")

    if not update.message:
        return  # игнорируем всё, что не является текстовым сообщением

    if state == "ADD_PRIVILEGE_TITLE":
        context.user_data["priv_title"] = update.message.text
        context.user_data["state"] = "ADD_PRIVILEGE_DESCRIPTION"
    
        await update.message.reply_text("📝 Введите описание привилегии:")

    elif state == "ADD_PRIVILEGE_DESCRIPTION":
        context.user_data["priv_description"] = update.message.text
        context.user_data["state"] = "ADD_PRIVILEGE_PRICE"
        await update.message.reply_text("💰 Введите цену привилегии (в рублях):")

    elif state == "ADD_PRIVILEGE_PRICE":
        try:
            price = int(update.message.text)
            context.user_data["priv_price"] = price

            pool = await connect_db()
            async with pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO privileges (title, description, price) VALUES ($1, $2, $3)",
                    context.user_data["priv_title"],
                    context.user_data["priv_description"],
                    context.user_data["priv_price"]
                )

            await update.message.reply_text("✅ Привилегия успешно добавлена!")
            await start(update, context)
            context.user_data["state"] = None
        except ValueError:
            await update.message.reply_text("🚫 Введите корректную сумму.")
    else:
        await update.message.reply_text("💬 Неизвестная команда. Используйте меню.")

async def handle_privileges(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pool = await connect_db()
    async with pool.acquire() as conn:
        privileges = await conn.fetch("SELECT id, title, description, price FROM privileges")

    if not privileges:
        text = "❌ Пока нет доступных привилегий."
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data='services')]]
    else:
        text = "<b>🎖 Доступные привилегии:</b>\n\n"
        keyboard = []

        for i, priv in enumerate(privileges, 1):
            title = priv["title"]
            description = priv["description"].strip()
            price = f"{priv['price']:,}".replace(",", " ")  # 1440 -> 1 440

            # Подготовка описания — каждую строку начинаем с тире
            desc_lines = "\n".join(f"• {line.strip()}" for line in description.splitlines() if line.strip())

            text += (
                f"<b>{i}. {title}</b>\n"
                f"{desc_lines}\n"
                f"<i>Цена:</i> <b>{price}₽</b>\n\n"
            )

            keyboard.append([InlineKeyboardButton(f"💎 {title}", callback_data=f"buy_privilege_{priv['id']}")])

        keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data='services')])

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def handle_services(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎖 Привилегии", callback_data="privileges")],
        [InlineKeyboardButton("⬅️ Назад в меню", callback_data='back_to_menu')],
    ]
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("🧰 Услуги: Список доступных услуг сервера.", reply_markup=InlineKeyboardMarkup(keyboard))

# Основной запуск
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_help, pattern="^help$"))
    app.add_handler(CallbackQueryHandler(handle_services, pattern="^services$"))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern="^back_to_menu$"))
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(handle_callback, pattern="^add_privilege$"))
    app.add_handler(CallbackQueryHandler(handle_privileges, pattern="^privileges$"))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(CallbackQueryHandler(handle_text, pattern="^delete_privilege$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__":
    main()
# bot.py - Telegram-бот для скачивания Reels, видео и фото из Instagram
# Автор: @back2hood

import os                     # Для работы с переменными окружения и файлами
import instaloader            # Библиотека для скачивания контента из Instagram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# Получаем токен бота из переменной окружения (безопасно!)
# На Render.com ты добавишь его в Environment Variables как BOT_TOKEN
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise ValueError("Не найден токен бота! Укажи BOT_TOKEN в переменных окружения.")

# Создаём объект Instaloader (без логина — работает только с публичными постами)
L = instaloader.Instaloader()

# Команда /start — приветствие и меню с кнопками
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Создаём inline-кнопки под сообщением
    keyboard = [
        [InlineKeyboardButton("📖 Как пользоваться", callback_data="help")],
        [InlineKeyboardButton("👨‍💓 Разработчик", url="https://t.me/back2hood")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Привет! 👋\n\n"
        "Я скачиваю Reels, видео и фото из Instagram.\n"
        "Просто пришли мне публичную ссылку на пост или Reel — я отправлю тебе контент без водяных знаков.\n\n"
        "Работает быстро и бесплатно 🚀",
        reply_markup=reply_markup
    )

# Обработка нажатий на inline-кнопки
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Убираем "часики" у кнопки

    if query.data == "help":
        await query.message.reply_text(
            "📖 Как пользоваться:\n\n"
            "1. Открой Instagram\n"
            "2. Найди нужный Reel, видео или фото\n"
            "3. Нажми «Поделиться» → «Копировать ссылку»\n"
            "4. Пришли эту ссылку мне\n\n"
            "Я отправлю тебе видео или фото!\n\n"
            "Важно: работает только с публичными аккаунтами."
        )

# Основная функция — обработка любой текстовой ссылки от пользователя
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    # Проверяем, что это действительно ссылка на Instagram
    if "instagram.com" not in url:
        await update.message.reply_text("❌ Это не ссылка на Instagram. Пришли ссылку вида:\nhttps://www.instagram.com/reel/ABC123/")
        return

    # Сообщаем пользователю, что начали скачивание
    status_message = await update.message.reply_text("⏳ Скачиваю контент... Подожди немного")

    try:
        # Извлекаем shortcode (уникальный код поста) из ссылки
        # Примеры: https://www.instagram.com/reel/C123abc/ → C123abc
        #          https://www.instagram.com/p/D456def/?igsh=... → D456def
        if url.endswith("/"):
            url = url[:-1]
        shortcode = url.split("/")[-1].split("?")[0]

        # Получаем объект поста по shortcode
        post = instaloader.Post.from_shortcode(L.context, shortcode)

        # Создаём временную папку с именем shortcode, чтобы не смешивать файлы
        target_dir = str(shortcode)
        L.download_post(post, target=target_dir)

        # Собираем все скачанные файлы из этой папки
        downloaded_files = []
        for file in os.listdir(target_dir):
            if file.endswith((".mp4", ".jpg", ".jpeg")):
                downloaded_files.append(os.path.join(target_dir, file))

        if not downloaded_files:
            await status_message.edit_text("😔 Не удалось найти видео или фото. Возможно, пост приватный или пустой.")
            return

        # Отправляем все найденные файлы (видео или фото)
        for file_path in downloaded_files:
            if file_path.endswith(".mp4"):
                with open(file_path, "rb") as video_file:
                    await update.message.reply_video(
                        video=video_file,
                        caption="🎥 Твой Reel/видео из Instagram!\nРазработчик: @back2hood"
                    )
            else:  # .jpg или .jpeg
                with open(file_path, "rb") as photo_file:
                    await update.message.reply_photo(
                        photo=photo_file,
                        caption="📸 Твоё фото из Instagram!\nРазработчик: @back2hood"
                    )

        await status_message.edit_text("✅ Готово! Контент отправлен выше 👆")

    except instaloader.exceptions.PrivateProfileNotFollowedError:
        await status_message.edit_text("🔒 Этот аккаунт приватный. Бот может скачивать только из публичных профилей.")
    except instaloader.exceptions.LoginRequiredException:
        await status_message.edit_text("🔒 Для этого поста нужен вход в аккаунт. Пока работаю только с публичными.")
    except Exception as e:
        # Любая другая ошибка — покажем пользователю понятное сообщение
        await status_message.edit_text(f"❌ Ошибка: {str(e)}\nПопробуй другую ссылку или позже.")

    finally:
        # УДАЛЕНИЕ ВСЕХ ВРЕМЕННЫХ ФАЙЛОВ (важно, чтобы не засорять сервер)
        try:
            if 'target_dir' in locals() and os.path.exists(target_dir):
                for file in os.listdir(target_dir):
                    os.remove(os.path.join(target_dir, file))
                os.rmdir(target_dir)
        except:
            pass  # Если не удалось удалить — не критично

# Основная функция запуска бота
def main():
    # Создаём приложение Telegram-бота
    app = Application.builder().token(TOKEN).build()

    # Добавляем обработчики команд и сообщений
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))           # для кнопок
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))  # для ссылок

    # Запускаем бота в режиме polling (он будет постоянно опрашивать Telegram)
    print("🤖 Бот запущен и работает! Нажми Ctrl+C для остановки.")
    app.run_polling()

# Запуск только если файл запущен напрямую
if __name__ == "__main__":
    main()
import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import asyncpg
from dotenv import load_dotenv
import dashscope
import json

# Загрузка переменных окружения из файла .env
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG  # Установите уровень логирования на DEBUG для подробной информации
)
logger = logging.getLogger(__name__)

# Используем переменные окружения для хранения токена и ключа API
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
QWEN_APP_ID = os.getenv('QWEN_APP_ID')
QWEN_API_KEY = os.getenv('QWEN_API_KEY')
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
POSTGRES_HOST = os.getenv('POSTGRES_HOST')
POSTGRES_PORT = int(os.getenv('POSTGRES_PORT'))
POSTGRES_DB = os.getenv('POSTGRES_DB')

if not TELEGRAM_BOT_TOKEN or not QWEN_APP_ID or not QWEN_API_KEY:
    logger.error("Не найдены переменные окружения TELEGRAM_BOT_TOKEN, QWEN_APP_ID или QWEN_API_KEY")
    exit(1)

if not POSTGRES_USER or not POSTGRES_PASSWORD or not POSTGRES_HOST or not POSTGRES_PORT or not POSTGRES_DB:
    logger.error("Не найдены переменные окружения для подключения к базе данных")
    exit(1)

# Установка API ключа
dashscope.api_key = QWEN_API_KEY

# Настройки API Qwen 2.5 Max
dashscope.base_http_api_url = 'https://dashscope-intl.aliyuncs.com/api/v1'

# Функция для подключения к базе данных
async def get_db_connection():
    try:
        conn = await asyncpg.connect(
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            database=POSTGRES_DB,
            host=POSTGRES_HOST,
            port=POSTGRES_PORT
        )
        logger.debug(f"Successfully connected to the database {POSTGRES_DB}")
        return conn
    except Exception as e:
        logger.error(f"Error connecting to the database {POSTGRES_DB}: {e}")
        raise

# Функция для сохранения контекста пользователя
async def save_context(chat_id, context):
    conn = await get_db_connection()
    try:
        logger.debug(f"Saving context for chat_id {chat_id}: {context}")
        await conn.execute('''
            INSERT INTO user_context (chat_id, context) VALUES ($1, $2)
            ON CONFLICT (chat_id) DO UPDATE SET context = EXCLUDED.context
        ''', chat_id, json.dumps(context))  # Сохраняем контекст как JSON-строку
        logger.info(f"Context saved successfully for chat_id {chat_id}")
    except Exception as e:
        logger.error(f"Error saving context for chat_id {chat_id}: {e}")
    finally:
        await conn.close()

# Функция для получения контекста пользователя
async def get_context(chat_id):
    conn = await get_db_connection()
    try:
        logger.debug(f"Fetching context for chat_id {chat_id}")
        result = await conn.fetchrow('SELECT context FROM user_context WHERE chat_id = $1', chat_id)
        if result and result['context']:
            logger.debug(f"Context found for chat_id {chat_id}: {result['context']}")
            return json.loads(result['context'])  # Преобразуем JSON-строку обратно в список
        else:
            logger.info(f"No context found for chat_id {chat_id}")
            return []
    except Exception as e:
        logger.error(f"Error fetching context for chat_id {chat_id}: {e}")
        return []
    finally:
        await conn.close()

def clean_markdown(text):
    """Удаляет экранирование символов Markdown."""
    # Удаляем обратные слэши, которые используются для экранирования символов
    return text.replace('\\', '')

def format_list_as_markdown(response_text):
    """Форматирует список в текстовом ответе в Markdown."""
    formatted_text = ""
    lines = response_text.split("\n")
    for line in lines:
        if line.strip().startswith("-"):
            formatted_text += f"• {line[1:].strip()}\n"
        elif line.strip().startswith("1.") or line.strip().startswith("2.") or line.strip().startswith("3.") or line.strip().startswith("4.") or line.strip().startswith("5."):
            formatted_text += f"{line.strip()}\n"
        else:
            formatted_text += f"{line.strip()}\n"
    return formatted_text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start."""
    await update.message.reply_text('Привет! Я бот, который взаимодействует с Qwen 2.5 Max API. Отправь мне запрос.')

async def send_message_in_chunks(update, content, max_chunk_size=4096):
    """Отправка сообщений по частям, если они превышают максимальный размер."""
    for i in range(0, len(content), max_chunk_size):
        chunk = content[i:i + max_chunk_size]
        await update.message.reply_text(chunk)

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /clearhistory."""
    chat_id = update.message.chat_id

    # Удаляем запись из базы данных
    conn = await get_db_connection()
    try:
        await conn.execute('DELETE FROM user_context WHERE chat_id = $1', chat_id)
        logger.info(f"Deleted context for chat_id {chat_id}")
        await update.message.reply_text("История успешно удалена.")
    except Exception as e:
        logger.error(f"Error deleting context for chat_id {chat_id}: {e}")
        await update.message.reply_text("Произошла ошибка при удалении истории.")
    finally:
        await conn.close()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений от пользователя."""
    user_message = update.message.text
    chat_id = update.message.chat_id
    
    # Получаем контекст из базы данных
    context_data = await get_context(chat_id)
    
    if not context_data:
        context_data = []
        logger.debug(f"No previous context found for chat_id {chat_id}. Starting with an empty context.")
    
    # Экранируем сообщение перед обработкой
    user_message_escaped = clean_markdown(user_message)
    # Добавляем сообщение пользователя в контекст
    context_data.append({'role': 'user', 'content': user_message_escaped})
    
    try:
        # Отправляем сообщение "Печатает...", чтобы уведомить пользователя
        typing_message = await update.message.reply_text("Печатает...")
        
        # Формируем список сообщений для передачи в параметре messages
        messages = [{'role': msg['role'], 'content': msg['content']} for msg in context_data]
        
        # Вызов API Qwen 2.5 Max
        response = dashscope.Application.call(app_id=QWEN_APP_ID, prompt=user_message_escaped, messages=messages)
        
        if response and 'output' in response:
            output_content = response['output']['text']
            
            # Форматируем список, если он есть в ответе
            formatted_output = format_list_as_markdown(output_content)
            # Удаляем экранирование
            clean_output = clean_markdown(formatted_output)
            # Попробуем отправить текст без MarkdownV2
            try:
                await send_message_in_chunks(update, clean_output)
            except Exception as e:
                # В случае ошибки отправляем без форматирования
                logger.error(f"Ошибка при отправке: {e}")
                await send_message_in_chunks(update, output_content, max_chunk_size=4096)
            
            # Добавляем ответ бота в контекст
            context_data.append({'role': 'assistant', 'content': clean_output})
            # Сохраняем обновленный контекст в базе данных
            await save_context(chat_id, context_data)
        else:
            await update.message.reply_text("Не удалось получить ответ от API. Попробуйте позже.")
        
        # Удаляем сообщение "Печатает..."
        await typing_message.delete()
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text("Произошла ошибка при отправке запроса.")

# Создание и запуск бота
if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("clearhistory", clear_history))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    # Запуск бота
    application.run_polling()

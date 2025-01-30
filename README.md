# Telegram Bot with Context Management

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

This is a Telegram bot that interacts with the Qwen 2.5 Max API and manages user context in a PostgreSQL database. The bot allows users to send text messages, view responses from the Qwen API, and clear their chat history.

## Features

- **Text Message Handling**: Users can send text messages and receive responses from the Qwen 2.5 Max API.
- **Context Management**: The bot maintains a conversation context for each user using a PostgreSQL database.
- **Clear History**: Users can clear their chat history by using the `/clearhistory` command.

## Prerequisites

Before you begin, ensure you have met the following requirements:

- Python 3.8 or higher installed on your system.
- A Telegram bot token (obtained from [BotFather](https://core.telegram.org/bots#botfather)).
- Qwen App ID and API Key.
- A running PostgreSQL instance.

## Installation

1. Clone the repository:
   git clone https://github.com/maksimnp/TelegramBotQwen.git
   cd telegram-bot

2. Install the required dependencies:
    pip install -r requirements.txt
   
4. Create a .env file in the root directory of the project with the following content:
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   QWEN_APP_ID=your_qwen_app_id
   QWEN_API_KEY=your_qwen_api_key
   POSTGRES_USER=your_postgres_user
   POSTGRES_PASSWORD=your_postgres_password
   POSTGRES_HOST=your_postgres_host
   POSTGRES_PORT=your_postgres_port
   POSTGRES_DB=your_postgres_db
   
5. Set up the database schema:
CREATE TABLE user_context (
    chat_id BIGINT PRIMARY KEY,
    context JSONB NOT NULL
);

## Usage
1. Start the bot:
python main.py

3. Interact with the bot via Telegram by sending text messages.

## Commands
  /start: Start the conversation with the bot.
  /clearhistory: Clear the chat history stored in the database.
## License
This project is licensed under the MIT License - see the LICENSE file for details.





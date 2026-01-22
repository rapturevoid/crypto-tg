# Crypto Self-Hosted Bot

A Telegram bot for managing cryptocurrency wallets 

## Prerequisites

- Docker and Docker Compose
- Telegram Bot Token (get from @BotFather)

## Setup

1. Clone the repository:
   ```bash
   git clone https://rapturevoid/crypto-tg
   cd crypto-tg
   ```

2. Copy the environment example file:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` file and add your Telegram Bot Token:
   ```
    BOT_TOKEN=your_telegram_bot_token_here
    TRON_NETWORK="mainnet"  # options: mainnet, nile
    MONGODB_BASE_URL="mongodb://admin:admin123@localhost:27017"
    MONGO_DB_NAME="crypto_bot_db"
   ```

4. Start the project using Docker Compose:
   ```bash
   docker-compose up --build
   ```

The bot will start and connect to MongoDB automatically.

## Running Locally (without Docker)

If you prefer to run locally:

1. Install uv (Python package manager):
   ```bash
   pip install uv
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Set up environment variables in `.env` file.

4. Run the bot:
   ```bash
   uv run python main.py
   ```

## Usage

Once the bot is running, interact with it on Telegram using the configured bot token.

## ATTENTION

For activate account on blockchain u need a topup wallet with 1 trx

https://developers.tron.network/docs/account#account-activation
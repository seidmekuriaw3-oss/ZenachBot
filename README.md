ZenachBot

ZenachBot is a Telegram commerce bot for catalog browsing, orders, payments, and admin management.

Features
- Product catalog with categories and stock tracking
- Order workflow and status management
- Admin dashboard and reporting
- Payment integration hooks
- Telegram webhook and polling support

Quick start
1. Create and activate a virtual environment.
2. Install dependencies:

	pip install -r requirements.txt

3. Create a PostgreSQL database and set the required environment variables before startup:

	BOT_TOKEN=your_telegram_bot_token
	ADMIN_IDS=123456789
	DATABASE_URL=postgresql://user:password@localhost:5432/zenach
	SECRET_KEY=long-random-secret

4. Start the bot:

	python main.py

Project layout
- main.py: application bootstrap
- handlers/: Telegram command and callback handlers
- models/: business entities and ORM models
- services/: external integrations
- database.py: PostgreSQL database access layer
- scheduler.py: background task scheduler
- webhook.py: Flask webhook endpoint for Telegram updates

Docker

Build and run with:

	docker build -t zenach-bot .
	docker run --env-file .env -p 8000:8000 zenach-bot

Testing

Run the test suite with:

	pytest -q

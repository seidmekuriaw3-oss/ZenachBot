#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ዘናጭ ቦት - ዋና የመግቢያ ፋይል
ይህ ፋይል ሁሉንም ሞጁሎች ያስጀምራል እና ቦቱን ያስነሳል
"""

import os
import sys
import logging
import asyncio
from datetime import datetime
from pathlib import Path

# የፕሮጀክቱን ሥር ወደ ፓይተን መንገድ መጨመር
sys.path.insert(0, str(Path(__file__).parent))

# የአካባቢ ተለዋዋጮችን መጫን
from dotenv import load_dotenv
load_dotenv()

# መዝገብ ማዋቀር
from utils.logger import setup_logger
logger = setup_logger('main')

# የቦት ሞጁሎች
from telebot import TeleBot
from telebot.types import BotCommand, BotCommandScopeDefault

# የውስጥ ሞጁሎች
from config import Config, BotConfig
from database import Database
from handlers import register_handlers
from scheduler import Scheduler
from middleware import setup_middleware
from utils.helpers import load_languages


def add_telegram_message_fallback(bot: TeleBot):
    """Retry messages without formatting when Telegram rejects Markdown."""
    original_send_message = bot.send_message

    def send_message_with_fallback(*args, **kwargs):
        try:
            return original_send_message(*args, **kwargs)
        except Exception as error:
            if kwargs.get('parse_mode') and "can't parse entities" in str(error).lower():
                fallback_kwargs = dict(kwargs)
                fallback_kwargs.pop('parse_mode', None)
                return original_send_message(*args, **fallback_kwargs)
            raise

    bot.send_message = send_message_with_fallback
    return bot

# የስህተት አያያዝ ክፍል
def setup_error_handlers():
    """አለምአቀፍ የስህተት አያያዝ ማዋቀር"""
    
    def handle_exception(exc_type, exc_value, exc_traceback):
        """ያልተያዙ ስህተቶችን መያዝ"""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        logger.critical(
            "ያልተጠበቀ ስህተት",
            exc_info=(exc_type, exc_value, exc_traceback)
        )
        
        # ወደ ፋይል መመዝገብ
        with open('logs/critical_errors.log', 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"የስህተት ጊዜ: {datetime.now()}\n")
            f.write(f"ስህተት አይነት: {exc_type.__name__}\n")
            f.write(f"መልእክት: {exc_value}\n")
            import traceback
            traceback.print_tb(exc_traceback, file=f)
            f.write(f"{'='*60}\n")
    
    sys.excepthook = handle_exception

# የቦት ትዕዛዞችን ማዋቀር
def setup_bot_commands(bot: TeleBot):
    """የቦት ትዕዛዞችን መመዝገብ"""
    commands = [
        BotCommand("start", "ቦቱን ጀምር / Start bot"),
        BotCommand("help", "እርዳታ ለማግኘት / Get help"),
        BotCommand("menu", "ዋና ሜኑ ለማሳየት / Show main menu"),
        BotCommand("profile", "መገለጫዎን ለማየት / View profile"),
        BotCommand("orders", "ትዕዛዞችዎን ለማየት / View orders"),
        BotCommand("cart", "ጋሪዎን ለማየት / View cart"),
        BotCommand("lang", "ቋንቋ ለመቀየር / Change language"),
    ]
    
    # የአስተዳዳሪ ተጠቃሚዎች ተጨማሪ ትዕዛዞች
    admin_commands = [
        BotCommand("admin", "የአስተዳዳሪ ፓነል / Admin panel"),
        BotCommand("stats", "ስታቲስቲክስ ለማየት / View stats"),
        BotCommand("backup", "የውሂብ ጎታ ምትኬ ለመስራት / Backup database"),
    ]
    
    try:
        bot.set_my_commands(commands, scope=BotCommandScopeDefault())
        logger.info("✅ የቦት ትዕዛዞች ተመዝግበዋል")
    except Exception as e:
        logger.warning(f"⚠️ ትዕዛዞችን መመዝገብ አልተቻለም; ቦቱ ግን ይቀጥላል: {e}")

# የቦት መጀመሪያ
def main():
    """ዋና ተግባር - ቦቱን ያስጀምራል"""
    
    # የስህተት አያያዝ ማዋቀር
    setup_error_handlers()
    
    # የፕሮጀክት ሥር ማውጫ
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # አስፈላጊ ማውጫዎችን መፍጠር
    required_dirs = [
        'logs',
        'cache',
        'assets/temp',
        'assets/images/products',
        'assets/documents/invoices',
        'assets/documents/backups',
    ]
    
    for dir_path in required_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    # ውቅር መፈተሽ
    config = Config()
    
    # ቋንቋዎችን መጫን
    try:
        load_languages()
        logger.info("✅ ቋንቋዎች ተጭነዋል")
    except Exception as e:
        logger.error(f"❌ ቋንቋዎችን መጫን አልተቻለም: {e}")
        sys.exit(1)
    
    # የውሂብ ጎታ ማዋቀር
    try:
        db = Database()
        logger.info("✅ የውሂብ ጎታ ተዘጋጅቷል")
    except Exception as e:
        logger.error(f"❌ የውሂብ ጎታ ማዋቀር አልተቻለም: {e}")
        sys.exit(1)
    
    # ቦት መፍጠር
    try:
        bot = add_telegram_message_fallback(TeleBot(config.bot.TOKEN))
        logger.info("✅ ቦት ተፈጥሯል")
    except Exception as e:
        logger.error(f"❌ ቦት መፍጠር አልተቻለም: {e}")
        sys.exit(1)
    
    # ሚድልዌር ማዋቀር
    try:
        setup_middleware(bot, db)
        logger.info("✅ ሚድልዌር ተዘጋጅቷል")
    except Exception as e:
        logger.error(f"❌ ሚድልዌር ማዋቀር አልተቻለም: {e}")
    
    # የቦት ትዕዛዞች ማዋቀር
    setup_bot_commands(bot)
    
    # የእጅ አያያዝ (handlers) መመዝገብ
    try:
        register_handlers(bot, db)
        logger.info("✅ ሁሉም እጅ አያያዞች ተመዝግበዋል")
    except Exception as e:
        logger.error(f"❌ እጅ አያያዞችን መመዝገብ አልተቻለም: {e}")
        sys.exit(1)
    
    # የጊዜ ሰሌዳ ማስጀመር
    try:
        scheduler = Scheduler(bot, db)
        scheduler.start()
        logger.info("✅ የጊዜ ሰሌዳ ተጀምሯል")
    except Exception as e:
        logger.error(f"❌ የጊዜ ሰሌዳ ማስጀመር አልተቻለም: {e}")
    
    # የቦት መጀመሪያ መልዕክት
    logger.info("=" * 60)
    logger.info(f"🤖 ዘናጭ ቦት እየሰራ ነው...")
    logger.info(f"📱 የቦት ስም: {bot.get_me().first_name}")
    logger.info(f"🆔 የቦት ID: {bot.get_me().id}")
    logger.info("🗄️ የውሂብ ጎታ: PostgreSQL")
    logger.info(f"⏰ ጊዜ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    # ቦቱን ማስነሳት
    try:
        # ማልቲ-ስራ ሂደት (webhook vs polling)
        if config.bot.USE_WEBHOOK:
            # ዌብሁክ ሞድ
            webhook_url = f"{config.bot.WEBHOOK_URL}{config.bot.WEBHOOK_PATH}"
            bot.remove_webhook()
            bot.set_webhook(
                url=webhook_url,
                certificate=open(config.bot.WEBHOOK_CERT, 'rb') if config.bot.WEBHOOK_CERT else None,
                max_connections=100
            )
            logger.info(f"✅ ዌብሁክ ተዘጋጅቷል: {webhook_url}")
            
            # ፍላስክ ሰርቨር ማስጀመር
            from webhook import app
            app.run(host='0.0.0.0', port=config.bot.WEBHOOK_PORT)
        else:
            # ፖሊንግ ሞድ
            logger.info("🔄 ቦቱ በፖሊንግ ሞድ እየሰራ ነው...")
            bot.infinity_polling(
                timeout=60,
                long_polling_timeout=30,
                allowed_updates=['message', 'callback_query', 'inline_query', 'chosen_inline_result'],
                none_stop=True,
                skip_pending=True,
                interval=0,
            )
    except KeyboardInterrupt:
        logger.info("🛑 ቦቱ በእጅ ተቋርጧል")
    except Exception as e:
        logger.error(f"❌ ቦቱ በስህተት ተቋርጧል: {e}")
        raise
    finally:
        # ማጽዳት
        try:
            scheduler.stop()
            db.close()
            logger.info("✅ ሁሉም ግብአቶች ተዘግተዋል")
        except:
            pass
        
        logger.info("👋 ቦቱ ተቋርጧል")

# የቦት መጀመሪያ በአማራጭ በዌብሁክ
def start_webhook():
    """የዌብሁክ ሰርቨር ማስጀመር"""
    from webhook import app, bot, db
    
    config = Config()
    
    # ዌብሁክ መዝገብ
    webhook_url = f"{config.bot.WEBHOOK_URL}{config.bot.WEBHOOK_PATH}"
    bot.remove_webhook()
    bot.set_webhook(
        url=webhook_url,
        max_connections=100
    )
    
    logger.info(f"✅ ዌብሁክ ተዘጋጅቷል: {webhook_url}")
    
    # ሰርቨር ማስጀመር
    app.run(host='0.0.0.0', port=config.bot.WEBHOOK_PORT)

if __name__ == '__main__':
    # የስራ ሁነታ መምረጥ
    if len(sys.argv) > 1 and sys.argv[1] == 'webhook':
        start_webhook()
    else:
        main()
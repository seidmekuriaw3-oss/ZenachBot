# -*- coding: utf-8 -*-

"""
ዘናጭ ቦት - የስህተት እጅ አያያዝ
ይህ ፋይል ሁሉንም የስህተት እጅ አያያዞችን ይይዛል
"""

import logging
import sys
import traceback
from datetime import datetime
from typing import Optional

from telebot import TeleBot
from telebot.types import Message, CallbackQuery

from database import Database
from config import config
from utils.helpers import get_user_lang, get_text
from services.notifications import notify_admins

logger = logging.getLogger(__name__)


def register(bot: TeleBot, db: Database):
    """የስህተት እጅ አያያዞችን መመዝገብ"""
    
    # ==================== አለምአቀፍ የስህተት አያያዝ ====================
    
    @bot.message_handler(func=lambda message: True)
    def handle_all_errors(message: Message):
        """ሁሉንም መልዕክቶች በስህተት ሲያያዝ አያያዝ"""
        try:
            # መልዕክቱን ማስኬድ
            bot.process_new_messages([message])
        except Exception as e:
            # ስህተት ከተከሰተ
            error_handler(message, e, db, bot)
    
    # ==================== የ Callback ስህተት አያያዝ ====================
    
    @bot.callback_query_handler(func=lambda call: True)
    def handle_callback_errors(call: CallbackQuery):
        """የ Callback ስህተት አያያዝ"""
        try:
            # Callback ማስኬድ
            bot.process_new_callback_query([call])
        except Exception as e:
            # ስህተት ከተከሰተ
            callback_error_handler(call, e, db, bot)
    
    # ==================== የስህተት አስተናጋጅ ====================
    
    def error_handler(message: Message, error: Exception, db: Database, bot: TeleBot):
        """የመልዕክት ስህተት አስተናጋጅ"""
        user_id = message.from_user.id if message.from_user else None
        chat_id = message.chat.id if message.chat else None
        
        # ስህተቱን መዝገብ
        error_msg = f"""
❌ የመልዕክት ስህተት
─────────────────
👤 ተጠቃሚ: {user_id}
💬 መልዕክት: {message.text[:100] if message.text else 'N/A'}
📅 ጊዜ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🐞 ስህተት: {str(error)}
📋 ዝርዝር:
{traceback.format_exc()}
"""
        
        logger.error(error_msg)
        
        # ለአስተዳዳሪ ማሳወቅ
        if user_id not in config.bot.ADMIN_IDS:
            notify_admins(bot, error_msg)
        
        # ለተጠቃሚ መልስ
        if chat_id:
            try:
                lang = get_user_lang(db, user_id) if user_id else 'am'
                bot.reply_to(
                    message,
                    get_text(lang, 'error_occurred')
                )
            except:
                # መልስ መላክ ካልተቻለ
                pass
        
        # ስህተቱን ወደ ፋይል መመዝገብ
        with open('logs/errors.log', 'a', encoding='utf-8') as f:
            f.write(error_msg)
            f.write("\n" + "="*60 + "\n")
    
    def callback_error_handler(call: CallbackQuery, error: Exception, db: Database, bot: TeleBot):
        """የ Callback ስህተት አስተናጋጅ"""
        user_id = call.from_user.id if call.from_user else None
        
        # ስህተቱን መዝገብ
        error_msg = f"""
❌ የ Callback ስህተት
─────────────────
👤 ተጠቃሚ: {user_id}
🔗 ጥሪ: {call.data}
📅 ጊዜ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🐞 ስህተት: {str(error)}
📋 ዝርዝር:
{traceback.format_exc()}
"""
        
        logger.error(error_msg)
        
        # ለአስተዳዳሪ ማሳወቅ
        if user_id not in config.bot.ADMIN_IDS:
            notify_admins(bot, error_msg)
        
        # ለተጠቃሚ መልስ
        try:
            lang = get_user_lang(db, user_id) if user_id else 'am'
            bot.answer_callback_query(
                call.id,
                get_text(lang, 'error_occurred'),
                show_alert=True
            )
        except:
            # መልስ መላክ ካልተቻለ
            pass
        
        # ስህተቱን ወደ ፋይል መመዝገብ
        with open('logs/callback_errors.log', 'a', encoding='utf-8') as f:
            f.write(error_msg)
            f.write("\n" + "="*60 + "\n")
    
    # ==================== የስርዓት ስህተት አያያዝ ====================
    
    def system_error_handler(exc_type, exc_value, exc_traceback):
        """የስርዓት ስህተት አስተናጋጅ"""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        # ስህተቱን መዝገብ
        error_msg = f"""
💥 የስርዓት ስህተት
─────────────────
📅 ጊዜ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🐞 ስህተት: {str(exc_value)}
📋 ዝርዝር:
{''.join(traceback.format_tb(exc_traceback))}
"""
        
        logger.critical(error_msg)
        
        # ወደ ፋይል መመዝገብ
        with open('logs/system_errors.log', 'a', encoding='utf-8') as f:
            f.write(error_msg)
            f.write("\n" + "="*60 + "\n")
        
        # ለአስተዳዳሪ ማሳወቅ (ከተቻለ)
        try:
            from services.notifications import notify_admins
            notify_admins(bot, error_msg)
        except:
            pass
    
    # የስርዓት ስህተት አስተናጋጅ መመዝገብ
    sys.excepthook = system_error_handler
    
    # ==================== የቦት ስህተት አያያዝ ====================
    
    @bot.error_handler
    def bot_error_handler(error: Error):
        """የቦት ስህተት አስተናጋጅ"""
        error_msg = f"""
⚠️ የቦት ስህተት
─────────────────
📅 ጊዜ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
🐞 ስህተት: {str(error)}
📋 ዝርዝር:
{traceback.format_exc()}
"""
        
        logger.error(error_msg)
        
        # ወደ ፋይል መመዝገብ
        with open('logs/bot_errors.log', 'a', encoding='utf-8') as f:
            f.write(error_msg)
            f.write("\n" + "="*60 + "\n")
        
        # ለአስተዳዳሪ ማሳወቅ
        try:
            notify_admins(bot, error_msg)
        except:
            pass
    
    # ==================== የውሂብ ጎታ ስህተት አያያዝ ====================
    
    def db_error_handler(error: Exception, query: str = None, params: tuple = None):
        """የውሂብ ጎታ ስህተት አስተናጋጅ"""
        error_msg = f"""
🗄️ የውሂብ ጎታ ስህተት
─────────────────
📅 ጊዜ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
📝 ጥያቄ: {query}
📦 መለኪያዎች: {params}
🐞 ስህተት: {str(error)}
📋 ዝርዝር:
{traceback.format_exc()}
"""
        
        logger.error(error_msg)
        
        # ወደ ፋይል መመዝገብ
        with open('logs/db_errors.log', 'a', encoding='utf-8') as f:
            f.write(error_msg)
            f.write("\n" + "="*60 + "\n")
        
        # ለአስተዳዳሪ ማሳወቅ
        try:
            notify_admins(bot, error_msg)
        except:
            pass
    
    # ==================== የማስታወቂያ ስህተት አያያዝ ====================
    
    def notification_error_handler(error: Exception, user_id: int, notification_type: str):
        """የማስታወቂያ ስህተት አስተናጋጅ"""
        error_msg = f"""
📨 የማስታወቂያ ስህተት
─────────────────
📅 ጊዜ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
👤 ተጠቃሚ: {user_id}
📊 አይነት: {notification_type}
🐞 ስህተት: {str(error)}
📋 ዝርዝር:
{traceback.format_exc()}
"""
        
        logger.error(error_msg)
        
        # ወደ ፋይል መመዝገብ
        with open('logs/notification_errors.log', 'a', encoding='utf-8') as f:
            f.write(error_msg)
            f.write("\n" + "="*60 + "\n")
    
    # ==================== የክፍያ ስህተት አያያዝ ====================
    
    def payment_error_handler(error: Exception, user_id: int, amount: float, method: str):
        """የክፍያ ስህተት አስተናጋጅ"""
        error_msg = f"""
💳 የክፍያ ስህተት
─────────────────
📅 ጊዜ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
👤 ተጠቃሚ: {user_id}
💰 መጠን: {amount} ETB
💳 ዘዴ: {method}
🐞 ስህተት: {str(error)}
📋 ዝርዝር:
{traceback.format_exc()}
"""
        
        logger.error(error_msg)
        
        # ወደ ፋይል መመዝገብ
        with open('logs/payment_errors.log', 'a', encoding='utf-8') as f:
            f.write(error_msg)
            f.write("\n" + "="*60 + "\n")
        
        # ለአስተዳዳሪ ማሳወቅ
        try:
            notify_admins(bot, error_msg)
        except:
            pass
    
    # ==================== የእንቅስቃሴ ማስተካከያ ====================
    
    # ለውጭ መጠቀሚያ የስህተት አስተናጋጆችን መጋራት
    bot.db_error_handler = db_error_handler
    bot.notification_error_handler = notification_error_handler
    bot.payment_error_handler = payment_error_handler
    
    logger.info("✅ የስህተት እጅ አያያዞች ተመዝግበዋል")


# ==================== ረዳት ተግባራት ====================

def format_error_for_user(error: Exception, lang: str = 'am') -> str:
    """ስህተቱን ለተጠቃሚ ለመላክ ማስተካከል"""
    error_messages = {
        'am': {
            'database': "❌ የውሂብ ጎታ ስህተት ተከስቷል. እባክዎ በኋላ ይሞክሩ.",
            'network': "❌ የአውታረ መረብ ስህተት. እባክዎ ግንኙነትዎን ይፈትሹ.",
            'payment': "❌ የክፍያ ስህተት ተከስቷል. እባክዎ በኋላ ይሞክሩ.",
            'unknown': "❌ ያልተጠበቀ ስህተት ተከስቷል. እባክዎ በኋላ ይሞክሩ."
        },
        'en': {
            'database': "❌ Database error occurred. Please try again later.",
            'network': "❌ Network error. Please check your connection.",
            'payment': "❌ Payment error occurred. Please try again later.",
            'unknown': "❌ An unexpected error occurred. Please try again later."
        }
    }
    
    # የስህተት አይነት መለየት
    error_str = str(error).lower()
    
    if 'database' in error_str or 'postgres' in error_str:
        error_type = 'database'
    elif 'network' in error_str or 'timeout' in error_str:
        error_type = 'network'
    elif 'payment' in error_str or 'chapa' in error_str:
        error_type = 'payment'
    else:
        error_type = 'unknown'
    
    return error_messages.get(lang, error_messages['am']).get(error_type, error_messages['am']['unknown'])


def safe_send_message(bot: TeleBot, chat_id: int, text: str, **kwargs):
    """በደህንነት መልዕክት መላክ"""
    try:
        return bot.send_message(chat_id, text, **kwargs)
    except Exception as e:
        logger.error(f"መልዕክት መላክ አልተቻለም: {e}")
        return None


def safe_edit_message(bot: TeleBot, chat_id: int, message_id: int, text: str, **kwargs):
    """በደህንነት መልዕክት ማስተካከል"""
    try:
        return bot.edit_message_text(text, chat_id, message_id, **kwargs)
    except Exception as e:
        logger.error(f"መልዕክት ማስተካከል አልተቻለም: {e}")
        return None


def safe_delete_message(bot: TeleBot, chat_id: int, message_id: int):
    """በደህንነት መልዕክት መሰረዝ"""
    try:
        return bot.delete_message(chat_id, message_id)
    except Exception as e:
        logger.error(f"መልዕክት መሰረዝ አልተቻለም: {e}")
        return None


def safe_answer_callback(bot: TeleBot, callback_id: str, text: str = None, show_alert: bool = False):
    """በደህንነት ጥሪ መልስ መስጠት"""
    try:
        return bot.answer_callback_query(callback_id, text, show_alert=show_alert)
    except Exception as e:
        logger.error(f"ጥሪ መልስ መስጠት አልተቻለም: {e}")
        return None
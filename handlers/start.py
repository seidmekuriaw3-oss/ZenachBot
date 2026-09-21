# -*- coding: utf-8 -*-

"""
ዘናጭ ቦት - የመጀመሪያ ሜኑ እጅ አያያዝ
ይህ ፋይል የ /start ትዕዛዝ እና የመጀመሪያ ሜኑ እጅ አያያዞችን ይይዛል
"""

import logging
from typing import Optional
from datetime import datetime

from telebot import TeleBot
from telebot.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database import Database
from utils.helpers import get_text, get_lang, get_user_lang
from keyboards.reply import get_main_menu, get_language_menu
from keyboards.inline import get_start_keyboard
from services.notifications import notify_admin

logger = logging.getLogger(__name__)


def register(bot: TeleBot, db: Database):
    """የ /start ትዕዛዝ እና ተዛማጅ እጅ አያያዞችን መመዝገብ"""
    
    # ==================== /start ትዕዛዝ ====================
    
    @bot.message_handler(commands=['start'])
    def start_command(message: Message):
        """የ /start ትዕዛዝ አያያዝ"""
        user_id = message.from_user.id
        username = message.from_user.username
        first_name = message.from_user.first_name
        last_name = message.from_user.last_name
        
        # ተጠቃሚን መመዝገብ
        user = db.get_user(user_id)
        
        if not user:
            # አዲስ ተጠቃሚ
            db.create_user(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                lang='am'  # ነባሪ ቋንቋ
            )
            logger.info(f"🆕 አዲስ ተጠቃሚ: {user_id} (@{username})")
            
            # ለአስተዳዳሪ ማሳወቅ
            notify_admin(
                bot,
                f"🆕 *አዲስ ተጠቃሚ ተመዝግቧል!*\n\n"
                f"👤 ስም: {first_name} {last_name or ''}\n"
                f"🔹 @{username or 'Unknown'}\n"
                f"🆔 ID: {user_id}\n"
                f"📅 ጊዜ: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
        else:
            # ነባር ተጠቃሚን ማዘመን
            db.update_user(
                user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                last_active=datetime.now().isoformat()
            )
        
        # የእንቅስቃሴ ሎግ
        db.log_activity(user_id, 'start', 'ቦቱን ጀምሯል')
        
        # ቋንቋ ምርጫ ማሳየት
        lang = get_user_lang(db, user_id)
        
        if not lang or lang not in ['am', 'en']:
            # ቋንቋ ካልተመረጠ - የቋንቋ ምርጫ ማሳየት
            markup = get_language_menu()
            bot.send_message(
                message.chat.id,
                "👋 እንኳን ደህና መጡ!\n\n"
                "ቋንቋ ይምረጡ / Choose Language:",
                reply_markup=markup
            )
        else:
            # ዋና ሜኑ ማሳየት
            show_welcome(message.chat.id, user_id, db, bot)
    
    # ==================== የቋንቋ ምርጫ ====================
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
    def handle_language_selection(call: CallbackQuery):
        """የቋንቋ ምርጫ አያያዝ"""
        user_id = call.from_user.id
        lang = 'am' if call.data == 'lang_am' else 'en'
        
        # ቋንቋ ማስቀመጥ
        db.update_user(user_id, lang=lang)
        db.log_activity(user_id, 'set_lang', f'ቋንቋ: {lang}')
        
        # ማስታወቂያ
        welcome_msg = get_text(lang, 'welcome')
        bot.answer_callback_query(call.id, welcome_msg)
        
        # መልዕክቱን መሰረዝ
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        
        # ዋና ሜኑ ማሳየት
        show_welcome(call.message.chat.id, user_id, db, bot)
    
    # ==================== ወደ ዋና ሜኑ መመለስ ====================
    
    @bot.message_handler(commands=['menu'])
    def menu_command(message: Message):
        """የ /menu ትዕዛዝ - ዋና ሜኑ ማሳየት"""
        user_id = message.from_user.id
        show_welcome(message.chat.id, user_id, db, bot)
    
    @bot.message_handler(commands=['help'])
    def help_command(message: Message):
        """የ /help ትዕዛዝ - እርዳታ ማሳየት"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        
        help_text = get_text(lang, 'help_text')
        
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("🔙 " + get_text(lang, 'back'), callback_data="main_menu")
        )
        
        bot.send_message(
            message.chat.id,
            help_text,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    
    # ==================== የመጀመሪያ ሜኑ ማሳየት ====================
    
    @bot.callback_query_handler(func=lambda call: call.data == 'main_menu')
    def handle_main_menu(call: CallbackQuery):
        """ወደ ዋና ሜኑ መመለስ"""
        user_id = call.from_user.id
        
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        
        show_welcome(call.message.chat.id, user_id, db, bot)
    
    # ==================== ረዳት ተግባራት ====================
    
    def show_welcome(chat_id: int, user_id: int, db: Database, bot: TeleBot):
        """የእንኳን ደህና መጡ መልዕክት እና ዋና ሜኑ ማሳየት"""
        lang = get_user_lang(db, user_id)
        user = db.get_user(user_id)
        
        # የእንኳን ደህና መጡ መልዕክት
        welcome_msg = get_text(lang, 'welcome_msg')
        
        # የተጠቃሚ ስም
        first_name = user['first_name'] if user else 'ደንበኛ'
        
        # የተቀናበረ መልዕክት
        msg = f"👋 *እንኳን ደህና መጡ {first_name}!*\n\n"
        msg += f"{welcome_msg}\n\n"
        msg += f"📌 ከታች ካሉት አዝራሮች ይምረጡ:"
        
        # ዋና ሜኑ ማግኘት
        markup = get_main_menu(user_id, db)
        
        bot.send_message(
            chat_id,
            msg,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    
    # ==================== መጀመሪያ ላይ ማሳወቅ ====================
    
    # ቦቱ ሲጀመር ለአስተዳዳሪዎች ማሳወቅ
    @bot.message_handler(commands=['start'], func=lambda m: m.from_user.id in db.get_admin_ids())
    def admin_start_notification(message: Message):
        """አስተዳዳሪ ሲጀምር ማሳወቅ"""
        user_id = message.from_user.id
        bot.send_message(
            user_id,
            "🔐 *የአስተዳዳሪ ፓነል ተዘጋጅቷል!*\n\n"
            "⚙️ /admin - ወደ አስተዳዳሪ ፓነል\n"
            "📊 /stats - ስታቲስቲክስ ለማየት\n"
            "📋 /orders - ትዕዛዞችን ለማስተዳደር\n"
            "📦 /products - ምርቶችን ለማስተዳደር\n"
            "👥 /users - ተጠቃሚዎችን ለማስተዳደር",
            parse_mode='Markdown'
        )


# ==================== ተጨማሪ ትዕዛዞች ====================

def register_additional_commands(bot: TeleBot, db: Database):
    """ተጨማሪ ትዕዛዞችን መመዝገብ"""
    
    @bot.message_handler(commands=['profile'])
    def profile_command(message: Message):
        """የ /profile ትዕዛዝ - መገለጫ ማሳየት"""
        from handlers.user import show_user_profile
        show_user_profile(message, db, bot)
    
    @bot.message_handler(commands=['orders'])
    def orders_command(message: Message):
        """የ /orders ትዕዛዝ - ትዕዛዞችን ማሳየት"""
        from handlers.orders import show_user_orders
        show_user_orders(message, db, bot)
    
    @bot.message_handler(commands=['cart'])
    def cart_command(message: Message):
        """የ /cart ትዕዛዝ - ጋሪ ማሳየት"""
        from handlers.orders import show_cart
        show_cart(message, db, bot)
    
    @bot.message_handler(commands=['lang'])
    def lang_command(message: Message):
        """የ /lang ትዕዛዝ - ቋንቋ መቀየር"""
        markup = get_language_menu()
        bot.send_message(
            message.chat.id,
            "🌍 ቋንቋ ይምረጡ / Choose Language:",
            reply_markup=markup
        )
    
    @bot.message_handler(commands=['admin'])
    def admin_command(message: Message):
        """የ /admin ትዕዛዝ - የአስተዳዳሪ ፓነል"""
        from handlers.admin import show_admin_panel
        show_admin_panel(message, db, bot)
    
    @bot.message_handler(commands=['stats'])
    def stats_command(message: Message):
        """የ /stats ትዕዛዝ - ስታቲስቲክስ ማሳየት"""
        from handlers.admin import show_stats
        show_stats(message, db, bot)
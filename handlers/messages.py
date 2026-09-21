# -*- coding: utf-8 -*-

"""
ዘናጭ ቦት - የመልዕክት እጅ አያያዝ
ይህ ፋይል ሁሉንም የመደበኛ መልዕክቶች እጅ አያያዝን ይይዛል
"""

import logging
import re
from typing import Optional
from datetime import datetime

from telebot import TeleBot
from telebot.types import Message, ReplyKeyboardMarkup, KeyboardButton

from database import Database
from utils.helpers import get_text, get_user_lang
from keyboards.reply import get_main_menu, get_admin_menu
from handlers.products import show_products_by_category
from handlers.user import show_user_profile
from handlers.orders import show_user_orders, show_cart
from services.notifications import toggle_subscription

logger = logging.getLogger(__name__)


def register(bot: TeleBot, db: Database):
    """የመልዕክት እጅ አያያዞችን መመዝገብ"""
    
    # ==================== ሁሉንም መልዕክቶች አያያዝ ====================
    
    @bot.message_handler(func=lambda message: True, content_types=['text'])
    def handle_text_messages(message: Message):
        """ሁሉንም የጽሁፍ መልዕክቶች አያያዝ"""
        user_id = message.from_user.id
        text = message.text
        lang = get_user_lang(db, user_id)
        
        # የተጠቃሚ እንቅስቃሴ መመዝገብ
        db.log_activity(user_id, 'message', f'ተጠቃሚ: {text[:50]}')
        
        # የአስተዳዳሪ ሜኑ
        if text in ['⚙️ አስተዳደር', '⚙️ Admin', 'አስተዳደር ⚙️', 'Admin ⚙️']:
            from handlers.admin import show_admin_panel
            show_admin_panel(message, db, bot)
            return
        
        # የምርት ምድቦች
        if text in ['👕 የወንድ ልብሶች', '👕 Men\'s Clothing', 'የወንድ ልብሶች 👕', 'Men\'s Clothing 👕']:
            show_products_by_category(message, 'Men', db, bot)
            return
        
        if text in ['👗 የሴት ልብሶች', '👗 Women\'s Clothing', 'የሴት ልብሶች 👗', 'Women\'s Clothing 👗']:
            show_products_by_category(message, 'Women', db, bot)
            return
        
        # ትዕዛዞች
        if text in ['📋 ትዕዛዞቼ', '📋 My Orders', 'ትዕዛዞቼ 📋', 'My Orders 📋']:
            show_user_orders(message, db, bot)
            return
        
        # ጋሪ
        if text in ['🛒 ጋሪ', '🛒 Cart', 'ጋሪ 🛒', 'Cart 🛒']:
            show_cart(message, db, bot)
            return
        
        # መገለጫ
        if text in ['👤 መገለጫ', '👤 Profile', 'መገለጫ 👤', 'Profile 👤']:
            show_user_profile(message, db, bot)
            return
        
        # አድራሻ
        if text in ['📍 አድራሻ', '📍 Address', 'አድራሻ እና ስልክ 📍', 'Address & Phone 📍']:
            show_contact_info(message, db, bot)
            return
        
        # ማስታወቂያ
        if text in ['📢 ለማስታወቂያ ተመዝገብ', '📢 Subscribe', 'ለማስታወቂያ ተመዝገብ 📢', 'Subscribe 📢']:
            toggle_subscription(message, db, bot, subscribe=True)
            return
        
        if text in ['🔕 ከማስታወቂያ ተመዝገብ', '🔕 Unsubscribe', 'ከማስታወቂያ ተመዝገብ 🔕', 'Unsubscribe 🔕']:
            toggle_subscription(message, db, bot, subscribe=False)
            return
        
        # ሌላ መልዕክት
        handle_other_messages(message, db, bot)
    
    # ==================== የፎቶ እጅ አያያዝ ====================
    
    @bot.message_handler(content_types=['photo'])
    def handle_photo_messages(message: Message):
        """የፎቶ መልዕክቶች አያያዝ"""
        user_id = message.from_user.id
        
        # ተጠቃሚ በአስተዳዳሪ ሁነታ ላይ መሆኑን ማረጋገጥ
        from handlers.admin import is_admin_uploading
        if is_admin_uploading(user_id):
            from handlers.admin import handle_admin_photo
            handle_admin_photo(message, db, bot)
            return
        
        # መደበኛ የፎቶ መልዕክት
        db.log_activity(user_id, 'photo', 'ፎቶ ልኳል')
        bot.reply_to(message, "📸 ፎቶዎ ተቀብያለሁ! በቅርቡ እንመለከተዋለን.")
    
    # ==================== ሌሎች የመልዕክት አይነቶች ====================
    
    @bot.message_handler(content_types=['document'])
    def handle_document_messages(message: Message):
        """የዶክመንት መልዕክቶች አያያዝ"""
        user_id = message.from_user.id
        db.log_activity(user_id, 'document', 'ዶክመንት ልኳል')
        bot.reply_to(message, "📄 ዶክመንትዎ ተቀብያለሁ!")
    
    @bot.message_handler(content_types=['contact'])
    def handle_contact_messages(message: Message):
        """የእውቂያ መልዕክቶች አያያዝ"""
        user_id = message.from_user.id
        contact = message.contact
        
        if contact:
            # የስልክ ቁጥር ማስቀመጥ
            phone = contact.phone_number
            db.update_user(user_id, phone=phone)
            db.log_activity(user_id, 'contact', f'ስልክ: {phone}')
            
            bot.reply_to(
                message,
                f"✅ የስልክ ቁጥርዎ {phone} ተመዝግቧል! 🙏"
            )
    
    @bot.message_handler(content_types=['location'])
    def handle_location_messages(message: Message):
        """የመገኛ መልዕክቶች አያያዝ"""
        user_id = message.from_user.id
        location = message.location
        
        if location:
            db.log_activity(
                user_id, 
                'location', 
                f'Lat: {location.latitude}, Lon: {location.longitude}'
            )
            bot.reply_to(
                message,
                f"📍 መገኛዎ ተቀብያለሁ!\n"
                f"🗺️ ኬክሮስ: {location.latitude}\n"
                f"🗺️ ኬንትሮስ: {location.longitude}"
            )
    
    # ==================== ረዳት ተግባራት ====================
    
    def show_contact_info(message: Message, db: Database, bot: TeleBot):
        """የአድራሻ መረጃ ማሳየት"""
        lang = get_user_lang(db, message.from_user.id)
        
        contact_msg = get_text(lang, 'contact_info')
        
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add(KeyboardButton(get_text(lang, 'back')))
        
        bot.send_message(
            message.chat.id,
            contact_msg,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    
    def handle_other_messages(message: Message, db: Database, bot: TeleBot):
        """ሌሎች መልዕክቶችን አያያዝ"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        text = message.text
        
        # የተወሰኑ ቁልፍ ቃላት
        keywords = {
            'hi': get_text(lang, 'greeting'),
            'hello': get_text(lang, 'greeting'),
            'እንዴት': get_text(lang, 'how_are_you'),
            'አመሰግናለሁ': get_text(lang, 'thank_you_response'),
            'thank you': get_text(lang, 'thank_you_response'),
            'bye': get_text(lang, 'bye_response'),
            'ሰላም': get_text(lang, 'greeting'),
        }
        
        # ቁልፍ ቃል መፈተሽ
        for key, response in keywords.items():
            if key.lower() in text.lower():
                bot.reply_to(message, response)
                return
        
        # ቅናሽ ኮድ መፈተሽ
        discount_pattern = r'^[A-Z0-9]{5,20}$'
        if re.match(discount_pattern, text.upper()):
            from handlers.orders import apply_discount_code
            apply_discount_code(message, text.upper(), db, bot)
            return
        
        # የምርት ፍለጋ
        if len(text) > 2:
            from handlers.products import search_products
            search_products(message, text, db, bot)
            return
        
        # ነባሪ መልስ
        bot.reply_to(
            message,
            f"❓ እባክዎ ከሜኑ አዝራሮች ይምረጡ.\n\n"
            f"💡 እርዳታ ከፈለጉ /help ይጫኑ"
        )
    
    # ==================== ስህተት አያያዝ ====================
    
    @bot.message_handler(content_types=['voice', 'video', 'audio', 'sticker'])
    def handle_other_content_types(message: Message):
        """ሌሎች የመልዕክት አይነቶች አያያዝ"""
        user_id = message.from_user.id
        content_type = message.content_type
        
        db.log_activity(user_id, content_type, f'የ{content_type} መልዕክት ልኳል')
        
        # ለአስተዳዳሪ ማሳወቅ
        from services.notifications import notify_admin
        notify_admin(
            bot,
            f"📨 አዲስ {content_type} መልዕክት\n"
            f"👤 ተጠቃሚ: {message.from_user.first_name}\n"
            f"🆔 ID: {user_id}"
        )
        
        bot.reply_to(
            message,
            f"📨 መልዕክትዎ ተቀብያለሁ! "
            f"በቅርቡ እንመለከተዋለን. 🙏"
        )
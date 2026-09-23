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
from utils.helpers import format_currency

logger = logging.getLogger(__name__)


def toggle_subscription(message: Message, db: Database, bot: TeleBot, subscribe: bool):
    """Update notification subscription from the reply keyboard."""
    user_id = message.from_user.id
    status = 1 if subscribe else 0
    db.update_user(user_id, is_subscribed=status)
    db.log_activity(user_id, 'toggle_subscription', f'አዲስ ሁኔታ: {status}')
    lang = get_user_lang(db, user_id)
    key = 'subscribed' if subscribe else 'unsubscribed'
    bot.send_message(
        message.chat.id,
        f"✅ {get_text(lang, 'subscription')}: {get_text(lang, key)}"
    )


def show_products_by_category(message: Message, category: str, db: Database, bot: TeleBot):
    """Display products selected from the reply keyboard."""
    lang = get_user_lang(db, message.from_user.id)
    products = db.get_products(category=category, limit=20, offset=0)
    if not products:
        bot.send_message(message.chat.id, get_text(lang, 'no_products_in_category'))
        return []

    lines = [f"📦 {get_text(lang, category.lower())}", '']
    for product in products[:10]:
        name = product.get('name_am') if lang == 'am' else product.get('name_en')
        lines.append(f"• {name or product.get('name_am', 'N/A')} - {format_currency(product.get('price', 0))}")
        lines.append(f"  /product {product['id']}")
    bot.send_message(message.chat.id, '\n'.join(lines))
    return products


def show_user_orders(message: Message, db: Database, bot: TeleBot):
    """Display the current user's recent orders."""
    orders = db.get_user_orders(message.from_user.id, limit=10)
    if not orders:
        bot.send_message(message.chat.id, "📋 እስካሁን ትዕዛዝ የለዎትም።")
        return []
    text = '\n'.join(
        f"• {order.get('order_number', order.get('id', 'N/A'))} - {order.get('status', 'N/A')} - {format_currency(order.get('final_amount', 0))}"
        for order in orders
    )
    bot.send_message(message.chat.id, f"📋 ትዕዛዞቼ\n\n{text}")
    return orders


def show_cart(message: Message, db: Database, bot: TeleBot):
    """Display the current user's cart."""
    cart = db.get_cart(message.from_user.id)
    items = cart.get('items', []) if cart else []
    if not items:
        bot.send_message(message.chat.id, "🛒 ጋሪዎ ባዶ ነው።")
        return []
    text = '\n'.join(
        f"• {item.get('name', 'N/A')} x{item.get('quantity', 0)} - {format_currency(item.get('price', 0))}"
        for item in items
    )
    bot.send_message(message.chat.id, f"🛒 ጋሪ\n\n{text}")
    return items


def show_user_profile(message: Message, db: Database, bot: TeleBot):
    """Display a compact user profile."""
    user = db.get_user(message.from_user.id)
    if not user:
        bot.send_message(message.chat.id, "👤 መገለጫዎ አልተገኘም።")
        return None
    text = (
        f"👤 መገለጫ\n\n"
        f"📝 ስም: {user.get('first_name', '')} {user.get('last_name', '')}\n"
        f"🔹 Username: @{user.get('username') or 'N/A'}\n"
        f"📱 ስልክ: {user.get('phone') or 'N/A'}"
    )
    bot.send_message(message.chat.id, text)
    return user


def show_admin_panel(message: Message, db: Database, bot: TeleBot):
    """Display the admin keyboard for an admin user."""
    from config import config
    if message.from_user.id not in config.bot.ADMIN_IDS:
        bot.send_message(message.chat.id, "⛔ ይህን ክፍል ለመጠቀም ፈቃድ የለዎትም።")
        return False
    bot.send_message(message.chat.id, "⚙️ የአስተዳዳሪ ፓነል", reply_markup=get_admin_menu(message.from_user.id, get_user_lang(db, message.from_user.id)))
    return True


def register_handlers(bot: TeleBot, db: Database):
    """Package-level API expected by main.py."""
    from handlers import start, products, orders, payments, user, admin, callback

    # Register specific handlers before messages.py's catch-all text handler.
    for module in (start, products, orders, payments, user, admin, callback):
        module.register(bot, db)
    register(bot, db)


def register(bot: TeleBot, db: Database):
    """የመልዕክት እጅ አያያዞችን መመዝገብ"""
    
    # ==================== ሁሉንም መልዕክቶች አያያዝ ====================
    
    @bot.message_handler(func=lambda message: True, content_types=['text'])
    def handle_text_messages(message: Message):
        """ሁሉንም የጽሁፍ መልዕክቶች አያያዝ"""
        user_id = message.from_user.id
        text = message.text
        lang = get_user_lang(db, user_id)

        if not db.get_user(user_id):
            db.create_user(
                user_id=user_id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                lang='am'
            )

        # ለአስተዳዳሪ የምርት መጨመር ተራ እውቅና ያለው ግብዓት በእውነተኛ ሂደት እንዲተካ ይደረጋል
        try:
            from handlers.admin import admin_states, route_admin_product_step
            if user_id in admin_states and admin_states[user_id].get('action') == 'add_product':
                if route_admin_product_step(message, db, bot):
                    return
        except Exception:
            pass

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
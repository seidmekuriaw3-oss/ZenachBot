# -*- coding: utf-8 -*-

"""
ዘናጭ ቦት - የአስተዳዳሪ ፓነል እጅ አያያዝ
ይህ ፋይል ሁሉንም የአስተዳዳሪ ፓነል እጅ አያያዞችን ይይዛል
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List

from telebot import TeleBot
from telebot.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

from database import Database
from config import config
from utils.helpers import get_text, get_user_lang, format_number, format_currency, is_admin
from keyboards.inline import get_admin_keyboard, get_confirm_keyboard
from services.notifications import notify_admins, send_broadcast

logger = logging.getLogger(__name__)

# ለአስተዳዳሪ ሂደቶች ጊዜያዊ መረጃ
admin_states = {}
admin_uploading = set()


def route_admin_product_step(message: Message, db: Database, bot: TeleBot):
    """Route an admin input through the active add-product state machine."""
    user_id = message.from_user.id
    state = admin_states.get(user_id)
    if not state or state.get('action') != 'add_product':
        return False

    step = state.get('step', 1)
    router = {
        1: process_add_product_name,
        2: process_add_product_name_en,
        3: process_add_product_price,
        4: process_add_product_size,
        5: process_add_product_category,
        6: process_add_product_stock,
        7: process_add_product_image,
    }
    func = router.get(step)
    if func:
        func(message, db, bot)
        return True
    return False


def start_add_product(message: Message, db: Database, bot: TeleBot):
    """አዲስ ምርት መጨመር ሂደት መጀመር"""
    user_id = message.from_user.id
    admin_states[user_id] = {'action': 'add_product', 'step': 1, 'data': {}}

    bot.send_message(
        message.chat.id,
        "📝 *አዲስ ምርት መጨመር*\n\n"
        "የምርቱን ስም በአማርኛ ያስገቡ:",
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(message, process_add_product_name, db, bot)


def process_add_product_name(message: Message, db: Database, bot: TeleBot):
    """የምርት ስም በአማርኛ ማስኬድ"""
    user_id = message.from_user.id
    admin_states[user_id]['data']['name_am'] = message.text
    admin_states[user_id]['step'] = 2

    bot.send_message(
        message.chat.id,
        "📝 የምርቱን ስም በእንግሊዝኛ ያስገቡ:"
    )
    bot.register_next_step_handler(message, process_add_product_name_en, db, bot)


def process_add_product_name_en(message: Message, db: Database, bot: TeleBot):
    """የምርት ስም በእንግሊዝኛ ማስኬድ"""
    user_id = message.from_user.id
    admin_states[user_id]['data']['name_en'] = message.text
    admin_states[user_id]['step'] = 3

    bot.send_message(
        message.chat.id,
        "💰 የምርቱን ዋጋ በብር ያስገቡ:"
    )
    bot.register_next_step_handler(message, process_add_product_price, db, bot)


def process_add_product_price(message: Message, db: Database, bot: TeleBot):
    """የምርት ዋጋ ማስኬድ"""
    user_id = message.from_user.id

    try:
        price = float(message.text)
        admin_states[user_id]['data']['price'] = price
        admin_states[user_id]['step'] = 4

        bot.send_message(
            message.chat.id,
            "📏 የምርቱን መጠን (Size) ያስገቡ (S, M, L, XL, XXL):"
        )
        bot.register_next_step_handler(message, process_add_product_size, db, bot)
    except ValueError:
        bot.send_message(
            message.chat.id,
            "❌ እባክዎ ትክክለኛ ቁጥር ያስገቡ!"
        )
        bot.register_next_step_handler(message, process_add_product_price, db, bot)


def process_add_product_size(message: Message, db: Database, bot: TeleBot):
    """የምርት መጠን ማስኬድ"""
    user_id = message.from_user.id
    admin_states[user_id]['data']['size'] = message.text.upper()
    admin_states[user_id]['step'] = 5

    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
    markup.add("Men", "Women", "Accessories")

    bot.send_message(
        message.chat.id,
        "📂 የምርቱን ምድብ ይምረጡ:",
        reply_markup=markup
    )
    bot.register_next_step_handler(message, process_add_product_category, db, bot)


def process_add_product_category(message: Message, db: Database, bot: TeleBot):
    """የምርት ምድብ ማስኬድ"""
    user_id = message.from_user.id

    if message.text not in ['Men', 'Women', 'Accessories']:
        bot.send_message(
            message.chat.id,
            "❌ እባክዎ ከላይ ካሉት ይምረጡ!"
        )
        bot.register_next_step_handler(message, process_add_product_category, db, bot)
        return

    admin_states[user_id]['data']['category'] = message.text
    admin_states[user_id]['step'] = 6

    bot.send_message(
        message.chat.id,
        "📦 የምርቱን የክምችት ብዛት ያስገቡ:"
    )
    admin_uploading.clear()
    bot.register_next_step_handler(message, process_add_product_stock, db, bot)


def process_add_product_stock(message: Message, db: Database, bot: TeleBot):
    """የምርት ክምችት ማስኬድ"""
    user_id = message.from_user.id

    try:
        stock = int(message.text)
        admin_states[user_id]['data']['stock_quantity'] = stock
        admin_states[user_id]['step'] = 7

        bot.send_message(
            message.chat.id,
            "📸 የምርቱን ፎቶ ይላኩ:"
        )
        admin_uploading.add(user_id)
        bot.register_next_step_handler(message, process_add_product_image, db, bot)
    except ValueError:
        bot.send_message(
            message.chat.id,
            "❌ እባክዎ ትክክለኛ ቁጥር ያስገቡ!"
        )
        bot.register_next_step_handler(message, process_add_product_stock, db, bot)


def process_add_product_image(message: Message, db: Database, bot: TeleBot):
    """የምርት ፎቶ ማስኬድ"""
    user_id = message.from_user.id

    if message.content_type != 'photo':
        bot.send_message(
            message.chat.id,
            "❌ እባክዎ ፎቶ ይላኩ!"
        )
        bot.register_next_step_handler(message, process_add_product_image, db, bot)
        return

    admin_uploading.discard(user_id)
    image_id = message.photo[-1].file_id
    data = admin_states[user_id]['data']

    product_data = {
        'name_am': data['name_am'],
        'name_en': data['name_en'],
        'price': data['price'],
        'size': data['size'],
        'category': data['category'],
        'image_id': image_id,
        'stock_quantity': data['stock_quantity'],
        'status': 'In Stock'
    }

    product_id = db.create_product(product_data)

    if product_id:
        notify_admins(
            bot,
            f"🆕 *አዲስ ምርት ተጨምሯል!*\n\n"
            f"📦 {data['name_am']}\n"
            f"💰 ዋጋ: {data['price']:.2f} ETB\n"
            f"📏 መጠን: {data['size']}\n"
            f"📂 ምድብ: {data['category']}\n"
            f"📦 ክምችት: {data['stock_quantity']}\n"
            f"🆔 ID: {product_id}"
        )

        bot.send_message(
            message.chat.id,
            f"✅ ምርቱ \"{data['name_am']}\" በተሳካ ሁኔታ ተጨምሯል!\n"
            f"🆔 የምርት ID: {product_id}"
        )

        db.log_activity(user_id, 'add_product',
                      f"ምርት: {data['name_am']}, ID: {product_id}")
    else:
        bot.send_message(
            message.chat.id,
            "❌ ምርቱ መጨመር አልተቻለም!"
        )

    admin_states.pop(user_id, None)
    show_admin_panel(message)


def is_admin_uploading(user_id: int) -> bool:
    """Check whether an admin is currently waiting for a photo upload."""
    return user_id in admin_uploading


def handle_admin_photo(message: Message, db: Database, bot: TeleBot):
    """Handle a photo uploaded during an admin workflow such as add-product."""
    user_id = message.from_user.id
    if not is_admin_uploading(user_id):
        return False

    admin_uploading.discard(user_id)
    state = admin_states.get(user_id)
    if not state or state.get('action') != 'add_product':
        bot.reply_to(message, "📸 ፎቶዎ ተቀብሏል።")
        return True

    try:
        image_id = message.photo[-1].file_id if message.photo else None
        if not image_id:
            bot.send_message(message.chat.id, "❌ እባክዎ ትክክለኛ ፎቶ ይላኩ!")
            return False

        data = state.get('data', {})
        product_data = {
            'name_am': data.get('name_am'),
            'name_en': data.get('name_en'),
            'price': data.get('price'),
            'size': data.get('size'),
            'category': data.get('category'),
            'image_id': image_id,
            'stock_quantity': data.get('stock_quantity', 0),
            'status': 'In Stock'
        }

        product_id = db.create_product(product_data)
        if product_id:
            notify_admins(
                bot,
                f"🆕 *አዲስ ምርት ተጨምሯል!*\n\n"
                f"📦 {data.get('name_am')}\n"
                f"💰 ዋጋ: {data.get('price'):.2f} ETB\n"
                f"📏 መጠን: {data.get('size')}\n"
                f"📂 ምድብ: {data.get('category')}\n"
                f"📦 ክምችት: {data.get('stock_quantity')}\n"
                f"🆔 ID: {product_id}"
            )
            bot.send_message(
                message.chat.id,
                f"✅ ምርቱ \"{data.get('name_am')}\" በተሳካ ሁኔታ ተጨምሯል!\n"
                f"🆔 የምርት ID: {product_id}"
            )
            db.log_activity(user_id, 'add_product', f"ምርት: {data.get('name_am')}, ID: {product_id}")
        else:
            bot.send_message(message.chat.id, "❌ ምርቱ መጨመር አልተቻለልም!")

        admin_states.pop(user_id, None)
        return True
    except Exception as exc:
        logger.exception(f"ምርት ፎቶ ማስተካከል አልተቻለም: {exc}")
        bot.send_message(message.chat.id, "❌ ፎቶውን ማስተካከል አልተቻለም።")
        admin_states.pop(user_id, None)
        return False


def register(bot: TeleBot, db: Database):
    """የአስተዳዳሪ እጅ አያያዞችን መመዝገብ"""
    
    # ==================== የአስተዳዳሪ ፓነል ====================
    
    @bot.message_handler(func=lambda m: m.text in ['⚙️ አስተዳደር', '⚙️ Admin', 'አስተዳደር ⚙️', 'Admin ⚙️'])
    def show_admin_panel(message: Message):
        """የአስተዳዳሪ ፓነል ማሳየት"""
        user_id = message.from_user.id
        
        if not is_admin(user_id, config.bot.ADMIN_IDS):
            bot.reply_to(message, "⛔ ይህን ለማድረግ ፈቃድ የለዎትም!")
            return
        
        lang = get_user_lang(db, user_id)
        
        # ስታቲስቲክስ ማግኘት
        stats = get_admin_stats(db)

        # አስተዳዳሪ የሚገባ ግብዓት በድርድር ሁኔታ እንዳይተኛ ይቆጣጠራል
        if user_id in admin_states and admin_states[user_id].get('action') == 'add_product':
            route_admin_product_step(message, db, bot)
            return

        msg = f"⚙️ *የአስተዳዳሪ ፓነል*\n\n"
        msg += f"👥 ተጠቃሚዎች: {stats['total_users']}\n"
        msg += f"📦 ምርቶች: {stats['total_products']}\n"
        msg += f"📋 ትዕዛዞች: {stats['total_orders']}\n"
        msg += f"⏳ በመጠባበቅ: {stats['pending_orders']}\n"
        msg += f"💰 ገቢ: {format_currency(stats['total_revenue'])}\n"
        msg += f"📅 ዛሬ: {stats['today_orders']} ትዕዛዞች\n\n"
        msg += f"📌 ከታች ካሉት አዝራሮች ይምረጡ:"
        
        markup = get_admin_menu(user_id, lang)
        
        bot.send_message(
            message.chat.id,
            msg,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    
    # ==================== የምርት አስተዳደር ====================
    
    @bot.message_handler(func=lambda m: m.text in ['📦 ምርቶች', '📦 Products'])
    def manage_products(message: Message):
        """የምርት አስተዳደር ሜኑ"""
        user_id = message.from_user.id
        
        if not is_admin(user_id, config.bot.ADMIN_IDS):
            return
        
        lang = get_user_lang(db, user_id)
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("➕ አዲስ ምርት", callback_data="admin_add_product"),
            InlineKeyboardButton("📋 ምርቶች አሳይ", callback_data="admin_list_products"),
            InlineKeyboardButton("✏️ ምርት አስተካክል", callback_data="admin_edit_product"),
            InlineKeyboardButton("🗑️ ምርት ሰርዝ", callback_data="admin_delete_product"),
            InlineKeyboardButton("📊 ዝቅተኛ ክምችት", callback_data="admin_low_stock"),
            InlineKeyboardButton("🔙 ወደኋላ", callback_data="admin_back")
        )
        
        bot.send_message(
            message.chat.id,
            "📦 *የምርት አስተዳደር*\n\nእባክዎ የሚፈልጉትን ይምረጡ:",
            reply_markup=markup,
            parse_mode='Markdown'
        )
    
    # ==================== የትዕዛዝ አስተዳደር ====================
    
    @bot.message_handler(func=lambda m: m.text in ['📋 ትዕዛዞች', '📋 Orders'])
    def manage_orders(message: Message):
        """የትዕዛዝ አስተዳደር ሜኑ"""
        user_id = message.from_user.id
        
        if not is_admin(user_id, config.bot.ADMIN_IDS):
            return
        
        lang = get_user_lang(db, user_id)
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("📋 ሁሉንም ትዕዛዞች", callback_data="admin_all_orders"),
            InlineKeyboardButton("⏳ በመጠባበቅ", callback_data="admin_pending_orders"),
            InlineKeyboardButton("📦 በሂደት", callback_data="admin_processing_orders"),
            InlineKeyboardButton("🚚 የተላኩ", callback_data="admin_shipped_orders"),
            InlineKeyboardButton("✅ የተጠናቀቁ", callback_data="admin_completed_orders"),
            InlineKeyboardButton("🔙 ወደኋላ", callback_data="admin_back")
        )
        
        bot.send_message(
            message.chat.id,
            "📋 *የትዕዛዝ አስተዳደር*\n\nእባክዎ የሚፈልጉትን ይምረጡ:",
            reply_markup=markup,
            parse_mode='Markdown'
        )
    
    # ==================== የተጠቃሚ አስተዳደር ====================
    
    @bot.message_handler(func=lambda m: m.text in ['👥 ተጠቃሚዎች', '👥 Users'])
    def manage_users(message: Message):
        """የተጠቃሚ አስተዳደር ሜኑ"""
        user_id = message.from_user.id
        
        if not is_admin(user_id, config.bot.ADMIN_IDS):
            return
        
        lang = get_user_lang(db, user_id)
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("👥 ሁሉንም ተጠቃሚዎች", callback_data="admin_all_users"),
            InlineKeyboardButton("📊 ንቁ ተጠቃሚዎች", callback_data="admin_active_users"),
            InlineKeyboardButton("📢 ማስታወቂያ ላክ", callback_data="admin_broadcast"),
            InlineKeyboardButton("👤 ተጠቃሚ ፈልግ", callback_data="admin_find_user"),
            InlineKeyboardButton("🔙 ወደኋላ", callback_data="admin_back")
        )
        
        bot.send_message(
            message.chat.id,
            "👥 *የተጠቃሚ አስተዳደር*\n\nእባክዎ የሚፈልጉትን ይምረጡ:",
            reply_markup=markup,
            parse_mode='Markdown'
        )
    
    # ==================== ሪፖርቶች ====================
    
    @bot.message_handler(func=lambda m: m.text in ['📊 ሪፖርቶች', '📊 Reports'])
    def show_reports(message: Message):
        """የሪፖርት ሜኑ"""
        user_id = message.from_user.id
        
        if not is_admin(user_id, config.bot.ADMIN_IDS):
            return
        
        lang = get_user_lang(db, user_id)
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("📊 የሽያጭ ሪፖርት", callback_data="admin_sales_report"),
            InlineKeyboardButton("🏆 ከፍተኛ ምርቶች", callback_data="admin_top_products"),
            InlineKeyboardButton("📈 ዕለታዊ ሪፖርት", callback_data="admin_daily_report"),
            InlineKeyboardButton("📊 የምድብ ሪፖርት", callback_data="admin_category_report"),
            InlineKeyboardButton("🔙 ወደኋላ", callback_data="admin_back")
        )
        
        bot.send_message(
            message.chat.id,
            "📊 *የሪፖርት ሜኑ*\n\nእባክዎ የሚፈልጉትን ይምረጡ:",
            reply_markup=markup,
            parse_mode='Markdown'
        )
    
    # ==================== የቅናሽ አስተዳደር ====================
    
    @bot.message_handler(func=lambda m: m.text in ['🏷️ ቅናሾች', '🏷️ Discounts'])
    def manage_discounts(message: Message):
        """የቅናሽ አስተዳደር ሜኑ"""
        user_id = message.from_user.id
        
        if not is_admin(user_id, config.bot.ADMIN_IDS):
            return
        
        lang = get_user_lang(db, user_id)
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("➕ አዲስ ቅናሽ", callback_data="admin_add_discount"),
            InlineKeyboardButton("📋 ሁሉንም ቅናሾች", callback_data="admin_list_discounts"),
            InlineKeyboardButton("🔙 ወደኋላ", callback_data="admin_back")
        )
        
        bot.send_message(
            message.chat.id,
            "🏷️ *የቅናሽ አስተዳደር*\n\nእባክዎ የሚፈልጉትን ይምረጡ:",
            reply_markup=markup,
            parse_mode='Markdown'
        )
    
    # ==================== የአስተዳዳሪ መልእክት ማስተናገጃ ====================
    
    # ከዚህ በታች የ Callback እጅ አያያዞች
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
    def handle_admin_callbacks(call: CallbackQuery):
        """የአስተዳዳሪ ጥሪ እጅ አያያዝ"""
        user_id = call.from_user.id
        
        if not is_admin(user_id, config.bot.ADMIN_IDS):
            bot.answer_callback_query(call.id, "⛔ ፈቃድ የለዎትም!")
            return
        
        data = call.data
        lang = get_user_lang(db, user_id)
        
        # ወደኋላ
        if data == 'admin_back':
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            show_admin_panel(call.message)
            return
        
        # ምርት መጨመር
        elif data == 'admin_add_product':
            start_add_product(call.message, db, bot)
        
        # ምርቶች መዘርዘር
        elif data == 'admin_list_products':
            list_products(call.message, db, bot)
        
        # ምርት ማስተካከል
        elif data == 'admin_edit_product':
            start_edit_product(call.message, db, bot)
        
        # ምርት መሰረዝ
        elif data == 'admin_delete_product':
            start_delete_product(call.message, db, bot)
        
        # ዝቅተኛ ክምችት
        elif data == 'admin_low_stock':
            show_low_stock(call.message, db, bot)
        
        # ትዕዛዞች
        elif data == 'admin_all_orders':
            show_orders_by_status(call.message, None, db, bot)
        elif data == 'admin_pending_orders':
            show_orders_by_status(call.message, 'Pending', db, bot)
        elif data == 'admin_processing_orders':
            show_orders_by_status(call.message, 'Processing', db, bot)
        elif data == 'admin_shipped_orders':
            show_orders_by_status(call.message, 'Shipped', db, bot)
        elif data == 'admin_completed_orders':
            show_orders_by_status(call.message, 'Delivered', db, bot)
        
        # ተጠቃሚዎች
        elif data == 'admin_all_users':
            show_all_users(call.message, db, bot)
        elif data == 'admin_active_users':
            show_active_users(call.message, db, bot)
        elif data == 'admin_broadcast':
            start_broadcast(call.message, db, bot)
        elif data == 'admin_find_user':
            start_find_user(call.message, db, bot)
        
        # ሪፖርቶች
        elif data == 'admin_sales_report':
            show_sales_report(call.message, db, bot)
        elif data == 'admin_top_products':
            show_top_products(call.message, db, bot)
        elif data == 'admin_daily_report':
            show_daily_report(call.message, db, bot)
        elif data == 'admin_category_report':
            show_category_report(call.message, db, bot)
        
        # ቅናሾች
        elif data == 'admin_add_discount':
            start_add_discount(call.message, db, bot)
        elif data == 'admin_list_discounts':
            list_discounts(call.message, db, bot)
        
        bot.answer_callback_query(call.id)
    
    # ==================== ረዳት ተግባራት ====================
    
    def get_admin_menu(user_id: int, lang: str) -> ReplyKeyboardMarkup:
        """የአስተዳዳሪ ሜኑ መፍጠር"""
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        
        buttons = [
            "📦 ምርቶች",
            "📋 ትዕዛዞች",
            "👥 ተጠቃሚዎች",
            "📊 ሪፖርቶች",
            "🏷️ ቅናሾች",
            "⚙️ ቅንብሮች",
            "🔙 ወደ መጀመሪያ"
        ]
        
        markup.add(*[KeyboardButton(btn) for btn in buttons])
        return markup
    
    def get_admin_stats(db: Database) -> Dict:
        """የአስተዳዳሪ ስታቲስቲክስ ማግኘት"""
        try:
            # ጠቅላላ ስታቲስቲክስ
            total_users = db.get_user_count()
            total_products = db.get_product_count()
            
            # ትዕዛዝ ስታቲስቲክስ
            order_stats = db.get_order_stats()
            
            total_orders = order_stats.get('summary', {}).get('total_orders', 0)
            total_revenue = order_stats.get('summary', {}).get('total_revenue', 0)
            pending_orders = order_stats.get('Pending', {}).get('count', 0)
            
            # የዕለት ስታቲስቲክስ
            daily_stats = db.get_daily_stats()
            today_orders = daily_stats.get('new_orders', 0)
            
            return {
                'total_users': total_users,
                'total_products': total_products,
                'total_orders': total_orders,
                'total_revenue': total_revenue,
                'pending_orders': pending_orders,
                'today_orders': today_orders
            }
        except Exception as e:
            logger.error(f"ስታቲስቲክስ ማግኘት አልተቻለም: {e}")
            return {
                'total_users': 0,
                'total_products': 0,
                'total_orders': 0,
                'total_revenue': 0,
                'pending_orders': 0,
                'today_orders': 0
            }
    
    # ==================== ምርት መጨመር ሂደት ====================
    
    def start_add_product(message: Message, db: Database, bot: TeleBot):
        """አዲስ ምርት መጨመር ሂደት መጀመር"""
        user_id = message.from_user.id
        admin_states[user_id] = {'action': 'add_product', 'step': 1, 'data': {}}
        
        bot.send_message(
            message.chat.id,
            "📝 *አዲስ ምርት መጨመር*\n\n"
            "የምርቱን ስም በአማርኛ ያስገቡ:",
            parse_mode='Markdown'
        )
        bot.register_next_step_handler(message, process_add_product_name, db, bot)
    
    def process_add_product_name(message: Message, db: Database, bot: TeleBot):
        """የምርት ስም በአማርኛ ማስኬድ"""
        user_id = message.from_user.id
        admin_states[user_id]['data']['name_am'] = message.text
        admin_states[user_id]['step'] = 2
        
        bot.send_message(
            message.chat.id,
            "📝 የምርቱን ስም በእንግሊዝኛ ያስገቡ:"
        )
        bot.register_next_step_handler(message, process_add_product_name_en, db, bot)
    
    def process_add_product_name_en(message: Message, db: Database, bot: TeleBot):
        """የምርት ስም በእንግሊዝኛ ማስኬድ"""
        user_id = message.from_user.id
        admin_states[user_id]['data']['name_en'] = message.text
        admin_states[user_id]['step'] = 3
        
        bot.send_message(
            message.chat.id,
            "💰 የምርቱን ዋጋ በብር ያስገቡ:"
        )
        bot.register_next_step_handler(message, process_add_product_price, db, bot)
    
    def process_add_product_price(message: Message, db: Database, bot: TeleBot):
        """የምርት ዋጋ ማስኬድ"""
        user_id = message.from_user.id
        
        try:
            price = float(message.text)
            admin_states[user_id]['data']['price'] = price
            admin_states[user_id]['step'] = 4
            
            bot.send_message(
                message.chat.id,
                "📏 የምርቱን መጠን (Size) ያስገቡ (S, M, L, XL, XXL):"
            )
            bot.register_next_step_handler(message, process_add_product_size, db, bot)
        except ValueError:
            bot.send_message(
                message.chat.id,
                "❌ እባክዎ ትክክለኛ ቁጥር ያስገቡ!"
            )
            bot.register_next_step_handler(message, process_add_product_price, db, bot)
    
    def process_add_product_size(message: Message, db: Database, bot: TeleBot):
        """የምርት መጠን ማስኬድ"""
        user_id = message.from_user.id
        admin_states[user_id]['data']['size'] = message.text.upper()
        admin_states[user_id]['step'] = 5
        
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
        markup.add("Men", "Women", "Accessories")
        
        bot.send_message(
            message.chat.id,
            "📂 የምርቱን ምድብ ይምረጡ:",
            reply_markup=markup
        )
        bot.register_next_step_handler(message, process_add_product_category, db, bot)
    
    def process_add_product_category(message: Message, db: Database, bot: TeleBot):
        """የምርት ምድብ ማስኬድ"""
        user_id = message.from_user.id
        
        if message.text not in ['Men', 'Women', 'Accessories']:
            bot.send_message(
                message.chat.id,
                "❌ እባክዎ ከላይ ካሉት ይምረጡ!"
            )
            bot.register_next_step_handler(message, process_add_product_category, db, bot)
            return
        
        admin_states[user_id]['data']['category'] = message.text
        admin_states[user_id]['step'] = 6
        
        bot.send_message(
            message.chat.id,
            "📦 የምርቱን የክምችት ብዛት ያስገቡ:"
        )
        admin_uploading.clear()
        bot.register_next_step_handler(message, process_add_product_stock, db, bot)
    
    def process_add_product_stock(message: Message, db: Database, bot: TeleBot):
        """የምርት ክምችት ማስኬድ"""
        user_id = message.from_user.id
        
        try:
            stock = int(message.text)
            admin_states[user_id]['data']['stock_quantity'] = stock
            admin_states[user_id]['step'] = 7
            
            bot.send_message(
                message.chat.id,
                "📸 የምርቱን ፎቶ ይላኩ:"
            )
            admin_uploading.add(user_id)
            bot.register_next_step_handler(message, process_add_product_image, db, bot)
        except ValueError:
            bot.send_message(
                message.chat.id,
                "❌ እባክዎ ትክክለኛ ቁጥር ያስገቡ!"
            )
            bot.register_next_step_handler(message, process_add_product_stock, db, bot)
    
    def process_add_product_image(message: Message, db: Database, bot: TeleBot):
        """የምርት ፎቶ ማስኬድ"""
        user_id = message.from_user.id
        
        if message.content_type != 'photo':
            bot.send_message(
                message.chat.id,
                "❌ እባክዎ ፎቶ ይላኩ!"
            )
            bot.register_next_step_handler(message, process_add_product_image, db, bot)
            return
        
        admin_uploading.discard(user_id)
        image_id = message.photo[-1].file_id
        data = admin_states[user_id]['data']
        
        # ምርት መፍጠር
        product_data = {
            'name_am': data['name_am'],
            'name_en': data['name_en'],
            'price': data['price'],
            'size': data['size'],
            'category': data['category'],
            'image_id': image_id,
            'stock_quantity': data['stock_quantity'],
            'status': 'In Stock'
        }
        
        product_id = db.create_product(product_data)
        
        if product_id:
            # ለአስተዳዳሪዎች ማሳወቅ
            notify_admins(
                bot,
                f"🆕 *አዲስ ምርት ተጨምሯል!*\n\n"
                f"📦 {data['name_am']}\n"
                f"💰 ዋጋ: {data['price']:.2f} ETB\n"
                f"📏 መጠን: {data['size']}\n"
                f"📂 ምድብ: {data['category']}\n"
                f"📦 ክምችት: {data['stock_quantity']}\n"
                f"🆔 ID: {product_id}"
            )
            
            bot.send_message(
                message.chat.id,
                f"✅ ምርቱ '{data['name_am']}' በተሳካ ሁኔታ ተጨምሯል!\n"
                f"🆔 የምርት ID: {product_id}"
            )
            
            db.log_activity(user_id, 'add_product', 
                          f"ምርት: {data['name_am']}, ID: {product_id}")
        else:
            bot.send_message(
                message.chat.id,
                "❌ ምርቱ መጨመር አልተቻለም!"
            )
        
        # ሁኔታን ማጽዳት
        admin_states.pop(user_id, None)
        show_admin_panel(message)


# ==================== ሌሎች የአስተዳዳሪ ተግባራት ====================

def show_orders_by_status(message: Message, status: Optional[str], db: Database, bot: TeleBot):
    """ትዕዛዞችን በሁኔታ ማሳየት"""
    orders = db.get_orders_by_status(status) if hasattr(db, 'get_orders_by_status') else []
    if not orders:
        bot.send_message(message.chat.id, "📋 ምንም ትዕዛዞች አልተገኙም.")
        return "no orders"

    summary = "\n".join(
        f"• {order.get('order_number', 'N/A')} - {order.get('status', status or 'Unknown')}"
        for order in orders[:10]
    )
    bot.send_message(message.chat.id, f"📋 ትዕዛዞች\n\n{summary}")
    return summary


def show_all_users(message: Message, db: Database, bot: TeleBot):
    """ሁሉንም ተጠቃሚዎች ማሳየት"""
    try:
        users = db.get_all_users(limit=20)
    except TypeError:
        users = db.get_all_users()
    if not users:
        bot.send_message(message.chat.id, "👥 ምንም ተጠቃሚ አልተገኘም.")
        return []

    text = "\n".join(
        f"• {user.get('first_name', 'Unknown')} (@{user.get('username', 'n/a')})"
        for user in users[:10]
    )
    bot.send_message(message.chat.id, f"👥 ተጠቃሚዎች\n\n{text}")
    return users


def show_active_users(message: Message, db: Database, bot: TeleBot):
    """ንቁ ተጠቃሚዎችን ማሳየት"""
    try:
        users = db.get_active_users(days=7)
    except TypeError:
        users = db.get_active_users()
    if not users:
        bot.send_message(message.chat.id, "📊 ንቁ ተጠቃሚ አልተገኘም.")
        return []

    text = "\n".join(
        f"• {user.get('first_name', 'Unknown')} ({user.get('last_active', 'N/A')})"
        for user in users[:10]
    )
    bot.send_message(message.chat.id, f"📊 ንቁ ተጠቃሚዎች\n\n{text}")
    return users


def start_broadcast(message: Message, db: Database, bot: TeleBot):
    """ማስታወቂያ መላክ ሂደት መጀመር"""
    bot.send_message(message.chat.id, "📢 ማስታወቂያ ለመላክ መልእክት ያስገቡ.")
    return "broadcast started"


def start_find_user(message: Message, db: Database, bot: TeleBot):
    """ተጠቃሚ መፈለግ ሂደት መጀመር"""
    bot.send_message(message.chat.id, "👤 የተጠቃሚ መለያ ያስገቡ:")
    return "find user started"


def show_sales_report(message: Message, db: Database, bot: TeleBot):
    """የሽያጭ ሪፖርት ማሳየት"""
    report = db.get_sales_report(days=30)
    if not report:
        bot.send_message(message.chat.id, "📊 ምንም የሽያጭ ሪፖርት አልተገኘም.")
        return []

    text = "\n".join(
        f"• {row.get('sale_date', 'N/A')}: {row.get('total_sales', 0)} ETB"
        for row in report[:10]
    )
    bot.send_message(message.chat.id, f"📊 የሽያጭ ሪፖርት\n\n{text}")
    return report


def show_top_products(message: Message, db: Database, bot: TeleBot):
    """ከፍተኛ ምርቶችን ማሳየት"""
    products = db.get_top_products(limit=5)
    if not products:
        bot.send_message(message.chat.id, "🏆 ምንም ከፍተኛ ምርት አልተገኘም.")
        return []

    text = "\n".join(
        f"• {product.get('name_am', 'N/A')} ({product.get('total_sold', 0)} sold)"
        for product in products
    )
    bot.send_message(message.chat.id, f"🏆 ከፍተኛ ምርቶች\n\n{text}")
    return products


def show_daily_report(message: Message, db: Database, bot: TeleBot):
    """የዕለት ሪፖርት ማሳየት"""
    stats = db.get_daily_stats()
    text = (
        f"📈 አዲስ ተጠቃሚዎች: {stats.get('new_users', 0)}\n"
        f"📦 አዲስ ትዕዛዞች: {stats.get('new_orders', 0)}\n"
        f"💰 የዕለት ገቢ: {stats.get('daily_revenue', 0)} ETB"
    )
    bot.send_message(message.chat.id, f"📈 የዕለት ሪፖርት\n\n{text}")
    return stats


def show_category_report(message: Message, db: Database, bot: TeleBot):
    """የምድብ ሪፖርት ማሳየት"""
    stats = db.get_category_stats()
    if not stats:
        bot.send_message(message.chat.id, "📊 ምንም የምድብ ሪፖርት አልተገኘም.")
        return []

    text = "\n".join(
        f"• {row.get('category', 'N/A')}: {row.get('product_count', 0)} products"
        for row in stats
    )
    bot.send_message(message.chat.id, f"📊 የምድብ ሪፖርት\n\n{text}")
    return stats


def start_add_discount(message: Message, db: Database, bot: TeleBot):
    """አዲስ ቅናሽ መፍጠር ሂደት መጀመር"""
    bot.send_message(message.chat.id, "🏷️ የቅናሽ ኮድ ያስገቡ:")
    return "discount started"


def list_discounts(message: Message, db: Database, bot: TeleBot):
    """ሁሉንም ቅናሾች ማሳየት"""
    discounts = db.get_discounts() if hasattr(db, 'get_discounts') else []
    if not discounts:
        bot.send_message(message.chat.id, "🏷️ ምንም ቅናሽ አልተገኘም.")
        return []

    text = "\n".join(f"• {discount.get('code', 'N/A')} - {discount.get('discount_percent', 0)}%" for discount in discounts[:10])
    bot.send_message(message.chat.id, f"🏷️ ቅናሾች\n\n{text}")
    return discounts


def list_products(message: Message, db: Database, bot: TeleBot):
    """ሁሉንም ምርቶች ማሳየት"""
    products = db.get_products(limit=10)
    if not products:
        bot.send_message(message.chat.id, "📦 ምንም ምርት አልተገኘም.")
        return []

    text = "\n".join(f"• {product.get('name_am', 'N/A')} - {product.get('price', 0)} ETB" for product in products[:10])
    bot.send_message(message.chat.id, f"📦 ምርቶች\n\n{text}")
    return products


def start_edit_product(message: Message, db: Database, bot: TeleBot):
    """ምርት ማስተካከል ሂደት መጀመር"""
    bot.send_message(message.chat.id, "✏️ የምርት አይዲ ያስገቡ:")
    return "edit product started"


def start_delete_product(message: Message, db: Database, bot: TeleBot):
    """ምርት መሰረዝ ሂደት መጀመር"""
    bot.send_message(message.chat.id, "🗑️ የምርት አይዲ ያስገቡ:")
    return "delete product started"


def show_low_stock(message: Message, db: Database, bot: TeleBot):
    """ዝቅተኛ ክምችት ያላቸውን ምርቶች ማሳየት"""
    products = db.get_low_stock_products(threshold=5)
    if not products:
        bot.send_message(message.chat.id, "📦 ዝቅተኛ ክምችት ያላቸው ምርቶች የሉም.")
        return []

    text = "\n".join(f"• {product.get('name_am', 'N/A')} ({product.get('stock_quantity', 0)})" for product in products)
    bot.send_message(message.chat.id, f"📦 ዝቅተኛ ክምችት\n\n{text}")
    return products


def show_admin_panel(message: Message):
    """የአስተዳዳሪ ፓነል ማሳየት"""
    return {"status": "ok", "chat_id": getattr(message.chat, 'id', None)}
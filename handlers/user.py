# -*- coding: utf-8 -*-

"""
ዘናጭ ቦት - የተጠቃሚ እጅ አያያዝ
ይህ ፋይል ሁሉንም የተጠቃሚ ተዛማጅ እጅ አያያዞችን ይይዛል
"""

import logging
from datetime import datetime
from typing import Optional, Dict

from telebot import TeleBot
from telebot.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database import Database
from utils.helpers import get_text, get_user_lang, format_currency, format_date
from keyboards.inline import get_back_keyboard
from services.notifications import notify_admins

logger = logging.getLogger(__name__)


def register(bot: TeleBot, db: Database):
    """የተጠቃሚ እጅ አያያዞችን መመዝገብ"""
    
    # ==================== መገለጫ ====================
    
    @bot.message_handler(func=lambda m: m.text in ['👤 መገለጫ', '👤 Profile', 'መገለጫ 👤', 'Profile 👤'])
    def profile_command(message: Message):
        """የመገለጫ ትዕዛዝ አያያዝ"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        show_user_profile(message, db, bot)
    
    def show_user_profile(message: Message, db: Database, bot: TeleBot):
        """የተጠቃሚ መገለጫ ማሳየት"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        
        user = db.get_user(user_id)
        
        if not user:
            bot.send_message(
                message.chat.id,
                get_text(lang, 'user_not_found')
            )
            return
        
        # ስታቲስቲክስ
        order_count = len(db.get_user_orders(user_id))
        cart = db.get_cart(user_id)
        cart_items = len(cart['items']) if cart and cart.get('items') else 0
        
        # የማስታወቂያ ሁኔታ
        sub_status = "✅ " + get_text(lang, 'subscribed') if user.get('is_subscribed', 1) else "❌ " + get_text(lang, 'unsubscribed')
        
        # መገለጫ መልዕክት
        msg = f"👤 *{get_text(lang, 'profile')}*\n\n"
        msg += f"📝 {get_text(lang, 'name')}: {user.get('first_name', 'N/A')} {user.get('last_name', '')}\n"
        msg += f"🔹 {get_text(lang, 'username')}: @{user.get('username', 'N/A')}\n"
        msg += f"🆔 {get_text(lang, 'user_id')}: {user_id}\n"
        msg += f"🌍 {get_text(lang, 'language')}: {'አማርኛ' if user.get('lang') == 'am' else 'English'}\n"
        msg += f"📱 {get_text(lang, 'phone')}: {user.get('phone', 'N/A')}\n"
        msg += f"📧 {get_text(lang, 'email')}: {user.get('email', 'N/A')}\n"
        msg += f"📅 {get_text(lang, 'registered')}: {format_date(user.get('registered_at'))}\n"
        msg += f"📋 {get_text(lang, 'orders')}: {order_count}\n"
        msg += f"🛒 {get_text(lang, 'cart_items')}: {cart_items}\n"
        msg += f"📢 {get_text(lang, 'subscription')}: {sub_status}\n"
        
        if user.get('balance', 0) > 0:
            msg += f"💰 {get_text(lang, 'balance')}: {format_currency(user['balance'])} ETB\n"
        
        # ኪቦርድ
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton(
                "✏️ " + get_text(lang, 'edit_profile'),
                callback_data="edit_profile"
            ),
            InlineKeyboardButton(
                "📋 " + get_text(lang, 'my_orders'),
                callback_data="view_orders"
            )
        )
        markup.add(
            InlineKeyboardButton(
                "🛒 " + get_text(lang, 'my_cart'),
                callback_data="view_cart"
            ),
            InlineKeyboardButton(
                "❤️ " + get_text(lang, 'my_wishlist'),
                callback_data="show_wishlist"
            )
        )
        markup.add(
            InlineKeyboardButton(
                "📢 " + (get_text(lang, 'subscribe') if not user.get('is_subscribed', 1) else get_text(lang, 'unsubscribe')),
                callback_data="toggle_subscription"
            ),
            InlineKeyboardButton(
                "🔙 " + get_text(lang, 'back'),
                callback_data="main_menu"
            )
        )
        
        bot.send_message(
            message.chat.id,
            msg,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    
    # ==================== መገለጫ ማስተካከል ====================
    
    @bot.callback_query_handler(func=lambda call: call.data == 'edit_profile')
    def handle_edit_profile(call: CallbackQuery):
        """መገለጫ ማስተካከል"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton(
                "📱 " + get_text(lang, 'change_phone'),
                callback_data="edit_phone"
            ),
            InlineKeyboardButton(
                "📧 " + get_text(lang, 'change_email'),
                callback_data="edit_email"
            )
        )
        markup.add(
            InlineKeyboardButton(
                "🌍 " + get_text(lang, 'change_language'),
                callback_data="change_language"
            ),
            InlineKeyboardButton(
                "🔙 " + get_text(lang, 'back'),
                callback_data="view_profile"
            )
        )
        
        bot.send_message(
            call.message.chat.id,
            "✏️ " + get_text(lang, 'edit_profile') + "\n\n" +
            get_text(lang, 'choose_what_to_edit'),
            reply_markup=markup
        )
        bot.answer_callback_query(call.id)
    
    @bot.callback_query_handler(func=lambda call: call.data == 'view_profile')
    def handle_view_profile(call: CallbackQuery):
        """ወደ መገለጫ መመለስ"""
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        
        show_user_profile(call.message, db, bot)
        bot.answer_callback_query(call.id)
    
    @bot.callback_query_handler(func=lambda call: call.data == 'edit_phone')
    def handle_edit_phone(call: CallbackQuery):
        """ስልክ ቁጥር ማስተካከል"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        msg = bot.send_message(
            call.message.chat.id,
            "📱 " + get_text(lang, 'enter_new_phone') + "\n\n" +
            "📌 " + get_text(lang, 'format_phone_example')
        )
        bot.register_next_step_handler(msg, process_phone_update, db, bot)
        bot.answer_callback_query(call.id)
    
    def process_phone_update(message: Message, db: Database, bot: TeleBot):
        """የስልክ ቁጥር ማስተካከያ ማስኬድ"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        phone = message.text.strip()
        
        # ቀላል ማረጋገጫ
        if len(phone) < 10 or not phone.isdigit():
            bot.send_message(
                message.chat.id,
                "❌ " + get_text(lang, 'invalid_phone')
            )
            return
        
        # ማዘመን
        db.update_user(user_id, phone=phone)
        db.log_activity(user_id, 'update_phone', f'አዲስ ስልክ: {phone}')
        
        bot.send_message(
            message.chat.id,
            "✅ " + get_text(lang, 'phone_updated')
        )
        
        # መገለጫ ማሳየት
        show_user_profile(message, db, bot)
    
    @bot.callback_query_handler(func=lambda call: call.data == 'edit_email')
    def handle_edit_email(call: CallbackQuery):
        """ኢሜይል ማስተካከል"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        msg = bot.send_message(
            call.message.chat.id,
            "📧 " + get_text(lang, 'enter_new_email')
        )
        bot.register_next_step_handler(msg, process_email_update, db, bot)
        bot.answer_callback_query(call.id)
    
    def process_email_update(message: Message, db: Database, bot: TeleBot):
        """የኢሜይል ማስተካከያ ማስኬድ"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        email = message.text.strip()
        
        # ቀላል ማረጋገጫ
        if '@' not in email or '.' not in email:
            bot.send_message(
                message.chat.id,
                "❌ " + get_text(lang, 'invalid_email')
            )
            return
        
        # ማዘመን
        db.update_user(user_id, email=email)
        db.log_activity(user_id, 'update_email', f'አዲስ ኢሜይል: {email}')
        
        bot.send_message(
            message.chat.id,
            "✅ " + get_text(lang, 'email_updated')
        )
        
        # መገለጫ ማሳየት
        show_user_profile(message, db, bot)
    
    @bot.callback_query_handler(func=lambda call: call.data == 'change_language')
    def handle_change_language(call: CallbackQuery):
        """ቋንቋ መቀየር"""
        user_id = call.from_user.id
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("🇪🇹 አማርኛ", callback_data="set_lang_am"),
            InlineKeyboardButton("🇬🇧 English", callback_data="set_lang_en")
        )
        markup.add(
            InlineKeyboardButton(
                "🔙 " + get_text('am', 'back'),
                callback_data="view_profile"
            )
        )
        
        bot.send_message(
            call.message.chat.id,
            "🌍 " + get_text('am', 'choose_language') + "\n\n" +
            "Choose your preferred language:",
            reply_markup=markup
        )
        bot.answer_callback_query(call.id)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('set_lang_'))
    def handle_set_language(call: CallbackQuery):
        """ቋንቋ ማዘመን"""
        user_id = call.from_user.id
        lang = call.data.replace('set_lang_', '')
        
        db.update_user(user_id, lang=lang)
        db.log_activity(user_id, 'change_language', f'ቋንቋ: {lang}')
        
        bot.answer_callback_query(
            call.id,
            "✅ " + get_text(lang, 'language_updated')
        )
        
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        
        show_user_profile(call.message, db, bot)
    
    # ==================== ማስታወቂያ መቀየር ====================
    
    @bot.callback_query_handler(func=lambda call: call.data == 'toggle_subscription')
    def handle_toggle_subscription(call: CallbackQuery):
        """ማስታወቂያ ማብራት/ማጥፋት"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        user = db.get_user(user_id)
        current = user.get('is_subscribed', 1)
        new_status = 0 if current else 1
        
        db.update_user(user_id, is_subscribed=new_status)
        db.log_activity(user_id, 'toggle_subscription', f'አዲስ ሁኔታ: {new_status}')
        
        status_text = get_text(lang, 'subscribed') if new_status else get_text(lang, 'unsubscribed')
        bot.answer_callback_query(
            call.id,
            f"✅ {get_text(lang, 'subscription')}: {status_text}"
        )
        
        # መገለጫ ማሳየት
        show_user_profile(call.message, db, bot)
    
    # ==================== ተመረጡ ====================
    
    @bot.callback_query_handler(func=lambda call: call.data == 'my_wishlist')
    def handle_my_wishlist(call: CallbackQuery):
        """ተመረጡ ማሳየት"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        # ተመረጡ ምርቶችን ማግኘት
        result = db.execute('''
            SELECT p.* FROM wishlists w 
            JOIN products p ON w.product_id = p.id 
            WHERE w.user_id = ?
            ORDER BY w.created_at DESC
        ''', (user_id,))
        
        products = result.fetchall()
        
        if not products:
            bot.send_message(
                call.message.chat.id,
                "❤️ " + get_text(lang, 'empty_wishlist')
            )
            bot.answer_callback_query(call.id)
            return
        
        msg = "❤️ *" + get_text(lang, 'my_wishlist') + "*\n\n"
        
        for i, product in enumerate(products[:10], 1):
            name = product['name_am'] if lang == 'am' else product['name_en']
            msg += f"{i}. *{name}*\n"
            msg += f"💰 {format_currency(product['price'])} ETB\n"
            msg += f"🆔 /product_{product['id']}\n\n"
        
        if len(products) > 10:
            msg += f"\n📌 {get_text(lang, 'and_more')} {len(products) - 10} {get_text(lang, 'items')}"
        
        markup = get_back_keyboard("view_profile", lang)
        
        bot.send_message(
            call.message.chat.id,
            msg,
            reply_markup=markup,
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)
    
    # ==================== ስልክ መጋራት ====================
    
    @bot.message_handler(content_types=['contact'])
    def handle_contact(message: Message):
        """የእውቂያ መልዕክት አያያዝ"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        
        contact = message.contact
        
        if contact:
            phone = contact.phone_number
            db.update_user(user_id, phone=phone)
            db.log_activity(user_id, 'share_contact', f'ስልክ: {phone}')
            
            bot.reply_to(
                message,
                "✅ " + get_text(lang, 'phone_saved')
            )
            
            # መገለጫ ማሳየት
            show_user_profile(message, db, bot)
    
    # ==================== አስተዳዳሪ ተጠቃሚ ፍለጋ ====================
    
    @bot.callback_query_handler(func=lambda call: call.data == 'admin_find_user')
    def handle_admin_find_user(call: CallbackQuery):
        """አስተዳዳሪ ተጠቃሚ መፈለግ"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        # አስተዳዳሪ መሆኑን ማረጋገጥ
        if user_id not in db.get_admin_ids():
            bot.answer_callback_query(call.id, "⛔ " + get_text(lang, 'not_admin'))
            return
        
        msg = bot.send_message(
            call.message.chat.id,
            "🔍 " + get_text(lang, 'enter_user_id_or_username')
        )
        bot.register_next_step_handler(msg, process_admin_find_user, db, bot)
        bot.answer_callback_query(call.id)
    
    def process_admin_find_user(message: Message, db: Database, bot: TeleBot):
        """አስተዳዳሪ ተጠቃሚ ፍለጋ ማስኬድ"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        search = message.text.strip()
        
        # በID መፈለግ
        if search.isdigit():
            user = db.get_user(int(search))
        else:
            # በዩዘርኔም መፈለግ
            username = search.replace('@', '')
            user = db.get_user_by_username(username)
        
        if not user:
            bot.send_message(
                message.chat.id,
                "❌ " + get_text(lang, 'user_not_found')
            )
            return
        
        # የተጠቃሚ መረጃ
        msg = f"👤 *{get_text(lang, 'user_details')}*\n\n"
        msg += f"🆔 ID: {user['user_id']}\n"
        msg += f"👤 {get_text(lang, 'name')}: {user.get('first_name', 'N/A')}\n"
        msg += f"🔹 @{user.get('username', 'N/A')}\n"
        msg += f"📱 {get_text(lang, 'phone')}: {user.get('phone', 'N/A')}\n"
        msg += f"📧 {get_text(lang, 'email')}: {user.get('email', 'N/A')}\n"
        msg += f"🌍 {get_text(lang, 'language')}: {user.get('lang', 'am')}\n"
        msg += f"📅 {get_text(lang, 'registered')}: {format_date(user.get('registered_at'))}\n"
        msg += f"📢 {get_text(lang, 'subscribed')}: {'✅' if user.get('is_subscribed', 1) else '❌'}\n"
        msg += f"🚫 {get_text(lang, 'banned')}: {'✅' if user.get('is_banned', 0) else '❌'}\n"
        
        # ትዕዛዝ ብዛት
        orders = db.get_user_orders(user['user_id'])
        msg += f"📋 {get_text(lang, 'orders')}: {len(orders)}\n"
        
        # የአስተዳዳሪ ኪቦርድ
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton(
                "📋 " + get_text(lang, 'view_orders'),
                callback_data=f"admin_user_orders_{user['user_id']}"
            ),
            InlineKeyboardButton(
                "🚫 " + (get_text(lang, 'ban_user') if not user.get('is_banned', 0) else get_text(lang, 'unban_user')),
                callback_data=f"admin_toggle_ban_{user['user_id']}"
            )
        )
        markup.add(
            InlineKeyboardButton(
                "📢 " + get_text(lang, 'send_message'),
                callback_data=f"admin_msg_user_{user['user_id']}"
            ),
            InlineKeyboardButton(
                "🔙 " + get_text(lang, 'back'),
                callback_data="admin_back"
            )
        )
        
        bot.send_message(
            message.chat.id,
            msg,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('admin_toggle_ban_'))
    def handle_admin_toggle_ban(call: CallbackQuery):
        """አስተዳዳሪ ተጠቃሚ መከልከል/መፍቀድ"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        target_id = int(call.data.replace('admin_toggle_ban_', ''))
        
        # አስተዳዳሪ መሆኑን ማረጋገጥ
        if user_id not in db.get_admin_ids():
            bot.answer_callback_query(call.id, "⛔ " + get_text(lang, 'not_admin'))
            return
        
        user = db.get_user(target_id)
        if not user:
            bot.answer_callback_query(call.id, "❌ " + get_text(lang, 'user_not_found'))
            return
        
        new_status = 0 if user.get('is_banned', 0) else 1
        db.update_user(target_id, is_banned=new_status)
        db.log_activity(user_id, 'toggle_ban', f'ተጠቃሚ {target_id}, አዲስ ሁኔታ: {new_status}')
        
        status_text = get_text(lang, 'banned') if new_status else get_text(lang, 'unbanned')
        bot.answer_callback_query(call.id, f"✅ {get_text(lang, 'user')} {status_text}")
        
        # ለተጠቃሚ ማሳወቅ
        if new_status:
            bot.send_message(
                target_id,
                "🚫 " + get_text(lang, 'you_have_been_banned') + "\n\n" +
                get_text(lang, 'contact_admin_for_help')
            )
        else:
            bot.send_message(
                target_id,
                "✅ " + get_text(lang, 'you_have_been_unbanned') + "\n\n" +
                get_text(lang, 'welcome_back')
            )
        
        # ለአስተዳዳሪ ማሳወቅ
        notify_admins(
            bot,
            f"👤 {get_text(lang, 'user_status_changed')}\n\n"
            f"👤 {get_text(lang, 'user')}: {user.get('first_name', 'N/A')}\n"
            f"🆔 ID: {target_id}\n"
            f"📊 {get_text(lang, 'status')}: {status_text}\n"
            f"👤 {get_text(lang, 'by')}: {call.from_user.first_name}"
        )
        
        # መልዕክቱን ማዘመን
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        
        process_admin_find_user(call.message, db, bot)
# -*- coding: utf-8 -*-
# pyright: reportOptionalMemberAccess=false, reportArgumentType=false, reportOptionalSubscript=false, reportAttributeAccessIssue=false

"""
ዘናጭ ቦት - የትዕዛዝ እጅ አያያዝ
ይህ ፋይል ሁሉንም የትዕዛዝ እጅ አያያዞችን ይይዛል
"""

import logging
import json
import random
import string
from datetime import datetime
from typing import Optional, Dict, List

from telebot import TeleBot
from telebot.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

from database import Database
from utils.helpers import get_text, get_user_lang, format_currency, generate_order_number
from keyboards.inline import get_order_keyboard, get_payment_keyboard
from services.notifications import notify_admins, send_order_confirmation

logger = logging.getLogger(__name__)

# ለትዕዛዝ ጊዜያዊ መረጃ
order_states = {}

show_cart = None
process_discount_code = None
handle_checkout = None
handle_payment = None
show_user_orders = None

show_cart = None
process_discount_code = None
handle_checkout = None
handle_payment = None
show_user_orders = None


def register(bot: TeleBot, db: Database):
    """የትዕዛዝ እጅ አያያዞችን መመዝገብ"""
    
    # ==================== ጋሪ ማሳየት ====================
    
    @bot.message_handler(func=lambda m: m.text in ['🛒 ጋሪ', '🛒 Cart', 'ጋሪ 🛒', 'Cart 🛒'])
    def show_cart_command(message: Message):
        """የጋሪ ትዕዛዝ አያያዝ"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        show_cart(message, db, bot)
    
    def show_cart(message: Message, db: Database, bot: TeleBot):
        """ጋሪ ማሳየት"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        
        cart = db.get_cart(user_id)
        
        if not cart or not cart.get('items'):
            bot.send_message(
                message.chat.id,
                "🛒 ጋሪዎ ባዶ ነው!\n\n"
                "📌 ምርቶችን ለመግዛት ከላይ ካሉት ምድቦች ይምረጡ."
            )
            return
        
        items = json.loads(cart['items']) if isinstance(cart['items'], str) else cart['items']
        
        msg = "🛒 *ጋሪዎ*\n\n"
        total = 0
        
        for i, item in enumerate(items, 1):
            subtotal = item['price'] * item['quantity']
            total += subtotal
            
            msg += f"{i}. {item['name']}\n"
            msg += f"   📦 ብዛት: {item['quantity']}\n"
            msg += f"   💰 {format_currency(item['price'])} × {item['quantity']} = {format_currency(subtotal)}\n\n"
        
        msg += f"💰 *ጠቅላላ:* {format_currency(total)} ETB\n"
        
        if cart.get('discount_amount', 0) > 0:
            msg += f"🏷️ *ቅናሽ:* -{format_currency(cart['discount_amount'])} ETB\n"
            msg += f"💰 *የተጣራ:* {format_currency(cart['final_amount'])} ETB\n"
        
        # ኪቦርድ
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("🛒 ለመግዛት", callback_data="checkout"),
            InlineKeyboardButton("🗑️ ጋሪ አጽዳ", callback_data="clear_cart"),
            InlineKeyboardButton("🏷️ ቅናሽ አስገባ", callback_data="apply_discount"),
            InlineKeyboardButton("🔙 ወደ መጀመሪያ", callback_data="main_menu")
        )
        
        bot.send_message(
            message.chat.id,
            msg,
            reply_markup=markup,
            parse_mode='Markdown'
        )

    globals()['show_cart'] = show_cart
    
    # ==================== ጋሪ ማጽዳት ====================
    
    @bot.callback_query_handler(func=lambda call: call.data == 'clear_cart')
    def handle_clear_cart(call: CallbackQuery):
        """ጋሪ ማጽዳት"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        db.clear_cart(user_id)
        bot.answer_callback_query(call.id, "✅ ጋሪዎ ተጽድቷል!")
        
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        
        show_cart(call.message, db, bot)
    
    # ==================== ቅናሽ መተግበር ====================
    
    @bot.callback_query_handler(func=lambda call: call.data == 'apply_discount')
    def handle_apply_discount(call: CallbackQuery):
        """ቅናሽ መተግበር"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        msg = bot.send_message(
            call.message.chat.id,
            "🏷️ የቅናሽ ኮዱን ያስገቡ:"
        )
        bot.register_next_step_handler(msg, process_discount_code, db, bot)
        bot.answer_callback_query(call.id)
    
    def process_discount_code(message: Message, db: Database, bot: TeleBot):
        """የቅናሽ ኮድ ማስኬድ"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        code = message.text.upper().strip()
        
        # ቅናሹን ማረጋገጥ
        discount = db.get_discount_by_code(code)
        
        if not discount:
            bot.send_message(
                message.chat.id,
                "❌ የቅናሽ ኮዱ ልክ አይደለም ወይም ጊዜው አልፏል!"
            )
            return
        
        # ተጠቃሚው ቅናሹን መጠቀም እንደሚችል ማረጋገጥ
        if discount['user_limit'] > 0:
            # ተጠቃሚው ስንት ጊዜ ተጠቅሟል ማረጋገጥ
            usage_count = db.execute(
                "SELECT COUNT(*) FROM discount_usage WHERE discount_id = ? AND user_id = ?",
                (discount['id'], user_id)
            ).fetchone()[0]
            
            if usage_count >= discount['user_limit']:
                bot.send_message(
                    message.chat.id,
                    "❌ ይህን ቅናሽ ከፍተኛውን ጊዜ ተጠቅመዋል!"
                )
                return
        
        # ቅናሽ መተግበር
        cart = db.get_cart(user_id)
        
        if not cart or not cart.get('items'):
            bot.send_message(
                message.chat.id,
                "❌ ጋሪዎ ባዶ ነው!"
            )
            return
        
        items = json.loads(cart['items']) if isinstance(cart['items'], str) else cart['items']
        total = sum(item['price'] * item['quantity'] for item in items)
        
        # ዝቅተኛ የትዕዛዝ መጠን ማረጋገጥ
        if discount['min_order_amount'] > 0 and total < discount['min_order_amount']:
            bot.send_message(
                message.chat.id,
                f"❌ ይህን ቅናሽ ለመጠቀም ቢያንስ {format_currency(discount['min_order_amount'])} ETB መግዛት አለብዎት!"
            )
            return
        
        # ቅናሽ ማስላት
        discount_amount = total * (discount['discount_percent'] / 100)
        
        # ከፍተኛ ቅናሽ ማረጋገጥ
        if discount['max_discount_amount'] and discount_amount > discount['max_discount_amount']:
            discount_amount = discount['max_discount_amount']
        
        final_amount = total - discount_amount
        
        # ጋሪ ማዘመን
        db.update_cart(user_id, items, code)
        
        bot.send_message(
            message.chat.id,
            f"✅ ቅናሽ ተተግብሯል!\n\n"
            f"🏷️ ኮድ: {code}\n"
            f"📊 ቅናሽ: {discount['discount_percent']}%\n"
            f"💰 ቅናሽ መጠን: {format_currency(discount_amount)} ETB\n"
            f"💰 የተጣራ: {format_currency(final_amount)} ETB"
        )
        
        # ጋሪ ማሳየት
        show_cart(message, db, bot)

    globals()['process_discount_code'] = process_discount_code
    
    # ==================== ግዢ ማረጋገጥ ====================
    
    @bot.callback_query_handler(func=lambda call: call.data == 'checkout')
    def handle_checkout(call: CallbackQuery):
        """ግዢ ማረጋገጥ"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        cart = db.get_cart(user_id)
        
        if not cart or not cart.get('items'):
            bot.answer_callback_query(call.id, "❌ ጋሪዎ ባዶ ነው!")
            return
        
        items = json.loads(cart['items']) if isinstance(cart['items'], str) else cart['items']
        total = cart['final_amount'] or sum(item['price'] * item['quantity'] for item in items)
        
        # የአድራሻ መረጃ መጠየቅ
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(
            KeyboardButton("📍 አድራሻዬን ላክ", request_location=True),
            KeyboardButton("📱 ስልኬን ላክ", request_contact=True),
            KeyboardButton("✏️ በእጅ ጻፍ")
        )
        
        msg = bot.send_message(
            call.message.chat.id,
            f"🛒 *ግዢ ማረጋገጥ*\n\n"
            f"💰 ጠቅላላ: {format_currency(total)} ETB\n\n"
            f"📍 የማጓጓዣ አድራሻዎን ያስገቡ:",
            reply_markup=markup,
            parse_mode='Markdown'
        )
        
        order_states[user_id] = {
            'step': 'address',
            'total': total,
            'items': items,
            'discount_code': cart.get('discount_code')
        }
        
        bot.register_next_step_handler(msg, process_address, db, bot)
        bot.answer_callback_query(call.id)
    
    def process_address(message: Message, db: Database, bot: TeleBot):
        """የአድራሻ መረጃ ማስኬድ"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        
        if message.content_type == 'location':
            location = message.location
            address = f"📍 ኬክሮስ: {location.latitude}, ኬንትሮስ: {location.longitude}"
        elif message.content_type == 'contact':
            contact = message.contact
            db.update_user(user_id, phone=contact.phone_number)
            address = f"📱 ስልክ: {contact.phone_number}\n👤 ስም: {contact.first_name}"
        else:
            address = message.text
        
        order_states[user_id]['address'] = address
        order_states[user_id]['step'] = 'payment'
        
        # የክፍያ ዘዴ ምርጫ
        markup = get_payment_keyboard(lang)
        
        bot.send_message(
            message.chat.id,
            "💳 *የክፍያ ዘዴ ይምረጡ:*",
            reply_markup=markup,
            parse_mode='Markdown'
        )
    
    # ==================== ክፍያ ማስኬድ ====================
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('pay_'))
    def handle_payment(call: CallbackQuery):
        """የክፍያ ምርጫ አያያዝ"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        payment_method = call.data.replace('pay_', '')
        state = order_states.get(user_id)
        
        if not state or state.get('step') != 'payment':
            bot.answer_callback_query(call.id, "❌ የግዢ ሂደት ተቋርጧል!")
            return
        
        # ትዕዛዝ መፍጠር
        order_number = generate_order_number()
        
        order_data = {
            'order_number': order_number,
            'user_id': user_id,
            'total_amount': state['total'],
            'subtotal_amount': state['total'],
            'discount_amount': 0,
            'shipping_amount': 0,
            'tax_amount': 0,
            'final_amount': state['total'],
            'status': 'Pending',
            'payment_method': payment_method,
            'shipping_address': state['address'],
            'shipping_phone': db.get_user(user_id).get('phone'),
            'shipping_name': db.get_user(user_id).get('first_name'),
            'notes': f"ከቦት ትዕዛዝ - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        }
        
        order_id = db.create_order(order_data)
        
        if not order_id:
            bot.send_message(
                call.message.chat.id,
                "❌ ትዕዛዙ መፍጠር አልተቻለም!"
            )
            return
        
        # የትዕዛዝ ዝርዝሮችን መጨመር
        for item in state['items']:
            db.add_order_item(
                order_id=order_id,
                product_id=item['product_id'],
                quantity=item['quantity'],
                price=item['price']
            )
        
        # ቅናሽ ከተጠቀሙ
        if state.get('discount_code'):
            discount = db.get_discount_by_code(state['discount_code'])
            if discount:
                db.use_discount(discount['id'], user_id, order_id)
        
        # ጋሪ ማጽዳት
        db.clear_cart(user_id)
        
        # ማስታወቂያ
        order = db.get_order(order_id)
        items = db.get_order_items(order_id)
        
        # ለተጠቃሚ ማሳወቅ
        msg = f"✅ *ትዕዛዝዎ ተረጋግጧል!*\n\n"
        msg += f"🔢 *ትዕዛዝ ቁጥር:* {order_number}\n"
        msg += f"💰 *ጠቅላላ:* {format_currency(state['total'])} ETB\n"
        msg += f"💳 *ክፍያ:* {payment_method}\n\n"
        msg += f"📦 በቅርቡ እናገኝዎታለን! 🙏\n\n"
        msg += f"📋 ትዕዛዝዎን ለመከታተል /orders ይጫኑ"
        
        bot.send_message(
            call.message.chat.id,
            msg,
            parse_mode='Markdown'
        )
        
        # ለአስተዳዳሪ ማሳወቅ
        admin_msg = f"🆕 *አዲስ ትዕዛዝ!*\n\n"
        admin_msg += f"🔢 {order_number}\n"
        admin_msg += f"👤 ተጠቃሚ: {call.from_user.first_name} (@{call.from_user.username or 'Unknown'})\n"
        admin_msg += f"💰 {format_currency(state['total'])} ETB\n"
        admin_msg += f"💳 {payment_method}\n"
        admin_msg += f"📍 {state['address'][:50]}...\n\n"
        admin_msg += f"📦 ምርቶች:\n"
        
        for item in items:
            product = db.get_product(item['product_id'])
            admin_msg += f"  • {product['name_am']} × {item['quantity']}\n"
        
        admin_msg += f"\n🔗 /order_{order_id}"
        
        notify_admins(bot, admin_msg)
        
        # ሁኔታን ማጽዳት
        order_states.pop(user_id, None)
        bot.answer_callback_query(call.id)

    globals()['handle_checkout'] = handle_checkout
    globals()['handle_payment'] = handle_payment
    
    # ==================== ትዕዛዞቼ ====================
    
    @bot.message_handler(func=lambda m: m.text in ['📋 ትዕዛዞቼ', '📋 My Orders', 'ትዕዛዞቼ 📋', 'My Orders 📋'])
    def show_orders_command(message: Message):
        """የትዕዛዝ ትዕዛዝ አያያዝ"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        show_user_orders(message, db, bot)
    
    def show_user_orders(message: Message, db: Database, bot: TeleBot):
        """የተጠቃሚ ትዕዛዞችን ማሳየት"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        
        orders = db.get_user_orders(user_id, limit=10)
        
        if not orders:
            bot.send_message(
                message.chat.id,
                "📭 ምንም ትዕዛዝ የለም\n\n"
                "🛒 ለመግዛት ከላይ ካሉት ምድቦች ይምረጡ."
            )
            return
        
        msg = "📋 *ትዕዛዞቼ*\n\n"
        
        for order in orders[:10]:
            status_emoji = {
                'Pending': '⏳',
                'Processing': '🔄',
                'Shipped': '🚚',
                'Delivered': '✅',
                'Cancelled': '❌'
            }.get(order['status'], '📦')
            
            msg += f"{status_emoji} *{order['order_number']}*\n"
            msg += f"💰 {format_currency(order['final_amount'])} ETB\n"
            msg += f"📦 {order['status']}\n"
            msg += f"📅 {order['order_date'][:10]}\n"
            msg += f"📦 {order.get('item_count', 0)} እቃዎች\n\n"
        
        # ተጨማሪ አዝራር
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton(
                "🔙 ወደ መጀመሪያ",
                callback_data="main_menu"
            )
        )
        
        bot.send_message(
            message.chat.id,
            msg,
            reply_markup=markup,
            parse_mode='Markdown'
        )

    globals()['show_user_orders'] = show_user_orders
    
    # ==================== የትዕዛዝ ዝርዝር ====================
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('order_'))
    def handle_order_detail(call: CallbackQuery):
        """የትዕዛዝ ዝርዝር ማሳየት"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        order_id = int(call.data.replace('order_', ''))
        order = db.get_order(order_id)
        
        if not order:
            bot.answer_callback_query(call.id, "❌ ትዕዛዙ አልተገኘም!")
            return
        
        # ተጠቃሚው የራሱ ትዕዛዝ መሆኑን ማረጋገጥ
        if order['user_id'] != user_id and user_id not in db.get_admin_ids():
            bot.answer_callback_query(call.id, "⛔ ፈቃድ የለዎትም!")
            return
        
        items = db.get_order_items(order_id)
        
        msg = f"📋 *የትዕዛዝ ዝርዝር*\n\n"
        msg += f"🔢 *ቁጥር:* {order['order_number']}\n"
        msg += f"📅 *ቀን:* {order['order_date']}\n"
        msg += f"📦 *ሁኔታ:* {order['status']}\n"
        msg += f"💳 *ክፍያ:* {order['payment_method']} - {order['payment_status']}\n\n"
        
        msg += "*📦 ምርቶች:*\n"
        for item in items:
            product = db.get_product(item['product_id'])
            name = product['name_am'] if product else 'N/A'
            msg += f"  • {name} × {item['quantity']} = {format_currency(item['total_price'])} ETB\n"
        
        msg += f"\n💰 *ጠቅላላ:* {format_currency(order['total_amount'])} ETB\n"
        
        if order['discount_amount'] > 0:
            msg += f"🏷️ *ቅናሽ:* -{format_currency(order['discount_amount'])} ETB\n"
        
        msg += f"💰 *የተጣራ:* {format_currency(order['final_amount'])} ETB\n"
        
        if order['shipping_address']:
            msg += f"\n📍 *አድራሻ:* {order['shipping_address']}"
        
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton(
                "🔙 ወደ ትዕዛዞች",
                callback_data="back_to_orders"
            )
        )
        
        bot.send_message(
            call.message.chat.id,
            msg,
            reply_markup=markup,
            parse_mode='Markdown'
        )
        
        bot.answer_callback_query(call.id)
    
    @bot.callback_query_handler(func=lambda call: call.data == 'back_to_orders')
    def handle_back_to_orders(call: CallbackQuery):
        """ወደ ትዕዛዞች መመለስ"""
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        
        show_user_orders(call.message, db, bot)
    
    # ==================== የአስተዳዳሪ ትዕዛዝ ማስተዳደር ====================
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('admin_order_'))
    def handle_admin_order(call: CallbackQuery):
        """የአስተዳዳሪ ትዕዛዝ ማስተዳደር"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        # አስተዳዳሪ መሆኑን ማረጋገጥ
        if user_id not in db.get_admin_ids():
            bot.answer_callback_query(call.id, "⛔ ፈቃድ የለዎትም!")
            return
        
        parts = call.data.split('_')
        action = parts[2]
        order_id = int(parts[3])
        
        if action == 'status':
            # የሁኔታ ለውጥ
            new_status = parts[4] if len(parts) > 4 else None
            
            if new_status:
                db.update_order_status(order_id, new_status)
                bot.answer_callback_query(call.id, f"✅ ሁኔታ ወደ {new_status} ተቀይሯል!")
                
                # ለተጠቃሚ ማሳወቅ
                order = db.get_order(order_id)
                if order:
                    bot.send_message(
                        order['user_id'],
                        f"📋 *የትዕዛዝ ሁኔታ ተቀይሯል!*\n\n"
                        f"🔢 ቁጥር: {order['order_number']}\n"
                        f"📦 አዲስ ሁኔታ: {new_status}\n\n"
                        f"📌 ለዝርዝር /orders ይጫኑ",
                        parse_mode='Markdown'
                    )
            else:
                # የሁኔታ ምርጫ ማሳየት
                markup = InlineKeyboardMarkup(row_width=2)
                statuses = ['Processing', 'Shipped', 'Delivered', 'Cancelled']
                
                for status in statuses:
                    markup.add(
                        InlineKeyboardButton(
                            status,
                            callback_data=f"admin_order_status_{order_id}_{status}"
                        )
                    )
                
                markup.add(
                    InlineKeyboardButton(
                        "🔙 ወደኋላ",
                        callback_data=f"admin_order_view_{order_id}"
                    )
                )
                
                bot.send_message(
                    call.message.chat.id,
                    f"📋 *ሁኔታ ለትዕዛዝ #{order_id}*\n\nአዲሱን ሁኔታ ይምረጡ:",
                    reply_markup=markup,
                    parse_mode='Markdown'
                )
        
        elif action == 'view':
            # የትዕዛዝ ዝርዝር ማሳየት
            order = db.get_order(order_id)
            
            if not order:
                bot.answer_callback_query(call.id, "❌ ትዕዛዙ አልተገኘም!")
                return
            
            items = db.get_order_items(order_id)
            user = db.get_user(order['user_id'])
            
            msg = f"📋 *የትዕዛዝ ዝርዝር*\n\n"
            msg += f"🔢 *ቁጥር:* {order['order_number']}\n"
            msg += f"👤 *ተጠቃሚ:* {user['first_name']} (@{user['username'] or 'Unknown'})\n"
            msg += f"📅 *ቀን:* {order['order_date']}\n"
            msg += f"📦 *ሁኔታ:* {order['status']}\n"
            msg += f"💳 *ክፍያ:* {order['payment_method']} - {order['payment_status']}\n\n"
            
            msg += "*📦 ምርቶች:*\n"
            for item in items:
                product = db.get_product(item['product_id'])
                name = product['name_am'] if product else 'N/A'
                msg += f"  • {name} × {item['quantity']} = {format_currency(item['total_price'])} ETB\n"
            
            msg += f"\n💰 *ጠቅላላ:* {format_currency(order['total_amount'])} ETB\n"
            
            if order['discount_amount'] > 0:
                msg += f"🏷️ *ቅናሽ:* -{format_currency(order['discount_amount'])} ETB\n"
            
            msg += f"💰 *የተጣራ:* {format_currency(order['final_amount'])} ETB\n"
            
            if order['shipping_address']:
                msg += f"\n📍 *አድራሻ:* {order['shipping_address']}"
            
            # የአስተዳዳሪ ኪቦርድ
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                InlineKeyboardButton(
                    "📦 ሁኔታ ቀይር",
                    callback_data=f"admin_order_status_{order_id}"
                ),
                InlineKeyboardButton(
                    "🔙 ወደ ትዕዛዞች",
                    callback_data="admin_back_to_orders"
                )
            )
            
            bot.send_message(
                call.message.chat.id,
                msg,
                reply_markup=markup,
                parse_mode='Markdown'
            )
        
        bot.answer_callback_query(call.id)
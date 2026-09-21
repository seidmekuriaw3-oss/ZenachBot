# -*- coding: utf-8 -*-

"""
ዘናጭ ቦት - የጥሪ እጅ አያያዝ
ይህ ፋይል ሁሉንም የ Inline ኪቦርድ ጥሪ እጅ አያያዞችን ይይዛል
"""

import logging
import json
from datetime import datetime
from typing import Optional, Dict, List

from telebot import TeleBot
from telebot.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database import Database
from utils.helpers import get_text, get_user_lang, format_currency
from keyboards.inline import get_main_keyboard, get_back_keyboard
from services.notifications import notify_admins

logger = logging.getLogger(__name__)


def register(bot: TeleBot, db: Database):
    """የጥሪ እጅ አያያዞችን መመዝገብ"""
    
    # ==================== ዋና ሜኑ ====================
    
    @bot.callback_query_handler(func=lambda call: call.data == 'main_menu')
    def handle_main_menu(call: CallbackQuery):
        """ወደ ዋና ሜኑ መመለስ"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        
        from handlers.start import show_welcome
        show_welcome(call.message.chat.id, user_id, db, bot)
        bot.answer_callback_query(call.id)
    
    # ==================== ምድቦች ====================
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('category_'))
    def handle_category(call: CallbackQuery):
        """የምድብ ምርጫ አያያዝ"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        category = call.data.replace('category_', '')
        
        # ምርቶችን ማግኘት
        products = db.get_products(category=category, limit=20, offset=0)
        
        if not products:
            bot.answer_callback_query(
                call.id, 
                get_text(lang, 'no_products_in_category')
            )
            return
        
        # የመጀመሪያውን ምርት ማሳየት
        from handlers.products import show_product
        show_product(
            call.message.chat.id, 
            products[0], 
            0, 
            len(products), 
            category, 
            lang, 
            db, 
            bot
        )
        bot.answer_callback_query(call.id)
    
    # ==================== ምርት አሰሳ ====================
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('product_nav_'))
    def handle_product_nav(call: CallbackQuery):
        """የምርት አሰሳ አያያዝ"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        parts = call.data.split('_')
        category = parts[2]
        index = int(parts[3])
        
        products = db.get_products(category=category, limit=20, offset=0)
        
        if not products or index >= len(products):
            bot.answer_callback_query(call.id, get_text(lang, 'no_more_products'))
            return
        
        # መልዕክቱን መሰረዝ
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        
        from handlers.products import show_product
        show_product(
            call.message.chat.id, 
            products[index], 
            index, 
            len(products), 
            category, 
            lang, 
            db, 
            bot
        )
        bot.answer_callback_query(call.id)
    
    # ==================== ምርት ዝርዝር ====================
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('product_view_'))
    def handle_product_view(call: CallbackQuery):
        """የምርት ዝርዝር ማሳየት"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        product_id = int(call.data.replace('product_view_', ''))
        product = db.get_product(product_id)
        
        if not product:
            bot.answer_callback_query(call.id, get_text(lang, 'product_not_found'))
            return
        
        from handlers.products import show_product_detail
        show_product_detail(call.message.chat.id, product, lang, db, bot)
        bot.answer_callback_query(call.id)
    
    # ==================== ምርት መግዛት ====================
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('product_buy_'))
    def handle_product_buy(call: CallbackQuery):
        """ምርት መግዛት አያያዝ"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        product_id = int(call.data.replace('product_buy_', ''))
        product = db.get_product(product_id)
        
        if not product:
            bot.answer_callback_query(call.id, get_text(lang, 'product_not_found'))
            return
        
        if product['stock_quantity'] <= 0:
            bot.answer_callback_query(call.id, get_text(lang, 'out_of_stock'))
            return
        
        from handlers.products import show_quantity_selector
        show_quantity_selector(call.message.chat.id, product, lang, db, bot)
        bot.answer_callback_query(call.id)
    
    # ==================== የቁጥር ምርጫ ====================
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('qty_'))
    def handle_quantity(call: CallbackQuery):
        """የቁጥር ምርጫ አያያዝ"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        parts = call.data.split('_')
        product_id = int(parts[1])
        quantity = int(parts[2])
        
        product = db.get_product(product_id)
        
        if not product:
            bot.answer_callback_query(call.id, get_text(lang, 'product_not_found'))
            return
        
        if quantity > product['stock_quantity']:
            bot.answer_callback_query(
                call.id, 
                get_text(lang, 'not_enough_stock').format(product['stock_quantity'])
            )
            return
        
        # ወደ ጋሪ መጨመር
        from handlers.orders import add_to_cart
        add_to_cart(user_id, product_id, quantity, db)
        
        bot.answer_callback_query(
            call.id, 
            get_text(lang, 'added_to_cart').format(product['name_am'], quantity)
        )
        
        # ጋሪ ማሳየት
        from handlers.orders import show_cart
        show_cart(call.message, db, bot)
    
    # ==================== ግምገማ ====================
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('product_review_'))
    def handle_product_review(call: CallbackQuery):
        """የምርት ግምገማ አያያዝ"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        product_id = int(call.data.replace('product_review_', ''))
        product = db.get_product(product_id)
        
        if not product:
            bot.answer_callback_query(call.id, get_text(lang, 'product_not_found'))
            return
        
        from handlers.products import show_reviews
        show_reviews(call.message.chat.id, product, lang, db, bot)
        bot.answer_callback_query(call.id)
    
    # ==================== ደረጃ መስጠት ====================
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('rate_'))
    def handle_rate(call: CallbackQuery):
        """ደረጃ መስጠት አያያዝ"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        parts = call.data.split('_')
        product_id = int(parts[1])
        rating = int(parts[2])
        
        # ተጠቃሚው ይህን ምርት መግዛቱን ማረጋገጥ
        orders = db.get_user_orders(user_id)
        has_purchased = False
        
        for order in orders:
            items = db.get_order_items(order['id'])
            if any(item['product_id'] == product_id for item in items):
                has_purchased = True
                break
        
        if not has_purchased:
            bot.answer_callback_query(
                call.id, 
                get_text(lang, 'must_purchase_to_review')
            )
            return
        
        # ግምገማ ማስቀመጥ
        success = db.add_review({
            'user_id': user_id,
            'product_id': product_id,
            'rating': rating,
            'is_verified': 1
        })
        
        if success:
            bot.answer_callback_query(
                call.id, 
                get_text(lang, 'review_added').format(rating)
            )
            
            # ለአስተዳዳሪ ማሳወቅ
            product = db.get_product(product_id)
            notify_admins(
                bot,
                f"⭐ *አዲስ ግምገማ!*\n\n"
                f"📦 ምርት: {product['name_am']}\n"
                f"⭐ ደረጃ: {rating}/5\n"
                f"👤 ተጠቃሚ: {call.from_user.first_name}"
            )
        else:
            bot.answer_callback_query(call.id, get_text(lang, 'error'))
    
    # ==================== ግምገማ አስተያየት ====================
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('review_comment_'))
    def handle_review_comment(call: CallbackQuery):
        """የግምገማ አስተያየት አያያዝ"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        product_id = int(call.data.replace('review_comment_', ''))
        
        msg = bot.send_message(
            call.message.chat.id,
            "💬 አስተያየትዎን ይጻፉ (ካልፈለጉ 'skip' ይተይቡ):"
        )
        bot.register_next_step_handler(msg, process_review_comment, product_id, db, bot)
        bot.answer_callback_query(call.id)
    
    def process_review_comment(message, product_id, db, bot):
        """የግምገማ አስተያየት ማስኬድ"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        
        comment = None if message.text.lower() == 'skip' else message.text
        
        # ግምገማ ማዘመን
        success = db.add_review({
            'user_id': user_id,
            'product_id': product_id,
            'comment': comment
        })
        
        if success:
            bot.send_message(
                message.chat.id,
                "✅ አስተያየትዎ ተመዝግቧል! እናመሰግናለን! 🙏"
            )
        else:
            bot.send_message(
                message.chat.id,
                "❌ አስተያየት መመዝገብ አልተቻለም!"
            )
    
    # ==================== ጋሪ ====================
    
    @bot.callback_query_handler(func=lambda call: call.data == 'view_cart')
    def handle_view_cart(call: CallbackQuery):
        """ጋሪ ማሳየት"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        from handlers.orders import show_cart
        show_cart(call.message, db, bot)
        bot.answer_callback_query(call.id)
    
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
        
        from handlers.orders import show_cart
        show_cart(call.message, db, bot)
    
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
    
    def process_discount_code(message, db, bot):
        """የቅናሽ ኮድ ማስኬድ"""
        from handlers.orders import process_discount_code as process
        process(message, db, bot)
    
    # ==================== ትዕዛዝ ማረጋገጥ ====================
    
    @bot.callback_query_handler(func=lambda call: call.data == 'checkout')
    def handle_checkout(call: CallbackQuery):
        """ግዢ ማረጋገጥ"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        from handlers.orders import handle_checkout
        handle_checkout(call)
    
    # ==================== ክፍያ ====================
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('pay_'))
    def handle_payment(call: CallbackQuery):
        """የክፍያ ምርጫ አያያዝ"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        from handlers.orders import handle_payment
        handle_payment(call)
    
    # ==================== ቅናሾች ====================
    
    @bot.callback_query_handler(func=lambda call: call.data == 'show_discounts')
    def handle_show_discounts(call: CallbackQuery):
        """ቅናሾችን ማሳየት"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        discounts = db.get_all_discounts(active_only=True)
        
        if not discounts:
            bot.send_message(
                call.message.chat.id,
                "🏷️ በአሁኑ ጊዜ ምንም ንቁ ቅናሽ የለም"
            )
            bot.answer_callback_query(call.id)
            return
        
        msg = "🏷️ *ንቁ ቅናሾች*\n\n"
        
        for discount in discounts[:5]:
            msg += f"🔹 *{discount['code']}*\n"
            msg += f"📊 {discount['discount_percent']}% ቅናሽ\n"
            
            if discount['description']:
                msg += f"💬 {discount['description']}\n"
            
            if discount['min_order_amount'] > 0:
                msg += f"💰 ዝቅተኛ: {format_currency(discount['min_order_amount'])} ETB\n"
            
            if discount['valid_to']:
                msg += f"📅 የሚያልቅ: {discount['valid_to'][:10]}\n"
            
            msg += "\n"
        
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton(
                "🔙 ወደ መጀመሪያ",
                callback_data="main_menu"
            )
        )
        
        bot.send_message(
            call.message.chat.id,
            msg,
            reply_markup=markup,
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)
    
    # ==================== ተመረጡ ====================
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('product_wishlist_'))
    def handle_wishlist(call: CallbackQuery):
        """ወደ ተመረጡ መጨመር"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        product_id = int(call.data.replace('product_wishlist_', ''))
        
        # ተመረጡ ላይ መኖሩን ማረጋገጥ
        result = db.execute(
            "SELECT * FROM wishlists WHERE user_id = ? AND product_id = ?",
            (user_id, product_id)
        ).fetchone()
        
        if result:
            # ካለ ማስወገድ
            db.execute(
                "DELETE FROM wishlists WHERE user_id = ? AND product_id = ?",
                (user_id, product_id)
            )
            bot.answer_callback_query(call.id, "❤️ ከተመረጡ ተወግዷል!")
        else:
            # መጨመር
            db.execute(
                "INSERT INTO wishlists (user_id, product_id) VALUES (?, ?)",
                (user_id, product_id)
            )
            bot.answer_callback_query(call.id, "❤️ ወደ ተመረጡ ተጨምሯል!")
        
        db.log_activity(user_id, 'wishlist', f'ምርት {product_id}')
    
    @bot.callback_query_handler(func=lambda call: call.data == 'show_wishlist')
    def handle_show_wishlist(call: CallbackQuery):
        """ተመረጡን ማሳየት"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        result = db.execute(
            "SELECT p.* FROM wishlists w JOIN products p ON w.product_id = p.id WHERE w.user_id = ?",
            (user_id,)
        ).fetchall()
        
        if not result:
            bot.send_message(
                call.message.chat.id,
                "❤️ ምንም የተመረጡ ምርቶች የሉም"
            )
            bot.answer_callback_query(call.id)
            return
        
        msg = "❤️ *የተመረጡ ምርቶች*\n\n"
        
        for product in result[:10]:
            name = product['name_am'] if lang == 'am' else product['name_en']
            msg += f"🔹 *{name}*\n"
            msg += f"💰 {format_currency(product['price'])} ETB\n"
            msg += f"🆔 /product_{product['id']}\n\n"
        
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton(
                "🔙 ወደ መጀመሪያ",
                callback_data="main_menu"
            )
        )
        
        bot.send_message(
            call.message.chat.id,
            msg,
            reply_markup=markup,
            parse_mode='Markdown'
        )
        bot.answer_callback_query(call.id)
    
    # ==================== ማስታወቂያ ====================
    
    @bot.callback_query_handler(func=lambda call: call.data == 'subscribe')
    def handle_subscribe(call: CallbackQuery):
        """ለማስታወቂያ መመዝገብ"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        db.update_user(user_id, is_subscribed=1)
        bot.answer_callback_query(call.id, "✅ ለማስታወቂያ ተመዝግበዋል!")
        
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        
        from handlers.start import show_welcome
        show_welcome(call.message.chat.id, user_id, db, bot)
    
    @bot.callback_query_handler(func=lambda call: call.data == 'unsubscribe')
    def handle_unsubscribe(call: CallbackQuery):
        """ከማስታወቂያ መውጣት"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        db.update_user(user_id, is_subscribed=0)
        bot.answer_callback_query(call.id, "❌ ከማስታወቂያ ወጥተዋል!")
        
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        
        from handlers.start import show_welcome
        show_welcome(call.message.chat.id, user_id, db, bot)
    
    # ==================== አስተዳዳሪ ጥሪዎች ====================
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('admin_'))
    def handle_admin_callbacks(call: CallbackQuery):
        """የአስተዳዳሪ ጥሪ አያያዝ"""
        from handlers.admin import handle_admin_callbacks
        handle_admin_callbacks(call)
    
    # ==================== ስህተት አያያዝ ====================
    
    @bot.callback_query_handler(func=lambda call: True)
    def handle_unknown_callback(call: CallbackQuery):
        """ያልታወቀ ጥሪ አያያዝ"""
        bot.answer_callback_query(
            call.id, 
            "❌ ይህ ጥሪ ልክ አይደለም ወይም ጊዜው አልፏል!"
        )
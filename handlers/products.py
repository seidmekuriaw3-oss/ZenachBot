# -*- coding: utf-8 -*-

"""
ዘናጭ ቦት - የምርት እጅ አያያዝ
ይህ ፋይል ሁሉንም የምርት እጅ አያያዞችን ይይዛል
"""

import logging
import json
from typing import Optional, Dict, List
from datetime import datetime

from telebot import TeleBot
from telebot.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database import Database
from utils.helpers import get_text, get_user_lang, format_currency
from keyboards.inline import get_product_keyboard, get_rating_keyboard
from services.notifications import notify_admins

logger = logging.getLogger(__name__)

# ለምርት ጊዜያዊ መረጃ
product_cache = {}


def register(bot: TeleBot, db: Database):
    """የምርት እጅ አያያዞችን መመዝገብ"""
    
    # ==================== ምርቶችን በምድብ ማሳየት ====================
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('category_'))
    def handle_category_selection(call: CallbackQuery):
        """የምድብ ምርጫ አያያዝ"""
        user_id = call.from_user.id
        category = call.data.replace('category_', '')
        lang = get_user_lang(db, user_id)
        
        # ምርቶችን ማግኘት
        products = db.get_products(category=category, limit=20, offset=0)
        
        if not products:
            bot.answer_callback_query(
                call.id, 
                get_text(lang, 'no_products_in_category')
            )
            return
        
        # የመጀመሪያውን ምርት ማሳየት
        show_product(call.message.chat.id, products[0], 0, len(products), category, lang, db, bot)
        bot.answer_callback_query(call.id)
    
    # ==================== ምርት ማሳየት ====================
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('product_'))
    def handle_product_navigation(call: CallbackQuery):
        """የምርት አሰሳ አያያዝ"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        # መረጃውን መተንተን
        parts = call.data.split('_')
        action = parts[1]
        
        if action == 'view':
            product_id = int(parts[2])
            product = db.get_product(product_id)
            
            if not product:
                bot.answer_callback_query(call.id, get_text(lang, 'product_not_found'))
                return
            
            # የምርት እይታ መመዝገብ
            db.log_activity(user_id, 'view_product', f'ምርት ID: {product_id}')
            
            # ምርት ማሳየት
            show_product_detail(call.message.chat.id, product, lang, db, bot)
            bot.answer_callback_query(call.id)
        
        elif action == 'nav':
            # አሰሳ: product_nav_category_index
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
        
        elif action == 'buy':
            product_id = int(parts[2])
            product = db.get_product(product_id)
            
            if not product:
                bot.answer_callback_query(call.id, get_text(lang, 'product_not_found'))
                return
            
            if product['stock_quantity'] <= 0:
                bot.answer_callback_query(call.id, get_text(lang, 'out_of_stock'))
                return
            
            # የቁጥር ምርጫ ማሳየት
            show_quantity_selector(call.message.chat.id, product, lang, db, bot)
            bot.answer_callback_query(call.id)
        
        elif action == 'review':
            product_id = int(parts[2])
            product = db.get_product(product_id)
            
            if not product:
                bot.answer_callback_query(call.id, get_text(lang, 'product_not_found'))
                return
            
            # ግምገማ ማሳየት
            show_reviews(call.message.chat.id, product, lang, db, bot)
            bot.answer_callback_query(call.id)
    
    # ==================== የቁጥር ምርጫ ====================
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('qty_'))
    def handle_quantity_selection(call: CallbackQuery):
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
        add_to_cart(user_id, product_id, quantity, db)
        
        bot.answer_callback_query(
            call.id, 
            get_text(lang, 'added_to_cart').format(product['name_am'], quantity)
        )
        
        # የምርት ዝርዝር ማሳየት
        show_product_detail(call.message.chat.id, product, lang, db, bot)
    
    # ==================== ግምገማ ====================
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('rate_'))
    def handle_rating(call: CallbackQuery):
        """የደረጃ ምርጫ አያያዝ"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        parts = call.data.split('_')
        product_id = int(parts[1])
        rating = int(parts[2])
        
        # ተጠቃሚው ይህን ምርት መግዛቱን ማረጋገጥ
        orders = db.get_user_orders(user_id)
        has_purchased = any(
            any(item['product_id'] == product_id for item in db.get_order_items(order['id']))
            for order in orders
        )
        
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
        
        product_id = int(call.data.split('_')[2])
        
        msg = bot.send_message(
            call.message.chat.id,
            "💬 አስተያየትዎን ይጻፉ (ካልፈለጉ 'skip' ይተይቡ):"
        )
        bot.register_next_step_handler(msg, process_review_comment, product_id, db, bot)
        bot.answer_callback_query(call.id)
    
    def process_review_comment(message: Message, product_id: int, db: Database, bot: TeleBot):
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
    
    # ==================== ረዳት ተግባራት ====================
    
    def show_product(chat_id: int, product: Dict, index: int, total: int, 
                     category: str, lang: str, db: Database, bot: TeleBot):
        """ምርት ማሳየት"""
        # የምርት ደረጃ
        rating = product.get('rating_avg', 0)
        rating_count = product.get('rating_count', 0)
        stars = "⭐" * round(rating) if rating else "☆"
        
        # ስም
        name = product['name_am'] if lang == 'am' else product['name_en']
        description = product.get('description_am', '') if lang == 'am' else product.get('description_en', '')
        
        # ሁኔታ
        status = "✅ በክምችት ላይ" if product['stock_quantity'] > 0 else "❌ ተሽጦ አልቋል"
        status_emoji = "✅" if product['stock_quantity'] > 0 else "❌"
        
        # መልዕክት
        msg = f"🔹 *{name}*\n\n"
        
        if description:
            msg += f"📝 {description}\n\n"
        
        msg += f"💰 *ዋጋ:* {format_currency(product['price'])} ETB\n"
        
        if product.get('compare_price'):
            msg += f"~~{format_currency(product['compare_price'])} ETB~~\n"
        
        msg += f"📏 *መጠን:* {product['size']}\n"
        msg += f"📦 *ሁኔታ:* {status}\n"
        msg += f"📊 *ክምችት:* {product['stock_quantity']}\n"
        
        if rating:
            msg += f"⭐ {stars} ({rating_count} {get_text(lang, 'reviews')})\n"
        
        msg += f"\n📌 ({index + 1}/{total})"
        
        # ኪቦርድ
        markup = get_product_keyboard(
            product['id'], 
            category, 
            index, 
            total, 
            product['stock_quantity'] > 0,
            lang
        )
        
        try:
            bot.send_photo(
                chat_id,
                product['image_id'],
                caption=msg,
                reply_markup=markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"ምርት ማሳየት አልተቻለም: {e}")
            bot.send_message(
                chat_id,
                msg,
                reply_markup=markup,
                parse_mode='Markdown'
            )
    
    def show_product_detail(chat_id: int, product: Dict, lang: str, db: Database, bot: TeleBot):
        """የምርት ዝርዝር ማሳየት"""
        # የምርት ደረጃ
        rating = product.get('rating_avg', 0)
        rating_count = product.get('rating_count', 0)
        stars = "⭐" * round(rating) if rating else "☆"
        
        # ስም
        name = product['name_am'] if lang == 'am' else product['name_en']
        description = product.get('description_am', '') if lang == 'am' else product.get('description_en', '')
        
        # ሁኔታ
        status = "✅ በክምችት ላይ" if product['stock_quantity'] > 0 else "❌ ተሽጦ አልቋል"
        
        # መልዕክት
        msg = f"🔹 *{name}*\n\n"
        
        if description:
            msg += f"📝 {description}\n\n"
        
        msg += f"💰 *ዋጋ:* {format_currency(product['price'])} ETB\n"
        
        if product.get('compare_price'):
            msg += f"~~{format_currency(product['compare_price'])} ETB~~\n"
        
        msg += f"📏 *መጠን:* {product['size']}\n"
        msg += f"📦 *ሁኔታ:* {status}\n"
        msg += f"📊 *ክምችት:* {product['stock_quantity']}\n"
        
        if rating:
            msg += f"⭐ {stars} ({rating_count} {get_text(lang, 'reviews')})\n"
        
        # ኪቦርድ
        markup = InlineKeyboardMarkup(row_width=2)
        
        if product['stock_quantity'] > 0:
            markup.add(
                InlineKeyboardButton(
                    "🛒 ለመግዛት",
                    callback_data=f"product_buy_{product['id']}"
                )
            )
        
        markup.add(
            InlineKeyboardButton(
                "⭐ ግምገማ",
                callback_data=f"product_review_{product['id']}"
            ),
            InlineKeyboardButton(
                "❤️ ወደ ተመረጡ",
                callback_data=f"product_wishlist_{product['id']}"
            )
        )
        
        markup.add(
            InlineKeyboardButton(
                "🔙 ወደ ምርቶች",
                callback_data=f"category_{product['category']}"
            )
        )
        
        try:
            bot.send_photo(
                chat_id,
                product['image_id'],
                caption=msg,
                reply_markup=markup,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"ምርት ማሳየት አልተቻለም: {e}")
            bot.send_message(
                chat_id,
                msg,
                reply_markup=markup,
                parse_mode='Markdown'
            )
    
    def show_quantity_selector(chat_id: int, product: Dict, lang: str, db: Database, bot: TeleBot):
        """የቁጥር ምርጫ ማሳየት"""
        max_qty = min(5, product['stock_quantity'])
        
        markup = InlineKeyboardMarkup(row_width=3)
        
        buttons = []
        for i in range(1, max_qty + 1):
            buttons.append(
                InlineKeyboardButton(
                    str(i),
                    callback_data=f"qty_{product['id']}_{i}"
                )
            )
        
        markup.add(*buttons)
        
        markup.add(
            InlineKeyboardButton(
                "🔙 ወደ ምርት",
                callback_data=f"product_view_{product['id']}"
            )
        )
        
        msg = f"🛒 *{product['name_am'] if lang == 'am' else product['name_en']}*\n\n"
        msg += f"💰 ዋጋ: {format_currency(product['price'])} ETB\n"
        msg += f"📦 ክምችት: {product['stock_quantity']}\n\n"
        msg += f"📌 ብዛት ይምረጡ:"
        
        bot.send_message(
            chat_id,
            msg,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    
    def show_reviews(chat_id: int, product: Dict, lang: str, db: Database, bot: TeleBot):
        """የምርት ግምገማዎችን ማሳየት"""
        reviews = db.get_product_reviews(product['id'], limit=10)
        
        msg = f"⭐ *ግምገማዎች ለ {product['name_am'] if lang == 'am' else product['name_en']}*\n\n"
        
        if not reviews:
            msg += get_text(lang, 'no_reviews_yet')
        else:
            for review in reviews[:5]:
                stars = "⭐" * review['rating']
                name = review.get('first_name', 'Anonymous')
                comment = review.get('comment', '')
                
                msg += f"{stars}\n"
                msg += f"👤 {name}\n"
                if comment:
                    msg += f"💬 {comment}\n"
                msg += f"📅 {review['created_at'][:10]}\n\n"
        
        # ግምገማ ለመስጠት ኪቦርድ
        markup = get_rating_keyboard(product['id'], lang)
        
        bot.send_message(
            chat_id,
            msg,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    
    def add_to_cart(user_id: int, product_id: int, quantity: int, db: Database):
        """ምርት ወደ ጋሪ መጨመር"""
        product = db.get_product(product_id)
        
        if not product:
            return False
        
        # የአሁኑን ጋሪ ማግኘት
        cart = db.get_cart(user_id)
        items = cart['items'] if cart and cart.get('items') else []
        
        # ምርቱ በጋሪ ውስጥ መኖሩን ማረጋገጥ
        found = False
        for item in items:
            if item['product_id'] == product_id:
                item['quantity'] += quantity
                found = True
                break
        
        if not found:
            items.append({
                'product_id': product_id,
                'name': product['name_am'],
                'price': product['price'],
                'quantity': quantity,
                'image_id': product['image_id']
            })
        
        # ጋሪ ማዘመን
        return db.update_cart(user_id, items)
    
    # ==================== የምርት ፍለጋ ====================
    
    @bot.message_handler(commands=['search'])
    def search_command(message: Message):
        """የ /search ትዕዛዝ - ምርቶችን መፈለግ"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        
        # የፍለጋ ጥያቄን ማግኘት
        query = message.text.replace('/search', '').strip()
        
        if not query:
            bot.send_message(
                message.chat.id,
                "🔍 ምን መፈለግ ይፈልጋሉ? በ /search ቀጥሎ ይጻፉ\n"
                "ለምሳሌ: /search ቀሚስ"
            )
            return
        
        # ምርቶችን መፈለግ
        products = db.search_products(query, limit=20)
        
        if not products:
            bot.send_message(
                message.chat.id,
                f"🔍 ለ '{query}' ምንም ምርት አልተገኘም"
            )
            return
        
        # ውጤቶችን ማሳየት
        msg = f"🔍 *የፍለጋ ውጤቶች ለ '{query}'*\n\n"
        
        for product in products[:10]:
            name = product['name_am'] if lang == 'am' else product['name_en']
            msg += f"• {name} - {format_currency(product['price'])} ETB\n"
            msg += f"  /product_{product['id']}\n\n"
        
        if len(products) > 10:
            msg += f"\n📌 {len(products)} ምርቶች ተገኝተዋል. ተጨማሪ ለማየት /search ይጠቀሙ"
        
        bot.send_message(
            message.chat.id,
            msg,
            parse_mode='Markdown'
        )
    
    # ==================== የምርት ዝርዝር በትዕዛዝ ====================
    
    @bot.message_handler(commands=['product'])
    def product_command(message: Message):
        """የ /product ትዕዛዝ - ምርት በID ማሳየት"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        
        try:
            product_id = int(message.text.replace('/product', '').strip())
        except ValueError:
            bot.send_message(
                message.chat.id,
                "❌ እባክዎ ትክክለኛ የምርት ID ያስገቡ!\n"
                "ለምሳሌ: /product 123"
            )
            return
        
        product = db.get_product(product_id)
        
        if not product:
            bot.send_message(
                message.chat.id,
                "❌ ምርቱ አልተገኘም!"
            )
            return
        
        show_product_detail(message.chat.id, product, lang, db, bot)
    
    # ==================== ምርቶች በምድብ ትዕዛዝ ====================
    
    @bot.message_handler(commands=['category'])
    def category_command(message: Message):
        """የ /category ትዕዛዝ - ምርቶችን በምድብ ማሳየት"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        
        category = message.text.replace('/category', '').strip()
        
        if not category:
            bot.send_message(
                message.chat.id,
                "📂 የምድብ ስም ያስገቡ!\n"
                "ለምሳሌ: /category Men\n\n"
                "📌 የሚገኙ ምድቦች:\n"
                "• Men\n"
                "• Women\n"
                "• Accessories"
            )
            return
        
        # ምርቶችን ማግኘት
        products = db.get_products(category=category, limit=20, offset=0)
        
        if not products:
            bot.send_message(
                message.chat.id,
                f"📂 በ '{category}' ምድብ ምንም ምርት የለም"
            )
            return
        
        # የመጀመሪያውን ምርት ማሳየት
        show_product(
            message.chat.id, 
            products[0], 
            0, 
            len(products), 
            category, 
            lang, 
            db, 
            bot
        )
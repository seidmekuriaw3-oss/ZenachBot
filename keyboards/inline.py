# -*- coding: utf-8 -*-

"""
ዘናጭ ቦት - Inline ኪቦርዶች
ይህ ፋይል ሁሉንም የ Inline ኪቦርድ መፍጠሪያ ተግባራትን ይይዛል
"""

from typing import Optional, List
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from utils.helpers import get_text


def get_main_keyboard(lang: str = 'am') -> InlineKeyboardMarkup:
    """ዋና Inline ኪቦርድ መፍጠር"""
    markup = InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        InlineKeyboardButton("👕 " + get_text(lang, 'men'), callback_data="category_Men"),
        InlineKeyboardButton("👗 " + get_text(lang, 'women'), callback_data="category_Women")
    )
    
    markup.add(
        InlineKeyboardButton("🛒 " + get_text(lang, 'cart'), callback_data="view_cart"),
        InlineKeyboardButton("📋 " + get_text(lang, 'orders'), callback_data="view_orders")
    )
    
    markup.add(
        InlineKeyboardButton("❤️ " + get_text(lang, 'wishlist'), callback_data="show_wishlist"),
        InlineKeyboardButton("🏷️ " + get_text(lang, 'discounts'), callback_data="show_discounts")
    )
    
    markup.add(
        InlineKeyboardButton("👤 " + get_text(lang, 'profile'), callback_data="view_profile"),
        InlineKeyboardButton("📍 " + get_text(lang, 'contact'), callback_data="view_contact")
    )
    
    return markup


def get_start_keyboard(lang: str = 'am') -> InlineKeyboardMarkup:
    """የመጀመሪያ ማስተዋወቂያ ኪቦርድ መፍጠር"""
    return get_main_keyboard(lang)


def get_back_keyboard(callback_data: str = "main_menu", lang: str = 'am') -> InlineKeyboardMarkup:
    """የመመለሻ ኪቦርድ መፍጠር"""
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(
            "🔙 " + get_text(lang, 'back'),
            callback_data=callback_data
        )
    )
    return markup


def get_product_keyboard(product_id: int, category: str, index: int, total: int, 
                         in_stock: bool = True, lang: str = 'am') -> InlineKeyboardMarkup:
    """የምርት ኪቦርድ መፍጠር"""
    markup = InlineKeyboardMarkup(row_width=2)
    
    # አሰሳ
    nav_buttons = []
    
    if index > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                "⬅️",
                callback_data=f"product_nav_{category}_{index-1}"
            )
        )
    
    nav_buttons.append(
        InlineKeyboardButton(
            f"{index+1}/{total}",
            callback_data="ignore"
        )
    )
    
    if index < total - 1:
        nav_buttons.append(
            InlineKeyboardButton(
                "➡️",
                callback_data=f"product_nav_{category}_{index+1}"
            )
        )
    
    markup.row(*nav_buttons)
    
    # ድርጊቶች
    if in_stock:
        markup.add(
            InlineKeyboardButton(
                "🛒 " + get_text(lang, 'buy'),
                callback_data=f"product_buy_{product_id}"
            )
        )
    
    markup.add(
        InlineKeyboardButton(
            "⭐ " + get_text(lang, 'review'),
            callback_data=f"product_review_{product_id}"
        ),
        InlineKeyboardButton(
            "❤️ " + get_text(lang, 'wishlist'),
            callback_data=f"product_wishlist_{product_id}"
        )
    )
    
    markup.add(
        InlineKeyboardButton(
            "🔙 " + get_text(lang, 'back'),
            callback_data="main_menu"
        )
    )
    
    return markup


def get_rating_keyboard(product_id: int, lang: str = 'am') -> InlineKeyboardMarkup:
    """የደረጃ ምርጫ ኪቦርድ መፍጠር"""
    markup = InlineKeyboardMarkup(row_width=5)
    
    # ደረጃ 1-5
    buttons = []
    for i in range(1, 6):
        buttons.append(
            InlineKeyboardButton(
                f"⭐ {i}",
                callback_data=f"rate_{product_id}_{i}"
            )
        )
    
    markup.add(*buttons)
    
    markup.add(
        InlineKeyboardButton(
            "💬 " + get_text(lang, 'add_comment'),
            callback_data=f"review_comment_{product_id}"
        )
    )
    
    markup.add(
        InlineKeyboardButton(
            "🔙 " + get_text(lang, 'back'),
            callback_data=f"product_view_{product_id}"
        )
    )
    
    return markup


def get_order_keyboard(order_id: int, status: str, lang: str = 'am') -> InlineKeyboardMarkup:
    """የትዕዛዝ ኪቦርድ መፍጠር"""
    markup = InlineKeyboardMarkup(row_width=2)
    
    # የትዕዛዝ ዝርዝር
    markup.add(
        InlineKeyboardButton(
            "📋 " + get_text(lang, 'view_details'),
            callback_data=f"order_{order_id}"
        )
    )
    
    # ሁኔታ ላይ የተመሰረቱ አዝራሮች
    if status == 'Pending':
        markup.add(
            InlineKeyboardButton(
                "❌ " + get_text(lang, 'cancel_order'),
                callback_data=f"order_cancel_{order_id}"
            )
        )
    
    if status in ['Shipped', 'Delivered']:
        markup.add(
            InlineKeyboardButton(
                "✅ " + get_text(lang, 'confirm_receipt'),
                callback_data=f"order_confirm_{order_id}"
            )
        )
    
    markup.add(
        InlineKeyboardButton(
            "🔙 " + get_text(lang, 'back'),
            callback_data="back_to_orders"
        )
    )
    
    return markup


def get_payment_keyboard(lang: str = 'am') -> InlineKeyboardMarkup:
    """የክፍያ ዘዴ ምርጫ ኪቦርድ መፍጠር"""
    markup = InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        InlineKeyboardButton(
            "💳 " + get_text(lang, 'chapa'),
            callback_data="pay_chapa"
        ),
        InlineKeyboardButton(
            "📱 " + get_text(lang, 'telebirr'),
            callback_data="pay_telebirr"
        )
    )
    
    markup.add(
        InlineKeyboardButton(
            "💰 " + get_text(lang, 'cash_on_delivery'),
            callback_data="pay_cash"
        ),
        InlineKeyboardButton(
            "🏦 " + get_text(lang, 'bank_transfer'),
            callback_data="pay_bank"
        )
    )
    
    markup.add(
        InlineKeyboardButton(
            "🔙 " + get_text(lang, 'back'),
            callback_data="checkout"
        )
    )
    
    return markup


def get_confirm_keyboard(action: str, lang: str = 'am') -> InlineKeyboardMarkup:
    """የማረጋገጫ ኪቦርድ መፍጠር"""
    markup = InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        InlineKeyboardButton(
            "✅ " + get_text(lang, 'confirm'),
            callback_data=f"confirm_{action}"
        ),
        InlineKeyboardButton(
            "❌ " + get_text(lang, 'cancel'),
            callback_data=f"cancel_{action}"
        )
    )
    
    return markup


def get_admin_keyboard(lang: str = 'am') -> InlineKeyboardMarkup:
    """የአስተዳዳሪ Inline ኪቦርድ መፍጠር"""
    markup = InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        InlineKeyboardButton("📦 " + get_text(lang, 'products'), callback_data="admin_products"),
        InlineKeyboardButton("📋 " + get_text(lang, 'orders'), callback_data="admin_orders"),
        InlineKeyboardButton("👥 " + get_text(lang, 'users'), callback_data="admin_users"),
        InlineKeyboardButton("📊 " + get_text(lang, 'reports'), callback_data="admin_reports"),
        InlineKeyboardButton("🏷️ " + get_text(lang, 'discounts'), callback_data="admin_discounts"),
        InlineKeyboardButton("⚙️ " + get_text(lang, 'settings'), callback_data="admin_settings"),
        InlineKeyboardButton("🔙 " + get_text(lang, 'back'), callback_data="main_menu")
    )
    
    return markup


def get_pagination_keyboard(base_callback: str, current_page: int, total_pages: int, 
                           lang: str = 'am') -> InlineKeyboardMarkup:
    """የገጽ አሰሳ ኪቦርድ መፍጠር"""
    markup = InlineKeyboardMarkup(row_width=3)
    
    buttons = []
    
    if current_page > 1:
        buttons.append(
            InlineKeyboardButton(
                "⬅️",
                callback_data=f"{base_callback}_{current_page-1}"
            )
        )
    
    buttons.append(
        InlineKeyboardButton(
            f"{current_page}/{total_pages}",
            callback_data="ignore"
        )
    )
    
    if current_page < total_pages:
        buttons.append(
            InlineKeyboardButton(
                "➡️",
                callback_data=f"{base_callback}_{current_page+1}"
            )
        )
    
    markup.row(*buttons)
    return markup


def get_filter_keyboard(filters: List[str], lang: str = 'am') -> InlineKeyboardMarkup:
    """የማጣሪያ ኪቦርድ መፍጠር"""
    markup = InlineKeyboardMarkup(row_width=2)
    
    for filter_name in filters:
        markup.add(
            InlineKeyboardButton(
                filter_name,
                callback_data=f"filter_{filter_name}"
            )
        )
    
    markup.add(
        InlineKeyboardButton(
            "🔙 " + get_text(lang, 'back'),
            callback_data="main_menu"
        )
    )
    
    return markup


def get_social_keyboard(lang: str = 'am') -> InlineKeyboardMarkup:
    """የማህበራዊ መገናኛ ኪቦርድ መፍጠር"""
    markup = InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        InlineKeyboardButton(
            "📱 " + get_text(lang, 'telegram'),
            url="https://t.me/zenach_bot"
        ),
        InlineKeyboardButton(
            "📸 " + get_text(lang, 'instagram'),
            url="https://instagram.com/zenach"
        )
    )
    
    markup.add(
        InlineKeyboardButton(
            "📘 " + get_text(lang, 'facebook'),
            url="https://facebook.com/zenach"
        ),
        InlineKeyboardButton(
            "🐦 " + get_text(lang, 'twitter'),
            url="https://twitter.com/zenach"
        )
    )
    
    markup.add(
        InlineKeyboardButton(
            "🔙 " + get_text(lang, 'back'),
            callback_data="main_menu"
        )
    )
    
    return markup
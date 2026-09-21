# -*- coding: utf-8 -*-

"""
ዘናጭ ቦት - የአስተዳዳሪ ኪቦርዶች
ይህ ፋይል ሁሉንም የአስተዳዳሪ ኪቦርድ መፍጠሪያ ተግባራትን ይይዛል
"""

from typing import Optional, List, Dict
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from utils.helpers import get_text


def get_admin_main_keyboard(lang: str = 'am') -> InlineKeyboardMarkup:
    """ዋና የአስተዳዳሪ ኪቦርድ መፍጠር"""
    markup = InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        InlineKeyboardButton("📦 " + get_text(lang, 'products'), callback_data="admin_products"),
        InlineKeyboardButton("📋 " + get_text(lang, 'orders'), callback_data="admin_orders"),
        InlineKeyboardButton("👥 " + get_text(lang, 'users'), callback_data="admin_users"),
        InlineKeyboardButton("📊 " + get_text(lang, 'reports'), callback_data="admin_reports"),
        InlineKeyboardButton("🏷️ " + get_text(lang, 'discounts'), callback_data="admin_discounts"),
        InlineKeyboardButton("⚙️ " + get_text(lang, 'settings'), callback_data="admin_settings"),
        InlineKeyboardButton("📢 " + get_text(lang, 'broadcast'), callback_data="admin_broadcast"),
        InlineKeyboardButton("🔙 " + get_text(lang, 'back'), callback_data="main_menu")
    )
    
    return markup


def get_admin_products_keyboard(lang: str = 'am') -> InlineKeyboardMarkup:
    """የምርት አስተዳደር ኪቦርድ መፍጠር"""
    markup = InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        InlineKeyboardButton("➕ " + get_text(lang, 'add_product'), callback_data="admin_add_product"),
        InlineKeyboardButton("📋 " + get_text(lang, 'list_products'), callback_data="admin_list_products"),
        InlineKeyboardButton("✏️ " + get_text(lang, 'edit_product'), callback_data="admin_edit_product"),
        InlineKeyboardButton("🗑️ " + get_text(lang, 'delete_product'), callback_data="admin_delete_product"),
        InlineKeyboardButton("📊 " + get_text(lang, 'low_stock'), callback_data="admin_low_stock"),
        InlineKeyboardButton("📦 " + get_text(lang, 'categories'), callback_data="admin_categories"),
        InlineKeyboardButton("🔙 " + get_text(lang, 'back'), callback_data="admin_back")
    )
    
    return markup


def get_admin_orders_keyboard(lang: str = 'am') -> InlineKeyboardMarkup:
    """የትዕዛዝ አስተዳደር ኪቦርድ መፍጠር"""
    markup = InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        InlineKeyboardButton("📋 " + get_text(lang, 'all_orders'), callback_data="admin_all_orders"),
        InlineKeyboardButton("⏳ " + get_text(lang, 'pending_orders'), callback_data="admin_pending_orders"),
        InlineKeyboardButton("🔄 " + get_text(lang, 'processing_orders'), callback_data="admin_processing_orders"),
        InlineKeyboardButton("🚚 " + get_text(lang, 'shipped_orders'), callback_data="admin_shipped_orders"),
        InlineKeyboardButton("✅ " + get_text(lang, 'completed_orders'), callback_data="admin_completed_orders"),
        InlineKeyboardButton("❌ " + get_text(lang, 'cancelled_orders'), callback_data="admin_cancelled_orders"),
        InlineKeyboardButton("🔙 " + get_text(lang, 'back'), callback_data="admin_back")
    )
    
    return markup


def get_admin_users_keyboard(lang: str = 'am') -> InlineKeyboardMarkup:
    """የተጠቃሚ አስተዳደር ኪቦርድ መፍጠር"""
    markup = InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        InlineKeyboardButton("👥 " + get_text(lang, 'all_users'), callback_data="admin_all_users"),
        InlineKeyboardButton("📊 " + get_text(lang, 'active_users'), callback_data="admin_active_users"),
        InlineKeyboardButton("📢 " + get_text(lang, 'broadcast'), callback_data="admin_broadcast"),
        InlineKeyboardButton("🔍 " + get_text(lang, 'find_user'), callback_data="admin_find_user"),
        InlineKeyboardButton("📋 " + get_text(lang, 'user_stats'), callback_data="admin_user_stats"),
        InlineKeyboardButton("🔙 " + get_text(lang, 'back'), callback_data="admin_back")
    )
    
    return markup


def get_admin_reports_keyboard(lang: str = 'am') -> InlineKeyboardMarkup:
    """የሪፖርት ኪቦርድ መፍጠር"""
    markup = InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        InlineKeyboardButton("📊 " + get_text(lang, 'sales_report'), callback_data="admin_sales_report"),
        InlineKeyboardButton("🏆 " + get_text(lang, 'top_products'), callback_data="admin_top_products"),
        InlineKeyboardButton("📈 " + get_text(lang, 'daily_report'), callback_data="admin_daily_report"),
        InlineKeyboardButton("📊 " + get_text(lang, 'category_report'), callback_data="admin_category_report"),
        InlineKeyboardButton("👥 " + get_text(lang, 'user_report'), callback_data="admin_user_report"),
        InlineKeyboardButton("📋 " + get_text(lang, 'detailed_report'), callback_data="admin_detailed_report"),
        InlineKeyboardButton("🔙 " + get_text(lang, 'back'), callback_data="admin_back")
    )
    
    return markup


def get_admin_discounts_keyboard(lang: str = 'am') -> InlineKeyboardMarkup:
    """የቅናሽ አስተዳደር ኪቦርድ መፍጠር"""
    markup = InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        InlineKeyboardButton("➕ " + get_text(lang, 'add_discount'), callback_data="admin_add_discount"),
        InlineKeyboardButton("📋 " + get_text(lang, 'list_discounts'), callback_data="admin_list_discounts"),
        InlineKeyboardButton("✏️ " + get_text(lang, 'edit_discount'), callback_data="admin_edit_discount"),
        InlineKeyboardButton("🗑️ " + get_text(lang, 'delete_discount'), callback_data="admin_delete_discount"),
        InlineKeyboardButton("🔙 " + get_text(lang, 'back'), callback_data="admin_back")
    )
    
    return markup


def get_admin_settings_keyboard(lang: str = 'am') -> InlineKeyboardMarkup:
    """የቅንብር ኪቦርድ መፍጠር"""
    markup = InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        InlineKeyboardButton("🌍 " + get_text(lang, 'language'), callback_data="admin_language"),
        InlineKeyboardButton("🔔 " + get_text(lang, 'notifications'), callback_data="admin_notifications"),
        InlineKeyboardButton("💰 " + get_text(lang, 'payment_settings'), callback_data="admin_payment"),
        InlineKeyboardButton("📦 " + get_text(lang, 'shipping_settings'), callback_data="admin_shipping"),
        InlineKeyboardButton("🛡️ " + get_text(lang, 'security'), callback_data="admin_security"),
        InlineKeyboardButton("💾 " + get_text(lang, 'backup'), callback_data="admin_backup"),
        InlineKeyboardButton("🔙 " + get_text(lang, 'back'), callback_data="admin_back")
    )
    
    return markup


def get_admin_order_detail_keyboard(order_id: int, status: str, lang: str = 'am') -> InlineKeyboardMarkup:
    """የትዕዛዝ ዝርዝር አስተዳደር ኪቦርድ መፍጠር"""
    markup = InlineKeyboardMarkup(row_width=2)
    
    # የሁኔታ ለውጥ አዝራሮች
    status_buttons = []
    
    if status != 'Processing':
        status_buttons.append(
            InlineKeyboardButton(
                "🔄 " + get_text(lang, 'processing'),
                callback_data=f"admin_order_status_{order_id}_Processing"
            )
        )
    
    if status != 'Shipped':
        status_buttons.append(
            InlineKeyboardButton(
                "🚚 " + get_text(lang, 'shipped'),
                callback_data=f"admin_order_status_{order_id}_Shipped"
            )
        )
    
    if status != 'Delivered':
        status_buttons.append(
            InlineKeyboardButton(
                "✅ " + get_text(lang, 'delivered'),
                callback_data=f"admin_order_status_{order_id}_Delivered"
            )
        )
    
    if status != 'Cancelled':
        status_buttons.append(
            InlineKeyboardButton(
                "❌ " + get_text(lang, 'cancel'),
                callback_data=f"admin_order_status_{order_id}_Cancelled"
            )
        )
    
    if status_buttons:
        markup.add(*status_buttons[:2])
        if len(status_buttons) > 2:
            markup.add(*status_buttons[2:])
    
    # ተጨማሪ አዝራሮች
    markup.add(
        InlineKeyboardButton(
            "👤 " + get_text(lang, 'view_user'),
            callback_data=f"admin_user_{order_id}"
        ),
        InlineKeyboardButton(
            "📝 " + get_text(lang, 'add_note'),
            callback_data=f"admin_order_note_{order_id}"
        )
    )
    
    markup.add(
        InlineKeyboardButton(
            "📄 " + get_text(lang, 'print_invoice'),
            callback_data=f"admin_order_invoice_{order_id}"
        ),
        InlineKeyboardButton(
            "📧 " + get_text(lang, 'email_customer'),
            callback_data=f"admin_order_email_{order_id}"
        )
    )
    
    markup.add(
        InlineKeyboardButton(
            "🔙 " + get_text(lang, 'back'),
            callback_data="admin_back"
        )
    )
    
    return markup


def get_admin_user_detail_keyboard(user_id: int, lang: str = 'am') -> InlineKeyboardMarkup:
    """የተጠቃሚ ዝርዝር አስተዳደር ኪቦርድ መፍጠር"""
    markup = InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        InlineKeyboardButton(
            "📋 " + get_text(lang, 'view_orders'),
            callback_data=f"admin_user_orders_{user_id}"
        ),
        InlineKeyboardButton(
            "✏️ " + get_text(lang, 'edit_user'),
            callback_data=f"admin_edit_user_{user_id}"
        )
    )
    
    markup.add(
        InlineKeyboardButton(
            "🚫 " + get_text(lang, 'ban_user'),
            callback_data=f"admin_ban_user_{user_id}"
        ),
        InlineKeyboardButton(
            "🔓 " + get_text(lang, 'unban_user'),
            callback_data=f"admin_unban_user_{user_id}"
        )
    )
    
    markup.add(
        InlineKeyboardButton(
            "📢 " + get_text(lang, 'send_message'),
            callback_data=f"admin_msg_user_{user_id}"
        ),
        InlineKeyboardButton(
            "🔙 " + get_text(lang, 'back'),
            callback_data="admin_back"
        )
    )
    
    return markup


def get_admin_broadcast_keyboard(lang: str = 'am') -> InlineKeyboardMarkup:
    """የማስታወቂያ መላክ ኪቦርድ መፍጠር"""
    markup = InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        InlineKeyboardButton("📢 " + get_text(lang, 'send_to_all'), callback_data="admin_broadcast_all"),
        InlineKeyboardButton("👥 " + get_text(lang, 'send_to_active'), callback_data="admin_broadcast_active"),
        InlineKeyboardButton("📋 " + get_text(lang, 'send_to_subscribers'), callback_data="admin_broadcast_subscribers"),
        InlineKeyboardButton("🔙 " + get_text(lang, 'back'), callback_data="admin_back")
    )
    
    return markup


def get_admin_confirmation_keyboard(action: str, item_id: int, lang: str = 'am') -> InlineKeyboardMarkup:
    """የአስተዳዳሪ ማረጋገጫ ኪቦርድ መፍጠር"""
    markup = InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        InlineKeyboardButton(
            "✅ " + get_text(lang, 'confirm'),
            callback_data=f"admin_confirm_{action}_{item_id}"
        ),
        InlineKeyboardButton(
            "❌ " + get_text(lang, 'cancel'),
            callback_data=f"admin_cancel_{action}_{item_id}"
        )
    )
    
    return markup


def get_admin_pagination_keyboard(base_callback: str, current_page: int, total_pages: int,
                                  lang: str = 'am') -> InlineKeyboardMarkup:
    """የአስተዳዳሪ ገጽ አሰሳ ኪቦርድ መፍጠር"""
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
    
    if buttons:
        markup.row(*buttons)
    
    markup.add(
        InlineKeyboardButton(
            "🔙 " + get_text(lang, 'back'),
            callback_data="admin_back"
        )
    )
    
    return markup


def get_admin_filter_keyboard(filters: List[Dict], lang: str = 'am') -> InlineKeyboardMarkup:
    """የአስተዳዳሪ ማጣሪያ ኪቦርድ መፍጠር"""
    markup = InlineKeyboardMarkup(row_width=2)
    
    for filter_item in filters:
        label = filter_item.get('label', '')
        value = filter_item.get('value', '')
        is_active = filter_item.get('active', False)
        
        if is_active:
            label = f"✅ {label}"
        
        markup.add(
            InlineKeyboardButton(
                label,
                callback_data=f"admin_filter_{value}"
            )
        )
    
    markup.add(
        InlineKeyboardButton(
            "🔙 " + get_text(lang, 'back'),
            callback_data="admin_back"
        )
    )
    
    return markup
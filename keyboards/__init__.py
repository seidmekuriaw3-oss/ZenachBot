# -*- coding: utf-8 -*-

"""
ዘናጭ ቦት - የኪቦርድ ሞጁል
ይህ ፋይል ሁሉንም የኪቦርድ ሞጁሎችን ያስመጣል
"""

from .reply import (
    get_main_menu,
    get_admin_menu,
    get_language_menu,
    get_contact_menu,
    get_cancel_menu
)

from .inline import (
    get_product_keyboard,
    get_rating_keyboard,
    get_order_keyboard,
    get_payment_keyboard,
    get_admin_keyboard,
    get_confirm_keyboard,
    get_main_keyboard,
    get_back_keyboard
)

from .admin import (
    get_admin_main_keyboard,
    get_admin_products_keyboard,
    get_admin_orders_keyboard,
    get_admin_users_keyboard,
    get_admin_reports_keyboard,
    get_admin_discounts_keyboard
)

__all__ = [
    # Reply keyboards
    'get_main_menu',
    'get_admin_menu',
    'get_language_menu',
    'get_contact_menu',
    'get_cancel_menu',
    
    # Inline keyboards
    'get_product_keyboard',
    'get_rating_keyboard',
    'get_order_keyboard',
    'get_payment_keyboard',
    'get_admin_keyboard',
    'get_confirm_keyboard',
    'get_main_keyboard',
    'get_back_keyboard',
    
    # Admin keyboards
    'get_admin_main_keyboard',
    'get_admin_products_keyboard',
    'get_admin_orders_keyboard',
    'get_admin_users_keyboard',
    'get_admin_reports_keyboard',
    'get_admin_discounts_keyboard'
]
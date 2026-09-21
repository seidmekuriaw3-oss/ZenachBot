# -*- coding: utf-8 -*-

"""
ዘናጭ ቦት - የማስታወቂያ አገልግሎት
ይህ ፋይል ሁሉንም የማስታወቂያ ተዛማጅ ተግባራትን ይይዛል
"""

import logging
import time
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any
from telebot import TeleBot

from database import Database
from config import config
from utils.helpers import get_text, format_currency
from utils.logger import get_logger

logger = get_logger('notifications')


def notify_admin(bot: TeleBot, message: str, parse_mode: str = 'Markdown'):
    """ለአስተዳዳሪዎች መልዕክት መላክ"""
    for admin_id in config.bot.ADMIN_IDS:
        try:
            bot.send_message(admin_id, message, parse_mode=parse_mode)
        except Exception as e:
            logger.error(f"ለአስተዳዳሪ {admin_id} መልዕክት መላክ አልተቻለም: {e}")


def notify_admins(bot: TeleBot, message: str, parse_mode: str = 'Markdown'):
    """ለሁሉም አስተዳዳሪዎች መልዕክት መላክ"""
    notify_admin(bot, message, parse_mode)


def send_broadcast(bot: TeleBot, db: Database, message: str, 
                   image_id: Optional[str] = None,
                   target: str = 'all',
                   parse_mode: str = 'Markdown'):
    """
    ለተጠቃሚዎች ማስታወቂያ መላክ
    
    Args:
        bot: የቴሌግራም ቦት ነገር
        db: የውሂብ ጎታ ነገር
        message: መልዕክቱ
        image_id: የፎቶ ID (አማራጭ)
        target: ዒላማ ('all', 'subscribers', 'active')
        parse_mode: የመልዕክት ፎርማት
    """
    # ተጠቃሚዎችን ማግኘት
    if target == 'all':
        users = db.get_all_users()
    elif target == 'subscribers':
        users = db.get_subscribed_users()
    elif target == 'active':
        users = db.get_active_users(days=7)
    else:
        users = []
    
    if not users:
        logger.warning("ምንም ተጠቃሚዎች አልተገኙም")
        return
    
    # ማስታወቂያ መመዝገብ
    notification_id = db.create_notification(
        title_am="ማስታወቂያ",
        title_en="Broadcast",
        message_am=message,
        message_en=message,
        image_id=image_id
    )
    
    # በቡድን መላክ
    batch_size = config.notification.NOTIFICATION_BATCH_SIZE
    total = len(users)
    sent = 0
    failed = 0
    
    for i, user in enumerate(users):
        try:
            if image_id:
                bot.send_photo(
                    user['user_id'],
                    image_id,
                    caption=message,
                    parse_mode=parse_mode
                )
            else:
                bot.send_message(
                    user['user_id'],
                    message,
                    parse_mode=parse_mode
                )
            sent += 1
            
            # በቡድን መላክ ለማቆም ትንሽ ጊዜ
            if (i + 1) % batch_size == 0:
                time.sleep(1)
                
        except Exception as e:
            failed += 1
            logger.error(f"ለተጠቃሚ {user['user_id']} መልዕክት መላክ አልተቻለም: {e}")
    
    # ማስታወቂያ ማዘመን
    db.mark_notification_sent(notification_id)
    db.update_notification_stats(notification_id, sent, failed)
    
    logger.info(f"ማስታወቂያ ተልኳል: {sent} ተላኩ, {failed} አልተላኩም")
    
    # ለአስተዳዳሪ ማሳወቅ
    notify_admins(
        bot,
        f"📢 *ማስታወቂያ ተልኳል!*\n\n"
        f"👥 አጠቃላይ: {total}\n"
        f"✅ የተላኩ: {sent}\n"
        f"❌ ያልተላኩ: {failed}\n"
        f"🎯 ዒላማ: {target}"
    )


def send_order_confirmation(bot: TeleBot, order_id: int, db: Database):
    """የትዕዛዝ ማረጋገጫ መልዕክት መላክ"""
    order = db.get_order(order_id)
    
    if not order:
        logger.error(f"ትዕዛዝ {order_id} አልተገኘም")
        return
    
    user = db.get_user(order['user_id'])
    if not user:
        logger.error(f"ተጠቃሚ {order['user_id']} አልተገኘም")
        return
    
    lang = user.get('lang', 'am')
    items = db.get_order_items(order_id)
    
    # መልዕክት መፍጠር
    msg = f"✅ *{get_text(lang, 'order_confirmation')}*\n\n"
    msg += f"🔢 {get_text(lang, 'order_number')}: {order['order_number']}\n"
    msg += f"📅 {get_text(lang, 'order_date')}: {order['order_date']}\n\n"
    
    msg += f"*{get_text(lang, 'order_items')}:*\n"
    for item in items:
        product = db.get_product(item['product_id'])
        name = product['name_am'] if product else 'N/A'
        msg += f"• {name} × {item['quantity']} = {format_currency(item['total_price'])} ETB\n"
    
    msg += f"\n💰 {get_text(lang, 'total')}: {format_currency(order['final_amount'])} ETB\n"
    
    if order['shipping_address']:
        msg += f"\n📍 {get_text(lang, 'shipping_address')}: {order['shipping_address']}"
    
    msg += f"\n\n📌 {get_text(lang, 'order_status')}: {order['status']}\n"
    msg += f"📋 {get_text(lang, 'track_order')}: /orders"
    
    try:
        bot.send_message(
            user['user_id'],
            msg,
            parse_mode='Markdown'
        )
        logger.info(f"የትዕዛዝ ማረጋገጫ ለ {order['user_id']} ተልኳል")
    except Exception as e:
        logger.error(f"የትዕዛዝ ማረጋገጫ መላክ አልተቻለም: {e}")


def send_payment_confirmation(bot: TeleBot, payment_id: int, db: Database):
    """የክፍያ ማረጋገጫ መልዕክት መላክ"""
    # ክፍያ ማግኘት
    payment = db.get_payment(payment_id)
    
    if not payment:
        logger.error(f"ክፍያ {payment_id} አልተገኘም")
        return
    
    user = db.get_user(payment['user_id'])
    if not user:
        logger.error(f"ተጠቃሚ {payment['user_id']} አልተገኘም")
        return
    
    lang = user.get('lang', 'am')
    
    # መልዕክት መፍጠር
    msg = f"✅ *{get_text(lang, 'payment_confirmation')}*\n\n"
    msg += f"💰 {get_text(lang, 'amount')}: {format_currency(payment['amount'])} ETB\n"
    msg += f"💳 {get_text(lang, 'method')}: {payment['method']}\n"
    msg += f"🔢 {get_text(lang, 'transaction_id')}: {payment['transaction_id']}\n"
    msg += f"📅 {get_text(lang, 'date')}: {payment['completed_at'] or payment['created_at']}\n\n"
    msg += f"📌 {get_text(lang, 'payment_status')}: {payment['status']}"
    
    try:
        bot.send_message(
            user['user_id'],
            msg,
            parse_mode='Markdown'
        )
        logger.info(f"የክፍያ ማረጋገጫ ለ {payment['user_id']} ተልኳል")
    except Exception as e:
        logger.error(f"የክፍያ ማረጋገጫ መላክ አልተቻለም: {e}")


def send_welcome_message(bot: TeleBot, user_id: int, db: Database):
    """የእንኳን ደህና መጡ መልዕክት መላክ"""
    user = db.get_user(user_id)
    
    if not user:
        logger.error(f"ተጠቃሚ {user_id} አልተገኘም")
        return
    
    lang = user.get('lang', 'am')
    
    msg = f"👋 *{get_text(lang, 'welcome')}*\n\n"
    msg += f"{get_text(lang, 'welcome_message')}\n\n"
    msg += f"📌 {get_text(lang, 'start_shopping')}\n"
    msg += f"💡 {get_text(lang, 'use_commands')}"
    
    try:
        bot.send_message(
            user_id,
            msg,
            parse_mode='Markdown'
        )
        logger.info(f"የእንኳን ደህና መጡ መልዕክት ለ {user_id} ተልኳል")
    except Exception as e:
        logger.error(f"የእንኳን ደህና መጡ መልዕክት መላክ አልተቻለም: {e}")


def send_product_notification(bot: TeleBot, product_id: int, db: Database):
    """አዲስ ምርት ሲጨመር ለተመዝጋቢዎች ማሳወቂያ መላክ"""
    product = db.get_product(product_id)
    
    if not product:
        logger.error(f"ምርት {product_id} አልተገኘም")
        return
    
    subscribers = db.get_subscribed_users()
    
    if not subscribers:
        logger.info("ምንም ተመዝጋቢዎች የሉም")
        return
    
    # በቡድን መላክ
    batch_size = config.notification.NOTIFICATION_BATCH_SIZE
    sent = 0
    
    for i, user in enumerate(subscribers):
        try:
            lang = user.get('lang', 'am')
            name = product['name_am'] if lang == 'am' else product['name_en']
            
            msg = f"🆕 *{get_text(lang, 'new_product')}*\n\n"
            msg += f"📦 {name}\n"
            msg += f"💰 {get_text(lang, 'price')}: {format_currency(product['price'])} ETB\n"
            msg += f"📏 {get_text(lang, 'size')}: {product['size']}\n\n"
            msg += f"👉 /product_{product_id} {get_text(lang, 'view_product')}"
            
            bot.send_photo(
                user['user_id'],
                product['image_id'],
                caption=msg,
                parse_mode='Markdown'
            )
            sent += 1
            
            # በቡድን መላክ ለማቆም
            if (i + 1) % batch_size == 0:
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"ለተጠቃሚ {user['user_id']} ማስታወቂያ መላክ አልተቻለም: {e}")
    
    logger.info(f"የምርት ማስታወቂያ ለ {sent} ተጠቃሚዎች ተልኳል")


def send_order_update(bot: TeleBot, order_id: int, db: Database):
    """የትዕዛዝ ሁኔታ ሲቀየር ለተጠቃሚ ማሳወቂያ መላክ"""
    order = db.get_order(order_id)
    
    if not order:
        logger.error(f"ትዕዛዝ {order_id} አልተገኘም")
        return
    
    user = db.get_user(order['user_id'])
    if not user:
        logger.error(f"ተጠቃሚ {order['user_id']} አልተገኘም")
        return
    
    lang = user.get('lang', 'am')
    
    # የሁኔታ ኢሞጂ
    status_emoji = {
        'Pending': '⏳',
        'Processing': '🔄',
        'Shipped': '🚚',
        'Delivered': '✅',
        'Cancelled': '❌'
    }.get(order['status'], '📦')
    
    msg = f"{status_emoji} *{get_text(lang, 'order_update')}*\n\n"
    msg += f"🔢 {get_text(lang, 'order_number')}: {order['order_number']}\n"
    msg += f"📦 {get_text(lang, 'status')}: {order['status']}\n"
    msg += f"📅 {get_text(lang, 'updated')}: {order['updated_at']}\n\n"
    
    if order['status'] == 'Shipped':
        msg += f"🚚 {get_text(lang, 'order_shipped')}\n"
    elif order['status'] == 'Delivered':
        msg += f"✅ {get_text(lang, 'order_delivered')}\n"
    
    msg += f"\n📋 /orders {get_text(lang, 'view_orders')}"
    
    try:
        bot.send_message(
            user['user_id'],
            msg,
            parse_mode='Markdown'
        )
        logger.info(f"የትዕዛዝ ማሳወቂያ ለ {order['user_id']} ተልኳል")
    except Exception as e:
        logger.error(f"የትዕዛዝ ማሳወቂያ መላክ አልተቻለም: {e}")
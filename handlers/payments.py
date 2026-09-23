# -*- coding: utf-8 -*-

"""
ዘናጭ ቦት - የክፍያ እጅ አያያዝ
ይህ ፋይል ሁሉንም የክፍያ ተዛማጅ እጅ አያያዞችን ይይዛል
"""

import logging
import json
import hashlib
import hmac
from datetime import datetime
from typing import Optional, Dict, Any

from telebot import TeleBot
from telebot.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from database import Database
from utils.helpers import get_text, get_user_lang, format_currency, generate_order_number
from services.payments import PaymentService
from services.notifications import notify_admins, send_order_confirmation
from config import config

logger = logging.getLogger(__name__)

# የክፍያ ሁኔታዎች
PAYMENT_STATUS = {
    'pending': '⏳ ',
    'processing': '🔄 ',
    'completed': '✅ ',
    'failed': '❌ ',
    'cancelled': '🚫 ',
    'refunded': '💰 '
}

# የክፍያ ዘዴዎች
PAYMENT_METHODS = {
    'chapa': '💳 Chapa',
    'telebirr': '📱 Telebirr',
    'cash': '💰 Cash',
    'bank': '🏦 Bank Transfer'
}


def register(bot: TeleBot, db: Database):
    """የክፍያ እጅ አያያዞችን መመዝገብ"""
    
    # የክፍያ አገልግሎት መፍጠር
    payment_service = PaymentService(db)

    def get_owned_payment(payment_id: int, user_id: int) -> Optional[Dict]:
        payment = payment_service.get_payment(payment_id)
        if not payment or int(payment.get('user_id', -1)) != user_id:
            return None
        return payment
    
    # ==================== የክፍያ ምርጫ ====================
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('pay_'))
    def handle_payment_method(call: CallbackQuery):
        """የክፍያ ዘዴ ምርጫ አያያዝ"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        method = call.data.replace('pay_', '')
        
        # የትዕዛዝ መረጃ ማግኘት
        order_data = get_order_data(user_id)
        
        if not order_data:
            bot.send_message(
                call.message.chat.id,
                "❌ " + get_text(lang, 'order_not_found')
            )
            bot.answer_callback_query(call.id)
            return
        
        # ክፍያ መፍጠር
        payment = payment_service.create_payment(
            user_id=user_id,
            order_id=order_data.get('order_id'),
            amount=order_data.get('final'),
            method=method,
            currency='ETB'
        )
        
        if not payment:
            bot.send_message(
                call.message.chat.id,
                "❌ " + get_text(lang, 'payment_error')
            )
            bot.answer_callback_query(call.id)
            return
        
        # በክፍያ ዘዴ ላይ የተመሰረተ ሂደት
        if method == 'chapa':
            process_chapa_payment(call.message, payment, db, bot)
        elif method == 'telebirr':
            process_telebirr_payment(call.message, payment, db, bot)
        elif method == 'cash':
            process_cash_payment(call.message, payment, db, bot)
        elif method == 'bank':
            process_bank_payment(call.message, payment, db, bot)
        else:
            bot.send_message(
                call.message.chat.id,
                "❌ " + get_text(lang, 'invalid_payment_method')
            )
        
        bot.answer_callback_query(call.id)
    
    # ==================== ቻፓ ክፍያ ====================
    
    def process_chapa_payment(message: Message, payment: Dict, db: Database, bot: TeleBot):
        """ቻፓ ክፍያ ማስኬድ"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        
        # የቻፓ ክፍያ ጅምር
        result = payment_service.initiate_chapa_payment(payment)
        
        if not result:
            bot.send_message(
                message.chat.id,
                "❌ " + get_text(lang, 'chapa_error')
            )
            return
        
        # የክፍያ ገጽ አገናኝ
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton(
                "💳 " + get_text(lang, 'pay_now'),
                url=result.get('checkout_url')
            ),
            InlineKeyboardButton(
                "✅ " + get_text(lang, 'verify_payment'),
                callback_data=f"verify_payment_{payment['id']}"
            ),
            InlineKeyboardButton(
                "❌ " + get_text(lang, 'cancel_payment'),
                callback_data=f"cancel_payment_{payment['id']}"
            )
        )
        
        msg = f"💳 *{get_text(lang, 'chapa_payment')}*\n\n"
        msg += f"💰 {get_text(lang, 'amount')}: {format_currency(payment['amount'])} ETB\n"
        msg += f"🔢 {get_text(lang, 'transaction_id')}: {payment['transaction_id']}\n\n"
        msg += f"📌 {get_text(lang, 'click_to_pay')}\n"
        msg += f"🔗 {get_text(lang, 'payment_link')}: {result.get('checkout_url')}"
        
        bot.send_message(
            message.chat.id,
            msg,
            reply_markup=markup,
            parse_mode='Markdown'
        )
        
        # ለአስተዳዳሪ ማሳወቅ
        notify_admins(
            bot,
            f"💳 *{get_text(lang, 'new_payment')}*\n\n"
            f"👤 {get_text(lang, 'user')}: {message.from_user.first_name}\n"
            f"💰 {get_text(lang, 'amount')}: {format_currency(payment['amount'])} ETB\n"
            f"🔢 {get_text(lang, 'transaction_id')}: {payment['transaction_id']}\n"
            f"💳 {get_text(lang, 'method')}: Chapa"
        )
    
    # ==================== ቴሌብር ክፍያ ====================
    
    def process_telebirr_payment(message: Message, payment: Dict, db: Database, bot: TeleBot):
        """ቴሌብር ክፍያ ማስኬድ"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        
        # የቴሌብር ክፍያ ጅምር
        result = payment_service.initiate_telebirr_payment(payment)
        
        if not result:
            bot.send_message(
                message.chat.id,
                "❌ " + get_text(lang, 'telebirr_error')
            )
            return
        
        # የክፍያ መመሪያ
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton(
                "📱 " + get_text(lang, 'pay_with_telebirr'),
                url=result.get('payment_url')
            ),
            InlineKeyboardButton(
                "✅ " + get_text(lang, 'verify_payment'),
                callback_data=f"verify_payment_{payment['id']}"
            ),
            InlineKeyboardButton(
                "❌ " + get_text(lang, 'cancel_payment'),
                callback_data=f"cancel_payment_{payment['id']}"
            )
        )
        
        msg = f"📱 *{get_text(lang, 'telebirr_payment')}*\n\n"
        msg += f"💰 {get_text(lang, 'amount')}: {format_currency(payment['amount'])} ETB\n"
        msg += f"🔢 {get_text(lang, 'transaction_id')}: {payment['transaction_id']}\n\n"
        msg += f"📌 {get_text(lang, 'telebirr_instructions')}\n"
        msg += f"🔗 {get_text(lang, 'payment_link')}: {result.get('payment_url')}"
        
        bot.send_message(
            message.chat.id,
            msg,
            reply_markup=markup,
            parse_mode='Markdown'
        )
        
        # ለአስተዳዳሪ ማሳወቅ
        notify_admins(
            bot,
            f"📱 *{get_text(lang, 'new_payment')}*\n\n"
            f"👤 {get_text(lang, 'user')}: {message.from_user.first_name}\n"
            f"💰 {get_text(lang, 'amount')}: {format_currency(payment['amount'])} ETB\n"
            f"🔢 {get_text(lang, 'transaction_id')}: {payment['transaction_id']}\n"
            f"📱 {get_text(lang, 'method')}: Telebirr"
        )
    
    # ==================== ጥሬ ገንዘብ ክፍያ ====================
    
    def process_cash_payment(message: Message, payment: Dict, db: Database, bot: TeleBot):
        """ጥሬ ገንዘብ ክፍያ ማስኬድ"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        
        # ክፍያ ማረጋገጥ
        payment_service.verify_payment(payment['id'])
        
        # ትዕዛዝ ማረጋገጥ
        order_id = payment.get('order_id')
        if order_id:
            db.update_order_status(order_id, 'Processing')
        
        # ክፍያ ማሳወቅ
        msg = f"💰 *{get_text(lang, 'cash_payment')}*\n\n"
        msg += f"✅ {get_text(lang, 'payment_confirmed')}\n"
        msg += f"💰 {get_text(lang, 'amount')}: {format_currency(payment['amount'])} ETB\n"
        msg += f"🔢 {get_text(lang, 'transaction_id')}: {payment['transaction_id']}\n\n"
        msg += f"📦 {get_text(lang, 'order_confirmed')}\n"
        msg += f"📌 {get_text(lang, 'cash_on_delivery_note')}"
        
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton(
                "📋 " + get_text(lang, 'view_order'),
                callback_data=f"order_{order_id}"
            ),
            InlineKeyboardButton(
                "🔙 " + get_text(lang, 'main_menu'),
                callback_data="main_menu"
            )
        )
        
        bot.send_message(
            message.chat.id,
            msg,
            reply_markup=markup,
            parse_mode='Markdown'
        )
        
        # ትዕዛዝ ማረጋገጫ መላክ
        send_order_confirmation(bot, order_id, db)
        
        # ለአስተዳዳሪ ማሳወቅ
        notify_admins(
            bot,
            f"💰 *{get_text(lang, 'new_payment')}*\n\n"
            f"👤 {get_text(lang, 'user')}: {message.from_user.first_name}\n"
            f"💰 {get_text(lang, 'amount')}: {format_currency(payment['amount'])} ETB\n"
            f"🔢 {get_text(lang, 'transaction_id')}: {payment['transaction_id']}\n"
            f"💰 {get_text(lang, 'method')}: Cash on Delivery"
        )
    
    # ==================== የባንክ ዝውውር ክፍያ ====================
    
    def process_bank_payment(message: Message, payment: Dict, db: Database, bot: TeleBot):
        """የባንክ ዝውውር ክፍያ ማስኬድ"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)
        
        # የባንክ መረጃ
        bank_info = get_bank_info(lang)
        
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton(
                "✅ " + get_text(lang, 'payment_done'),
                callback_data=f"confirm_bank_payment_{payment['id']}"
            ),
            InlineKeyboardButton(
                "❌ " + get_text(lang, 'cancel_payment'),
                callback_data=f"cancel_payment_{payment['id']}"
            )
        )
        
        msg = f"🏦 *{get_text(lang, 'bank_transfer')}*\n\n"
        msg += f"💰 {get_text(lang, 'amount')}: {format_currency(payment['amount'])} ETB\n"
        msg += f"🔢 {get_text(lang, 'transaction_id')}: {payment['transaction_id']}\n\n"
        msg += f"*{get_text(lang, 'bank_details')}:*\n"
        msg += bank_info + "\n\n"
        msg += f"📌 {get_text(lang, 'bank_transfer_instructions')}\n"
        msg += f"📸 {get_text(lang, 'upload_receipt')}"
        
        bot.send_message(
            message.chat.id,
            msg,
            reply_markup=markup,
            parse_mode='Markdown'
        )
        
        # ለአስተዳዳሪ ማሳወቅ
        notify_admins(
            bot,
            f"🏦 *{get_text(lang, 'new_payment')}*\n\n"
            f"👤 {get_text(lang, 'user')}: {message.from_user.first_name}\n"
            f"💰 {get_text(lang, 'amount')}: {format_currency(payment['amount'])} ETB\n"
            f"🔢 {get_text(lang, 'transaction_id')}: {payment['transaction_id']}\n"
            f"🏦 {get_text(lang, 'method')}: Bank Transfer"
        )
    
    # ==================== ክፍያ ማረጋገጥ ====================
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('verify_payment_'))
    def handle_verify_payment(call: CallbackQuery):
        """ክፍያ ማረጋገጥ"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        try:
            payment_id = int(call.data.replace('verify_payment_', ''))
        except ValueError:
            bot.answer_callback_query(call.id, "❌ Invalid payment")
            return

        if not get_owned_payment(payment_id, user_id):
            bot.answer_callback_query(call.id, "❌ Payment not found")
            return
        
        # ክፍያ ማረጋገጥ
        payment = payment_service.verify_payment(payment_id)
        
        if not payment:
            bot.answer_callback_query(
                call.id,
                "❌ " + get_text(lang, 'payment_not_found')
            )
            return
        
        if payment.get('status') == 'completed':
            bot.answer_callback_query(
                call.id,
                "✅ " + get_text(lang, 'payment_successful')
            )
            
            # ትዕዛዝ ማረጋገጥ
            order_id = payment.get('order_id')
            if order_id:
                db.update_order_status(order_id, 'Processing')
                
                # ትዕዛዝ ማረጋገጫ መላክ
                send_order_confirmation(bot, order_id, db)
            
            # መልዕክት ማሳየት
            try:
                bot.delete_message(call.message.chat.id, call.message.message_id)
            except:
                pass
            
            msg = f"✅ *{get_text(lang, 'payment_successful')}*\n\n"
            msg += f"💰 {get_text(lang, 'amount')}: {format_currency(payment['amount'])} ETB\n"
            msg += f"🔢 {get_text(lang, 'transaction_id')}: {payment['transaction_id']}\n\n"
            msg += f"📦 {get_text(lang, 'order_confirmed')}\n"
            msg += f"📌 {get_text(lang, 'we_will_notify_you')}"
            
            bot.send_message(
                call.message.chat.id,
                msg,
                parse_mode='Markdown'
            )
        else:
            bot.answer_callback_query(
                call.id,
                "⏳ " + get_text(lang, 'payment_pending')
            )
    
    # ==================== ክፍያ መሰረዝ ====================
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('cancel_payment_'))
    def handle_cancel_payment(call: CallbackQuery):
        """ክፍያ መሰረዝ"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        try:
            payment_id = int(call.data.replace('cancel_payment_', ''))
        except ValueError:
            bot.answer_callback_query(call.id, "❌ Invalid payment")
            return

        if not get_owned_payment(payment_id, user_id):
            bot.answer_callback_query(call.id, "❌ Payment not found")
            return
        
        # ክፍያ መሰረዝ
        payment_service.cancel_payment(payment_id)
        
        bot.answer_callback_query(
            call.id,
            "❌ " + get_text(lang, 'payment_cancelled')
        )
        
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        
        bot.send_message(
            call.message.chat.id,
            "❌ " + get_text(lang, 'payment_cancelled') + "\n\n" +
            get_text(lang, 'you_can_try_again')
        )
    
    # ==================== የባንክ ክፍያ ማረጋገጫ ====================
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_bank_payment_'))
    def handle_confirm_bank_payment(call: CallbackQuery):
        """የባንክ ክፍያ ማረጋገጫ"""
        user_id = call.from_user.id
        lang = get_user_lang(db, user_id)
        
        try:
            payment_id = int(call.data.replace('confirm_bank_payment_', ''))
        except ValueError:
            bot.answer_callback_query(call.id, "❌ Invalid payment")
            return

        if not get_owned_payment(payment_id, user_id):
            bot.answer_callback_query(call.id, "❌ Payment not found")
            return
        
        msg = bot.send_message(
            call.message.chat.id,
            "📸 " + get_text(lang, 'upload_payment_receipt') + "\n\n" +
            get_text(lang, 'receipt_instructions')
        )
        bot.register_next_step_handler(msg, process_receipt_upload, payment_id, db, bot)
        bot.answer_callback_query(call.id)
    
    def process_receipt_upload(message: Message, payment_id: int, db: Database, bot: TeleBot):
        """የደረሰኝ ፋይል ማስኬድ"""
        user_id = message.from_user.id
        lang = get_user_lang(db, user_id)

        if not get_owned_payment(payment_id, user_id):
            bot.send_message(message.chat.id, "❌ " + get_text(lang, 'payment_not_found'))
            return
        
        if message.content_type != 'photo':
            bot.send_message(
                message.chat.id,
                "❌ " + get_text(lang, 'please_upload_photo')
            )
            bot.register_next_step_handler(message, process_receipt_upload, payment_id, db, bot)
            return
        
        # ፎቶ ማስቀመጥ
        file_id = message.photo[-1].file_id
        
        # ክፍያ ማዘመን
        payment = payment_service.update_payment_receipt(payment_id, file_id)
        
        if payment:
            # ክፍያ ማረጋገጥ
            payment_service.verify_payment(payment_id)
            
            # ትዕዛዝ ማረጋገጥ
            order_id = payment.get('order_id')
            if order_id:
                db.update_order_status(order_id, 'Processing')
                send_order_confirmation(bot, order_id, db)
            
            bot.send_message(
                message.chat.id,
                "✅ " + get_text(lang, 'receipt_uploaded') + "\n\n" +
                get_text(lang, 'payment_verified')
            )
            
            # ለአስተዳዳሪ ማሳወቅ
            notify_admins(
                bot,
                f"📸 *{get_text(lang, 'new_receipt_uploaded')}*\n\n"
                f"👤 {get_text(lang, 'user')}: {message.from_user.first_name}\n"
                f"🔢 {get_text(lang, 'payment_id')}: {payment_id}\n"
                f"💰 {get_text(lang, 'amount')}: {format_currency(payment['amount'])} ETB"
            )
        else:
            bot.send_message(
                message.chat.id,
                "❌ " + get_text(lang, 'receipt_upload_failed')
            )
    
    # ==================== ረዳት ተግባራት ====================
    
    def get_order_data(user_id: int) -> Optional[Dict]:
        """የትዕዛዝ መረጃ ማግኘት"""
        # ጋሪ ማግኘት
        cart = db.get_cart(user_id)
        
        if not cart or not cart.get('items'):
            return None
        
        items = json.loads(cart['items']) if isinstance(cart['items'], str) else cart['items']
        total = sum(item['price'] * item['quantity'] for item in items)
        
        return {
            'order_id': cart.get('order_id'),
            'items': items,
            'total': total,
            'discount': cart.get('discount_amount', 0),
            'final': cart.get('final_amount', total)
        }
    
    def get_bank_info(lang: str = 'am') -> str:
        """የባንክ መረጃ ማግኘት"""
        if lang == 'am':
            return """
🏦 የባንክ ስም: አብሲኒያ ባንክ
👤 ባለሂሳብ: ዘናጭ ልብስ ቤት
🔢 የሂሳብ ቁጥር: 1234567890
🔢 የንግድ ኮድ: 9876543210
"""
        else:
            return """
🏦 Bank Name: Abyssinia Bank
👤 Account Holder: Zenach Boutique
🔢 Account Number: 1234567890
🔢 Business Code: 9876543210
"""
    
    # ==================== የChapa ዌብሁክ ====================
    
    # ይህ ተግባር ከChapa የሚመጡ ዌብሁክ ጥሪዎችን ያስተናግዳል
    def handle_chapa_webhook(data: Dict):
        """የቻፓ ዌብሁክ አያያዝ"""
        # ፊርማ ማረጋገጥ
        signature = data.get('signature')
        if not signature:
            logger.warning("Chapa webhook: No signature")
            return
        
        # የፊርማ ማረጋገጫ
        expected = hmac.new(
            config.payment.CHAPA_SECRET_KEY.encode(),
            data.get('data', '').encode(),
            hashlib.sha256
        ).hexdigest()
        
        if signature != expected:
            logger.warning("Chapa webhook: Invalid signature")
            return
        
        # የክፍያ መረጃ
        payment_data = data.get('data', {})
        transaction_id = payment_data.get('tx_ref')
        status = payment_data.get('status')
        
        # ክፍያ ማዘመን
        payment = payment_service.update_payment_status(transaction_id, status)
        
        if payment and status == 'success':
            # ትዕዛዝ ማረጋገጥ
            order_id = payment.get('order_id')
            if order_id:
                db.update_order_status(order_id, 'Processing')
                
                # ትዕዛዝ ማረጋገጫ መላክ
                send_order_confirmation(bot, order_id, db)
        
        logger.info(f"Chapa webhook: Transaction {transaction_id} -> {status}")
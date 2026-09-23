# -*- coding: utf-8 -*-

"""
ዘናጭ ቦት - የክፍያ አገልግሎት
ይህ ፋይል ሁሉንም የክፍያ ተዛማጅ አገልግሎቶችን ይይዛል
"""

import logging
import json
import uuid
import hashlib
import hmac
import requests
from datetime import datetime
from typing import Optional, Dict, Any, List
from decimal import Decimal

from database import Database
from config import config
from utils.helpers import generate_order_number, format_currency

logger = logging.getLogger(__name__)


class PaymentService:
    """የክፍያ አገልግሎት ክፍል"""
    
    def __init__(self, db: Database):
        self.db = db
        self.chapa_secret = config.payment.CHAPA_SECRET_KEY
        self.chapa_api_url = config.payment.CHAPA_API_URL
        self.telebirr_api_key = config.payment.TELEBIRR_API_KEY
        self.telebirr_api_url = config.payment.TELEBIRR_API_URL
        self.currency = config.payment.CURRENCY
    
    def create_payment(self, user_id: int, order_id: int, amount: float,
                       method: str, currency: str = 'ETB') -> Optional[Dict]:
        """አዲስ ክፍያ መፍጠር"""
        try:
            transaction_id = f"PAY-{uuid.uuid4().hex[:8].upper()}-{datetime.now().strftime('%Y%m%d')}"
            
            payment_data = {
                'order_id': order_id,
                'user_id': user_id,
                'amount': amount,
                'currency': currency,
                'method': method,
                'transaction_id': transaction_id,
                'status': 'pending'
            }
            
            # ወደ ውሂብ ጎታ መመዝገብ
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO payments (
                        order_id, user_id, amount, currency, method,
                        transaction_id, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    RETURNING id
                ''', (
                    payment_data['order_id'],
                    payment_data['user_id'],
                    payment_data['amount'],
                    payment_data['currency'],
                    payment_data['method'],
                    payment_data['transaction_id'],
                    payment_data['status']
                ))
                
                payment_id = cursor.fetchone()['id']
                payment_data['id'] = payment_id
                
                # የትዕዛዝ ክፍያ ሁኔታ ማዘመን
                cursor.execute('''
                    UPDATE orders 
                    SET payment_status = 'Pending', payment_id = ?
                    WHERE id = ?
                ''', (transaction_id, order_id))
            
            logger.info(f"አዲስ ክፍያ ተፈጥሯል: {transaction_id} - {amount} {currency}")
            return payment_data
            
        except Exception as e:
            logger.error(f"ክፍያ መፍጠር አልተቻለም: {e}")
            return None
    
    def get_payment(self, payment_id: int) -> Optional[Dict]:
        """ክፍያ በID ማግኘት"""
        try:
            cursor = self.db.execute(
                "SELECT * FROM payments WHERE id = ?",
                (payment_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"ክፍያ ማግኘት አልተቻለም: {e}")
            return None
    
    def get_payment_by_transaction(self, transaction_id: str) -> Optional[Dict]:
        """ክፍያ በግብይት ቁጥር ማግኘት"""
        try:
            cursor = self.db.execute(
                "SELECT * FROM payments WHERE transaction_id = ?",
                (transaction_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"ክፍያ ማግኘት አልተቻለም: {e}")
            return None
    
    def update_payment_status(self, transaction_id: str, status: str,
                              provider_response: Dict = None) -> bool:
        """የክፍያ ሁኔታ ማዘመን"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                if provider_response:
                    cursor.execute('''
                        UPDATE payments 
                        SET status = ?, provider_response = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE transaction_id = ?
                    ''', (status, json.dumps(provider_response), transaction_id))
                else:
                    cursor.execute('''
                        UPDATE payments 
                        SET status = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE transaction_id = ?
                    ''', (status, transaction_id))
                
                # ክፍያ ከተጠናቀቀ
                if status == 'completed':
                    cursor.execute('''
                        UPDATE payments 
                        SET completed_at = CURRENT_TIMESTAMP
                        WHERE transaction_id = ?
                    ''', (transaction_id,))
                    
                    # የትዕዛዝ ክፍያ ሁኔታ ማዘመን
                    cursor.execute('''
                        UPDATE orders 
                        SET payment_status = 'Paid'
                        WHERE payment_id = ?
                    ''', (transaction_id,))
                
                # ክፍያ ከተሰረዘ
                elif status in ['failed', 'cancelled']:
                    cursor.execute('''
                        UPDATE orders 
                        SET payment_status = 'Failed'
                        WHERE payment_id = ?
                    ''', (transaction_id,))
            
            logger.info(f"ክፍያ ሁኔታ ተዘምኗል: {transaction_id} -> {status}")
            return True
            
        except Exception as e:
            logger.error(f"ክፍያ ሁኔታ ማዘመን አልተቻለም: {e}")
            return False
    
    def verify_payment(self, payment_id: int) -> Optional[Dict]:
        """ክፍያ ማረጋገጥ"""
        payment = self.get_payment(payment_id)
        
        if not payment:
            return None
        
        # ክፍያ አስቀድሞ ከተረጋገጠ
        if payment['status'] == 'completed':
            return payment
        
        # በክፍያ ዘዴ ላይ የተመሰረተ ማረጋገጫ
        if payment['method'] == 'chapa':
            return self.verify_chapa_payment(payment)
        elif payment['method'] == 'telebirr':
            return self.verify_telebirr_payment(payment)
        else:
            # ጥሬ ገንዘብ እና የባንክ ዝውውር በእጅ ይረጋገጣሉ
            self.update_payment_status(payment['transaction_id'], 'processing')
            return payment
    
    # ==================== ቻፓ ክፍያ ====================
    
    def initiate_chapa_payment(self, payment: Dict) -> Optional[Dict]:
        """የቻፓ ክፍያ ማስጀመር"""
        try:
            # የትዕዛዝ መረጃ
            order = self.db.get_order(payment['order_id'])
            user = self.db.get_user(payment['user_id'])
            
            # የቻፓ ጥያቄ መረጃ
            payload = {
                'amount': str(payment['amount']),
                'currency': payment['currency'],
                'email': user.get('email', 'customer@example.com'),
                'first_name': user.get('first_name', 'Customer'),
                'last_name': user.get('last_name', ''),
                'phone_number': user.get('phone', ''),
                'tx_ref': payment['transaction_id'],
                'callback_url': 'https://your-domain.com/chapa-callback',
                'return_url': 'https://t.me/your_bot',
                'customization': {
                    'title': 'ዘናጭ ቦት ክፍያ',
                    'description': f'ትዕዛዝ #{order["order_number"]}'
                }
            }
            
            # ወደ ቻፓ መላክ
            headers = {
                'Authorization': f'Bearer {self.chapa_secret}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f"{self.chapa_api_url}/transaction/initialize",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 'success':
                    checkout_url = data.get('data', {}).get('checkout_url')
                    
                    # የክፍያ መረጃ ማዘመን
                    self.update_payment_status(
                        payment['transaction_id'],
                        'processing',
                        {'checkout_url': checkout_url, 'chapa_response': data}
                    )
                    
                    return {
                        'checkout_url': checkout_url,
                        'transaction_id': payment['transaction_id']
                    }
            
            logger.error(f"ቻፓ ክፍያ መጀመር አልተቻለም: {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"ቻፓ ክፍያ መጀመር አልተቻለም: {e}")
            return None
    
    def verify_chapa_payment(self, payment: Dict) -> Optional[Dict]:
        """የቻፓ ክፍያ ማረጋገጥ"""
        try:
            headers = {
                'Authorization': f'Bearer {self.chapa_secret}'
            }
            
            response = requests.get(
                f"{self.chapa_api_url}/transaction/verify/{payment['transaction_id']}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 'success':
                    payment_data = data.get('data', {})
                    
                    amount_matches = str(payment_data.get('amount')) == str(payment['amount'])
                    currency_matches = payment_data.get('currency', payment['currency']) == payment['currency']
                    reference_matches = payment_data.get('tx_ref', payment['transaction_id']) == payment['transaction_id']

                    if payment_data.get('status') == 'success' and amount_matches and currency_matches and reference_matches:
                        # ክፍያ ተረጋግጧል
                        self.update_payment_status(
                            payment['transaction_id'],
                            'completed',
                            data
                        )
                        return self.get_payment(payment['id'])
            
            logger.warning(f"ቻፓ ክፍያ ማረጋገጥ አልተቻለም: {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"ቻፓ ክፍያ ማረጋገጥ አልተቻለም: {e}")
            return None
    
    # ==================== ቴሌብር ክፍያ ====================
    
    def initiate_telebirr_payment(self, payment: Dict) -> Optional[Dict]:
        """የቴሌብር ክፍያ ማስጀመር"""
        try:
            # የቴሌብር ጥያቄ መረጃ
            payload = {
                'merchant_id': config.payment.TELEBIRR_MERCHANT_ID,
                'transaction_id': payment['transaction_id'],
                'amount': str(payment['amount']),
                'currency': payment['currency'],
                'return_url': 'https://t.me/your_bot'
            }
            
            headers = {
                'Authorization': f'Bearer {self.telebirr_api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f"{self.telebirr_api_url}/payment/initiate",
                json=payload,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 'success':
                    payment_url = data.get('data', {}).get('payment_url')
                    
                    self.update_payment_status(
                        payment['transaction_id'],
                        'processing',
                        {'payment_url': payment_url, 'telebirr_response': data}
                    )
                    
                    return {
                        'payment_url': payment_url,
                        'transaction_id': payment['transaction_id']
                    }
            
            logger.error(f"ቴሌብር ክፍያ መጀመር አልተቻለም: {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"ቴሌብር ክፍያ መጀመር አልተቻለም: {e}")
            return None
    
    def verify_telebirr_payment(self, payment: Dict) -> Optional[Dict]:
        """የቴሌብር ክፍያ ማረጋገጥ"""
        try:
            headers = {
                'Authorization': f'Bearer {self.telebirr_api_key}'
            }
            
            response = requests.get(
                f"{self.telebirr_api_url}/payment/verify/{payment['transaction_id']}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 'success':
                    payment_data = data.get('data', {})
                    
                    if payment_data.get('status') == 'completed':
                        self.update_payment_status(
                            payment['transaction_id'],
                            'completed',
                            data
                        )
                        return self.get_payment(payment['id'])
            
            logger.warning(f"ቴሌብር ክፍያ ማረጋገጥ አልተቻለም: {response.text}")
            return None
            
        except Exception as e:
            logger.error(f"ቴሌብር ክፍያ ማረጋገጥ አልተቻለም: {e}")
            return None
    
    # ==================== ሌሎች ክፍያዎች ====================
    
    def cancel_payment(self, payment_id: int) -> bool:
        """ክፍያ መሰረዝ"""
        payment = self.get_payment(payment_id)
        
        if not payment:
            return False
        
        if payment['status'] in ['completed', 'cancelled']:
            return False
        
        return self.update_payment_status(payment['transaction_id'], 'cancelled')
    
    def refund_payment(self, payment_id: int) -> bool:
        """ክፍያ መመለስ"""
        payment = self.get_payment(payment_id)
        
        if not payment:
            return False
        
        if payment['status'] != 'completed':
            return False
        
        # ክፍያ መመለስ ሂደት
        return self.update_payment_status(payment['transaction_id'], 'refunded')
    
    def update_payment_receipt(self, payment_id: int, receipt_file_id: str) -> Optional[Dict]:
        """የክፍያ ደረሰኝ ማዘመን"""
        payment = self.get_payment(payment_id)
        
        if not payment:
            return None
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE payments 
                    SET provider_response = COALESCE(provider_response, '{}'::jsonb)
                        || jsonb_build_object('receipt_file_id', ?)
                    WHERE id = ?
                ''', (receipt_file_id, payment_id))
            
            return self.get_payment(payment_id)
            
        except Exception as e:
            logger.error(f"የክፍያ ደረሰኝ ማዘመን አልተቻለም: {e}")
            return None
    
    def get_user_payments(self, user_id: int, limit: int = 20) -> List[Dict]:
        """የተጠቃሚ ክፍያዎች ማግኘት"""
        try:
            cursor = self.db.execute('''
                SELECT * FROM payments 
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (user_id, limit))
            
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"የተጠቃሚ ክፍያዎች ማግኘት አልተቻለም: {e}")
            return []
    
    def get_payment_stats(self) -> Dict:
        """የክፍያ ስታቲስቲክስ"""
        try:
            cursor = self.db.execute('''
                SELECT 
                    COUNT(*) as total_payments,
                    SUM(CASE WHEN status = 'completed' THEN amount ELSE 0 END) as total_revenue,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful_payments,
                    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_payments,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_payments
                FROM payments
            ''')
            
            row = cursor.fetchone()
            
            return {
                'total_payments': row[0] or 0,
                'total_revenue': row[1] or 0,
                'successful_payments': row[2] or 0,
                'pending_payments': row[3] or 0,
                'failed_payments': row[4] or 0
            }
            
        except Exception as e:
            logger.error(f"የክፍያ ስታቲስቲክስ ማግኘት አልተቻለም: {e}")
            return {
                'total_payments': 0,
                'total_revenue': 0,
                'successful_payments': 0,
                'pending_payments': 0,
                'failed_payments': 0
            }


# ==================== የቻፓ ዌብሁክ አስተናጋጅ ====================

def handle_chapa_webhook(request_data: Dict, payment_service: PaymentService) -> Dict:
    """የቻፓ ዌብሁክ ጥሪ አስተናጋጅ"""
    try:
        # ፊርማ ማረጋገጥ
        signature = request_data.get('signature')
        if not signature:
            return {'status': 'error', 'message': 'No signature provided'}, 400
        
        # የፊርማ ማረጋገጫ
        payload = request_data.get('data', {})
        signed_data = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        expected = hmac.new(
            config.payment.CHAPA_SECRET_KEY.encode(),
            signed_data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected):
            return {'status': 'error', 'message': 'Invalid signature'}, 401
        
        # የክፍያ መረጃ
        payment_data = request_data.get('data', {})
        transaction_id = payment_data.get('tx_ref')
        status = payment_data.get('status')
        
        if not transaction_id:
            return {'status': 'error', 'message': 'No transaction ID'}, 400
        
        # ክፍያ ማዘመን
        if status == 'success':
            payment_service.update_payment_status(transaction_id, 'completed', request_data)
        else:
            payment_service.update_payment_status(transaction_id, 'failed', request_data)
        
        logger.info(f"ቻፓ ዌብሁክ: {transaction_id} -> {status}")
        return {'status': 'success'}, 200
        
    except Exception as e:
        logger.error(f"ቻፓ ዌብሁክ ስህተት: {e}")
        return {'status': 'error', 'message': str(e)}, 500
# -*- coding: utf-8 -*-

"""
ዘናጭ ቦት - ውቅር ፋይል
ይህ ፋይል ሁሉንም የቦቱን ውቅር ተለዋዋጮች ይዟል
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

# የአካባቢ ተለዋዋጮችን መጫን
load_dotenv()

# የፕሮጀክቱ ሥር ማውጫ
BASE_DIR = Path(__file__).parent


@dataclass
class BotConfig:
    """የቦት ውቅር ክፍል"""
    
    # ቶከን
    TOKEN: str = os.getenv('BOT_TOKEN', '')
    
    # አስተዳዳሪዎች
    ADMIN_IDS: List[int] = field(default_factory=lambda: [
        int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id
    ])
    
    # የቦት ስም
    BOT_NAME: str = os.getenv('BOT_NAME', 'ዘናጭ ቦት')
    BOT_USERNAME: str = os.getenv('BOT_USERNAME', 'ZenachBot')
    
    # ዌብሁክ ውቅር
    USE_WEBHOOK: bool = os.getenv('USE_WEBHOOK', 'False').lower() == 'true'
    WEBHOOK_URL: str = os.getenv('WEBHOOK_URL', 'https://example.com')
    WEBHOOK_PATH: str = os.getenv('WEBHOOK_PATH', '/webhook')
    WEBHOOK_PORT: int = int(os.getenv('WEBHOOK_PORT', 8443))
    WEBHOOK_CERT: Optional[str] = os.getenv('WEBHOOK_CERT')
    WEBHOOK_KEY: Optional[str] = os.getenv('WEBHOOK_KEY')
    
    # ፖሊንግ ውቅር
    POLLING_TIMEOUT: int = int(os.getenv('POLLING_TIMEOUT', 60))
    POLLING_INTERVAL: int = int(os.getenv('POLLING_INTERVAL', 30))
    
    # ሌሎች ውቅሮች
    ALLOWED_UPDATES: List[str] = field(default_factory=lambda: [
        'message', 'callback_query', 'inline_query', 'chosen_inline_result'
    ])
    
    # ደህንነት
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'your-secret-key-change-this')
    
    def validate(self) -> bool:
        """ውቅሩን ማረጋገጥ"""
        if not self.TOKEN:
            raise ValueError("❌ BOT_TOKEN አልተገኘም!")
        if not self.ADMIN_IDS:
            raise ValueError("❌ ADMIN_IDS አልተገኘም!")
        return True


@dataclass
class DatabaseConfig:
    """የውሂብ ጎታ ውቅር"""
    
    # SQLite
    DB_PATH: str = os.getenv('DB_PATH', 'data/zenach.db')
    DB_POOL_SIZE: int = int(os.getenv('DB_POOL_SIZE', 10))
    DB_TIMEOUT: int = int(os.getenv('DB_TIMEOUT', 30))
    
    # ምትኬ
    BACKUP_DIR: str = os.getenv('BACKUP_DIR', 'assets/documents/backups')
    BACKUP_INTERVAL_DAYS: int = int(os.getenv('BACKUP_INTERVAL_DAYS', 1))
    BACKUP_RETENTION_DAYS: int = int(os.getenv('BACKUP_RETENTION_DAYS', 30))
    
    def validate(self) -> bool:
        """የውሂብ ጎታ ማውጫ መኖሩን ማረጋገጥ"""
        db_dir = Path(self.DB_PATH).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        return True


@dataclass
class PaymentConfig:
    """የክፍያ ውቅር"""
    
    # ቻፓ
    CHAPA_SECRET_KEY: str = os.getenv('CHAPA_SECRET_KEY', '')
    CHAPA_API_URL: str = os.getenv('CHAPA_API_URL', 'https://api.chapa.co/v1')
    
    # ቴሌብር
    TELEBIRR_API_KEY: str = os.getenv('TELEBIRR_API_KEY', '')
    TELEBIRR_API_URL: str = os.getenv('TELEBIRR_API_URL', 'https://api.telegram.org')
    TELEBIRR_MERCHANT_ID: str = os.getenv('TELEBIRR_MERCHANT_ID', '')
    
    # ገደቦች
    MIN_AMOUNT: float = float(os.getenv('MIN_AMOUNT', 10.0))
    MAX_AMOUNT: float = float(os.getenv('MAX_AMOUNT', 100000.0))
    CURRENCY: str = os.getenv('CURRENCY', 'ETB')
    
    def validate(self) -> bool:
        """የክፍያ ውቅር ማረጋገጥ"""
        # Cash and bank transfer remain available without an online provider.
        return True


@dataclass
class NotificationConfig:
    """የማስታወቂያ ውቅር"""
    
    # ኢሜይል
    SMTP_HOST: str = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    SMTP_PORT: int = int(os.getenv('SMTP_PORT', 587))
    SMTP_USER: str = os.getenv('SMTP_USER', '')
    SMTP_PASSWORD: str = os.getenv('SMTP_PASSWORD', '')
    EMAIL_FROM: str = os.getenv('EMAIL_FROM', '')
    
    # ኤስኤምኤስ
    SMS_API_KEY: str = os.getenv('SMS_API_KEY', '')
    SMS_SENDER_ID: str = os.getenv('SMS_SENDER_ID', 'ZenachBot')
    SMS_API_URL: str = os.getenv('SMS_API_URL', '')
    
    # ቦት ማስታወቂያ
    NOTIFICATION_BATCH_SIZE: int = int(os.getenv('NOTIFICATION_BATCH_SIZE', 100))
    NOTIFICATION_INTERVAL: int = int(os.getenv('NOTIFICATION_INTERVAL', 60))  # ሰከንዶች
    

@dataclass
class CacheConfig:
    """የካሽ ውቅር"""
    
    # ካሽ አይነት (memory, redis)
    CACHE_TYPE: str = os.getenv('CACHE_TYPE', 'memory')
    
    # ሬዲስ (ከፈለጉ)
    REDIS_URL: str = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    REDIS_PASSWORD: str = os.getenv('REDIS_PASSWORD', '')
    
    # ጊዜያዊ መጠን
    DEFAULT_TTL: int = int(os.getenv('DEFAULT_TTL', 3600))  # 1 ሰዓት
    SESSION_TTL: int = int(os.getenv('SESSION_TTL', 86400))  # 24 ሰዓት
    CART_TTL: int = int(os.getenv('CART_TTL', 604800))  # 7 ቀናት


@dataclass
class SecurityConfig:
    """የደህንነት ውቅር"""
    
    # ደህንነት
    RATE_LIMIT_ENABLED: bool = os.getenv('RATE_LIMIT_ENABLED', 'True').lower() == 'true'
    RATE_LIMIT_REQUESTS: int = int(os.getenv('RATE_LIMIT_REQUESTS', 30))  # በደቂቃ
    RATE_LIMIT_PERIOD: int = int(os.getenv('RATE_LIMIT_PERIOD', 60))  # ሰከንዶች
    
    # የጸረ-ስፓም
    SPAM_DETECTION_ENABLED: bool = os.getenv('SPAM_DETECTION_ENABLED', 'True').lower() == 'true'
    MAX_MESSAGES_PER_MINUTE: int = int(os.getenv('MAX_MESSAGES_PER_MINUTE', 20))
    
    # የተፈቀዱ ጎራዎች
    ALLOWED_DOMAINS: List[str] = field(default_factory=lambda: [
        domain.strip() for domain in os.getenv('ALLOWED_DOMAINS', '').split(',') if domain
    ])


@dataclass
class LoggingConfig:
    """የመዝገብ ውቅር"""
    
    # ደረጃ
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.getenv('LOG_FILE', 'logs/bot.log')
    ERROR_LOG_FILE: str = os.getenv('ERROR_LOG_FILE', 'logs/errors.log')
    ACCESS_LOG_FILE: str = os.getenv('ACCESS_LOG_FILE', 'logs/access.log')
    
    # ፎርማት
    LOG_FORMAT: str = os.getenv('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    DATE_FORMAT: str = os.getenv('DATE_FORMAT', '%Y-%m-%d %H:%M:%S')
    
    # ማሽከርከር
    MAX_LOG_SIZE: int = int(os.getenv('MAX_LOG_SIZE', 10485760))  # 10MB
    BACKUP_COUNT: int = int(os.getenv('BACKUP_COUNT', 5))


@dataclass
class LanguageConfig:
    """የቋንቋ ውቅር"""
    
    # የሚገኙ ቋንቋዎች
    LANGUAGES: List[str] = field(default_factory=lambda: ['am', 'en'])
    DEFAULT_LANGUAGE: str = os.getenv('DEFAULT_LANGUAGE', 'am')
    LOCALE_DIR: str = os.getenv('LOCALE_DIR', 'locales')
    
    # የቋንቋ ፋይሎች
    def get_language_file(self, lang: str) -> Path:
        """የቋንቋ ፋይል መንገድ መመለስ"""
        return Path(self.LOCALE_DIR) / f"{lang}.json"


@dataclass
class ProductConfig:
    """የምርት ውቅር"""
    
    # ምድቦች
    CATEGORIES: List[str] = field(default_factory=lambda: ['Men', 'Women', 'Accessories'])
    
    # መጠኖች
    SIZES: List[str] = field(default_factory=lambda: ['XS', 'S', 'M', 'L', 'XL', 'XXL'])
    
    # ገደቦች
    MAX_IMAGES_PER_PRODUCT: int = int(os.getenv('MAX_IMAGES_PER_PRODUCT', 5))
    PRODUCTS_PER_PAGE: int = int(os.getenv('PRODUCTS_PER_PAGE', 10))
    LOW_STOCK_THRESHOLD: int = int(os.getenv('LOW_STOCK_THRESHOLD', 5))


@dataclass
class OrderConfig:
    """የትዕዛዝ ውቅር"""
    
    # ሁኔታዎች
    ORDER_STATUSES: List[str] = field(default_factory=lambda: [
        'Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled'
    ])
    
    # የትዕዛዝ ቁጥር ቅድመ-ቅጥያ
    ORDER_PREFIX: str = os.getenv('ORDER_PREFIX', 'ZEN')
    
    # ገደቦች
    MAX_ITEMS_PER_ORDER: int = int(os.getenv('MAX_ITEMS_PER_ORDER', 50))
    MIN_ORDER_AMOUNT: float = float(os.getenv('MIN_ORDER_AMOUNT', 0.0))
    FREE_SHIPPING_THRESHOLD: float = float(os.getenv('FREE_SHIPPING_THRESHOLD', 500.0))
    
    # ማስታወቂያ
    SEND_ORDER_CONFIRMATION: bool = os.getenv('SEND_ORDER_CONFIRMATION', 'True').lower() == 'true'
    SEND_SHIPPING_NOTIFICATION: bool = os.getenv('SEND_SHIPPING_NOTIFICATION', 'True').lower() == 'true'


class Config:
    """አጠቃላይ ውቅር ክፍል"""
    
    def __init__(self):
        self.bot = BotConfig()
        self.database = DatabaseConfig()
        self.payment = PaymentConfig()
        self.notification = NotificationConfig()
        self.cache = CacheConfig()
        self.security = SecurityConfig()
        self.logging = LoggingConfig()
        self.language = LanguageConfig()
        self.product = ProductConfig()
        self.order = OrderConfig()
        
        # ሁሉንም ውቅሮች ማረጋገጥ
        self.validate_all()
    
    def validate_all(self):
        """ሁሉንም ውቅሮች ማረጋገጥ"""
        self.bot.validate()
        self.database.validate()
        self.payment.validate()
        # ሌሎች ውቅሮች አማራጭ ናቸው
    
    def to_dict(self) -> Dict[str, Any]:
        """ውቅሩን ወደ መዝገብ መለወጥ"""
        return {
            'bot': {
                'name': self.bot.BOT_NAME,
                'username': self.bot.BOT_USERNAME,
                'admins': len(self.bot.ADMIN_IDS)
            },
            'database': {
                'path': self.database.DB_PATH,
                'pool_size': self.database.DB_POOL_SIZE
            },
            'payment': {
                'currency': self.payment.CURRENCY,
                'chapa_enabled': bool(self.payment.CHAPA_SECRET_KEY),
                'telebirr_enabled': bool(self.payment.TELEBIRR_API_KEY)
            },
            'cache': {
                'type': self.cache.CACHE_TYPE,
                'ttl': self.cache.DEFAULT_TTL
            },
            'security': {
                'rate_limit': self.security.RATE_LIMIT_ENABLED,
                'spam_detection': self.security.SPAM_DETECTION_ENABLED
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """በቁልፍ ውቅር እሴት ማግኘት"""
        # በአሁኑ ጊዜ ቀላል አገልግሎት
        return getattr(self, key, default)


# ወደ ፋይል ማስቀመጥ
def save_config_to_file(config: Config, filepath: str = 'config.json'):
    """ውቅሩን ወደ ፋይል ማስቀመጥ"""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)


def load_config_from_file(filepath: str = 'config.json') -> Dict[str, Any]:
    """ከፋይል ውቅር ማንበብ"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


# አለምአቀፍ ውቅር ነገር
config = Config()


# ለሙከራ
if __name__ == '__main__':
    print("=" * 50)
    print("📋 የዘናጭ ቦት ውቅር")
    print("=" * 50)
    
    print(f"\n🤖 የቦት ስም: {config.bot.BOT_NAME}")
    print(f"👥 አስተዳዳሪዎች: {len(config.bot.ADMIN_IDS)}")
    print(f"🗄️ ውሂብ ጎታ: {config.database.DB_PATH}")
    print(f"💳 ክፍያ: {config.payment.CURRENCY}")
    print(f"🌍 ቋንቋዎች: {', '.join(config.language.LANGUAGES)}")
    print(f"🛡️ ደህንነት: {'✅ ንቁ' if config.security.RATE_LIMIT_ENABLED else '❌ ያልነቃ'}")
    
    # ወደ ፋይል ማስቀመጥ
    save_config_to_file(config)
    print(f"\n✅ ውቅር ወደ 'config.json' ተቀምጧል")
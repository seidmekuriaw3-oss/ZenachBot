# -*- coding: utf-8 -*-

"""
ዘናጭ ቦት - ረዳት ተግባራት
ይህ ፋይል የተለያዩ ረዳት ተግባራትን ይይዛል
"""

import os
import json
import random
import string
import re
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Union
from pathlib import Path
import pytz

from config import config


# ==================== ቋንቋ ====================

_languages = {}
_language_dir = Path(__file__).parent.parent / 'locales'


def load_languages():
    """ሁሉንም የቋንቋ ፋይሎች መጫን"""
    global _languages
    
    try:
        if not _language_dir.exists():
            _language_dir.mkdir(parents=True, exist_ok=True)
            # ነባሪ ቋንቋ ፋይሎች መፍጠር
            create_default_language_files()
        
        for lang_file in _language_dir.glob('*.json'):
            lang_code = lang_file.stem
            with open(lang_file, 'r', encoding='utf-8') as f:
                _languages[lang_code] = json.load(f)
        
        if not _languages:
            create_default_language_files()
            load_languages()
            
    except Exception as e:
        print(f"❌ ቋንቋዎችን መጫን አልተቻለም: {e}")


def create_default_language_files():
    """ነባሪ ቋንቋ ፋይሎችን መፍጠር"""
    # አማርኛ
    am_file = _language_dir / 'am.json'
    if not am_file.exists():
        with open(am_file, 'w', encoding='utf-8') as f:
            json.dump({
                'welcome': "እንኳን ወደ ዘናጭ ልብስ ቤት በሰላም መጡ!",
                'men': "👕 የወንድ ልብሶች",
                'women': "👗 የሴት ልብሶች",
                'contact': "📍 አድራሻ እና ስልክ",
                'orders': "📋 ትዕዛዞቼ",
                'profile': "👤 መገለጫ",
                'cart': "🛒 ጋሪ",
                'subscribe': "📢 ለማስታወቂያ ተመዝገብ",
                'unsubscribe': "🔕 ከማስታወቂያ ተመዝገብ",
                'admin': "⚙️ አስተዳደር",
                'back': "🔙 ወደ መጀመሪያ",
                'price': "💰 ዋጋ",
                'size': "📏 መጠን",
                'status': "📦 ሁኔታ",
                'in_stock': "✅ በክምችት ላይ",
                'out_of_stock': "❌ ተሽጦ አልቋል",
                'buy': "🛍 ለመግዛት",
                'review': "⭐ ግምገማ",
                'discount': "🏷️ ቅናሽ",
                'report': "📊 ሪፖርት",
                'add_product': "➕ ምርት ጨምር",
                'delete_product': "➖ ምርት ሰርዝ",
                'stats': "📈 ስታቲስቲክስ",
                'error': "❌ ስህተት!",
                'success': "✅ ተሳካ!",
                'warning': "⚠️ ማስጠንቀቂያ!"
            }, f, ensure_ascii=False, indent=2)
    
    # እንግሊዝኛ
    en_file = _language_dir / 'en.json'
    if not en_file.exists():
        with open(en_file, 'w', encoding='utf-8') as f:
            json.dump({
                'welcome': "Welcome to Zenach Boutique!",
                'men': "👕 Men's Clothing",
                'women': "👗 Women's Clothing",
                'contact': "📍 Address & Phone",
                'orders': "📋 My Orders",
                'profile': "👤 Profile",
                'cart': "🛒 Cart",
                'subscribe': "📢 Subscribe",
                'unsubscribe': "🔕 Unsubscribe",
                'admin': "⚙️ Admin",
                'back': "🔙 Main Menu",
                'price': "💰 Price",
                'size': "📏 Size",
                'status': "📦 Status",
                'in_stock': "✅ In Stock",
                'out_of_stock': "❌ Out of Stock",
                'buy': "🛍 Buy Now",
                'review': "⭐ Review",
                'discount': "🏷️ Discount",
                'report': "📊 Report",
                'add_product': "➕ Add Product",
                'delete_product': "➖ Delete Product",
                'stats': "📈 Statistics",
                'error': "❌ Error!",
                'success': "✅ Success!",
                'warning': "⚠️ Warning!"
            }, f, ensure_ascii=False, indent=2)


def get_language_file(lang: str) -> Dict:
    """የቋንቋ ፋይል ማግኘት"""
    if not _languages:
        load_languages()
    
    return _languages.get(lang, _languages.get('am', {}))


def get_text(lang: str, key: str) -> str:
    """የተተረጎመ ጽሁፍ ማግኘት"""
    lang_data = get_language_file(lang)
    return lang_data.get(key, key)


def get_user_lang(db, user_id: int) -> str:
    """የተጠቃሚ ቋንቋ ማግኘት"""
    user = db.get_user(user_id) if db else None
    return user.get('lang', config.language.DEFAULT_LANGUAGE) if user else config.language.DEFAULT_LANGUAGE


def get_lang(user_id: int) -> str:
    """የተጠቃሚ ቋንቋ ማግኘት (ከመረጃ ጎታ ውጭ)"""
    # ይህ ተግባር አሁን አገልግሎት ላይ የሚውልበት ቦታ የለም
    return config.language.DEFAULT_LANGUAGE


# ==================== ፎርማቲንግ ====================

def format_currency(amount: float, currency: str = 'ETB') -> str:
    """የገንዘብ ፎርማት ማድረግ"""
    try:
        return f"{amount:,.2f} {currency}"
    except:
        return f"{amount} {currency}"


def format_date(date_str: str) -> str:
    """ቀን ፎርማት ማድረግ"""
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M')
    except:
        return date_str


def format_number(number: Union[int, float]) -> str:
    """ቁጥር ፎርማት ማድረግ"""
    try:
        return f"{number:,}"
    except:
        return str(number)


def format_duration(seconds: int) -> str:
    """ጊዜ ፎርማት ማድረግ"""
    minutes = seconds // 60
    hours = minutes // 60
    days = hours // 24
    
    if days > 0:
        return f"{days} ቀናት"
    elif hours > 0:
        return f"{hours} ሰዓታት"
    elif minutes > 0:
        return f"{minutes} ደቂቃዎች"
    else:
        return f"{seconds} ሰከንዶች"


# ==================== ጄኔሬተር ====================

def generate_order_number(prefix: str = 'ZEN') -> str:
    """የትዕዛዝ ቁጥር መፍጠር"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_part = ''.join(random.choices(string.digits, k=4))
    return f"{prefix}{timestamp}{random_part}"


def generate_referral_code(user_id: int = None) -> str:
    """የማጣቀሻ ኮድ መፍጠር"""
    if user_id:
        return f"ZEN{user_id}{datetime.now().strftime('%m%d')}"
    return f"ZEN{''.join(random.choices(string.ascii_uppercase + string.digits, k=6))}"


def generate_random_string(length: int = 8, include_digits: bool = True) -> str:
    """የዘፈቀደ ጽሁፍ መፍጠር"""
    chars = string.ascii_uppercase + string.ascii_lowercase
    if include_digits:
        chars += string.digits
    return ''.join(random.choices(chars, k=length))


def generate_discount_code(length: int = 8) -> str:
    """የቅናሽ ኮድ መፍጠር"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


def generate_transaction_id(prefix: str = 'TXN') -> str:
    """የግብይት ቁጥር መፍጠር"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_part = ''.join(random.choices(string.digits, k=6))
    return f"{prefix}{timestamp}{random_part}"


def generate_product_sku(category: str, name: str) -> str:
    """የምርት SKU መፍጠር"""
    category_part = category[:3].upper()
    name_part = ''.join([w[0] for w in name.split()[:2]]).upper()
    random_part = ''.join(random.choices(string.digits, k=4))
    return f"{category_part}{name_part}{random_part}"


def generate_invoice_number() -> str:
    """የደረሰኝ ቁጥር መፍጠር"""
    return f"INV-{datetime.now().strftime('%Y%m')}-{''.join(random.choices(string.digits, k=6))}"


def generate_otp(length: int = 6) -> str:
    """የአንድ ጊዜ ፓስዎርድ መፍጠር"""
    return ''.join(random.choices(string.digits, k=length))


def generate_password(length: int = 12) -> str:
    """ፓስዎርድ መፍጠር"""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choices(chars, k=length))


def generate_username(first_name: str = None) -> str:
    """የተጠቃሚ ስም መፍጠር"""
    if first_name:
        base = first_name.lower().replace(' ', '')
    else:
        base = 'user'
    return f"{base}{''.join(random.choices(string.digits, k=4))}"


# ==================== ማረጋገጫ ====================

def is_admin(user_id: int, admin_ids: List[int]) -> bool:
    """ተጠቃሚ አስተዳዳሪ መሆኑን ማረጋገጥ"""
    return user_id in admin_ids


def validate_phone(phone: str) -> bool:
    """የስልክ ቁጥር ማረጋገጥ"""
    phone = phone.replace('+', '').replace(' ', '').replace('-', '')
    return len(phone) >= 10 and phone.isdigit()


def validate_email(email: str) -> bool:
    """ኢሜይል ማረጋገጥ"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_url(url: str) -> bool:
    """ዩአርኤል ማረጋገጥ"""
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
    return bool(re.match(pattern, url))


def validate_date(date_str: str) -> bool:
    """ቀን ማረጋገጥ"""
    try:
        datetime.fromisoformat(date_str)
        return True
    except:
        return False


def validate_amount(amount: float) -> bool:
    """መጠን ማረጋገጥ"""
    return isinstance(amount, (int, float)) and amount > 0


def validate_quantity(quantity: int) -> bool:
    """ብዛት ማረጋገጥ"""
    return isinstance(quantity, int) and quantity > 0


def validate_rating(rating: int) -> bool:
    """ደረጃ ማረጋገጥ"""
    return isinstance(rating, int) and 1 <= rating <= 5


# ==================== ጽሁፍ ማስተካከያ ====================

def truncate_text(text: str, max_length: int = 100) -> str:
    """ጽሁፍ ማጥረግ"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def clean_text(text: str) -> str:
    """ጽሁፍ ማጽዳት"""
    # የማይፈለጉ ቁምፊዎችን ማስወገድ
    text = re.sub(r'[^\w\s@.,!?-]', '', text)
    # ብዙ ክፍተቶችን ወደ አንድ መቀየር
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def remove_emoji(text: str) -> str:
    """ኢሞጂዎችን ማስወገድ"""
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', text)


def safe_cast(value: Any, cast_type: type, default: Any = None) -> Any:
    """በደህንነት አይነት መቀየር"""
    try:
        return cast_type(value)
    except:
        return default


def parse_command_args(text: str) -> List[str]:
    """የትዕዛዝ ክርክሮችን መተንተን"""
    parts = text.split()
    return parts[1:] if len(parts) > 1 else []


def get_file_extension(filename: str) -> str:
    """የፋይል ቅጥያ ማግኘት"""
    return os.path.splitext(filename)[1].lower()


def is_valid_url(url: str) -> bool:
    """ዩአርኤል ልክ መሆኑን ማረጋገጥ"""
    return validate_url(url)


# ==================== ጊዜ ====================

def get_timezone() -> str:
    """የሰዓት ዞን ማግኘት"""
    return config.bot.TIMEZONE if hasattr(config.bot, 'TIMEZONE') else 'Africa/Addis_Ababa'


def get_datetime(timezone: str = None) -> datetime:
    """የአሁኑን ጊዜ ማግኘት"""
    tz = timezone or get_timezone()
    try:
        return datetime.now(pytz.timezone(tz))
    except:
        return datetime.now()


# ==================== ፋይል ====================

def ensure_directory(path: str) -> bool:
    """ማውጫ መኖሩን ማረጋገጥ"""
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return True
    except:
        return False


def get_file_size(filepath: str) -> int:
    """የፋይል መጠን ማግኘት"""
    try:
        return os.path.getsize(filepath)
    except:
        return 0


def read_json_file(filepath: str) -> Optional[Dict]:
    """JSON ፋይል ማንበብ"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return None


def write_json_file(filepath: str, data: Dict) -> bool:
    """JSON ፋይል መጻፍ"""
    try:
        ensure_directory(os.path.dirname(filepath))
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except:
        return False


# ቋንቋዎችን መጫን
load_languages()
# -*- coding: utf-8 -*-

"""
ዘናጭ ቦት - የውሂብ ጎታ ሞጁል
ይህ ፋይል ሁሉንም የውሂብ ጎታ ግንኙነቶችን እና ስራዎችን ይይዛል
"""

import re
import json
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple, Union
from contextlib import contextmanager
import threading
import logging

from config import config
from utils.logger import get_logger

logger = get_logger('database')


def _decode_json(value):
    if isinstance(value, str):
        return json.loads(value)
    return value


class _CursorProxy:
    def __init__(self, cursor, database):
        self._cursor = cursor
        self._database = database

    def execute(self, query, params=()):
        query, params = self._database.prepare_query(query, params)
        self._cursor.execute(query, params)
        return self

    def executemany(self, query, params):
        query, _ = self._database.prepare_query(query, ())
        self._cursor.executemany(query, params)
        return self

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class _ConnectionProxy:
    def __init__(self, connection, database):
        self._connection = connection
        self._database = database

    def cursor(self):
        return _CursorProxy(self._connection.cursor(), self._database)

    def execute(self, query, params=()):
        cursor = self.cursor()
        return cursor.execute(query, params)

    def __getattr__(self, name):
        return getattr(self._connection, name)


class Database:
    """የውሂብ ጎታ ክፍል - ሁሉንም የውሂብ ጎታ ስራዎች ያከናውናል"""
    
    def __init__(self):
        self.db_url = config.database.DB_URL
        if not self.db_url.startswith(('postgresql://', 'postgres://')):
            raise ValueError('DATABASE_URL must be a PostgreSQL connection URL')
        self._local = threading.local()
        self._lock = threading.RLock()

        # የውሂብ ጎታ ሰንጠረዦችን መፍጠር
        self.init_database()
        logger.info("✅ PostgreSQL የውሂብ ጎታ ተዘጋጅቷል")
    
    @contextmanager
    def get_connection(self):
        """የውሂብ ጎታ ግንኙነት መፍጠር"""
        conn = getattr(self._local, 'connection', None)
        if conn is None:
            try:
                import psycopg2
                from psycopg2.extras import DictCursor
            except ImportError as error:
                raise RuntimeError('psycopg2-binary is required for PostgreSQL') from error
            conn = psycopg2.connect(
                self.db_url,
                connect_timeout=config.database.DB_TIMEOUT,
                cursor_factory=DictCursor
            )
            self._local.connection = conn
        
        try:
            yield _ConnectionProxy(conn, self)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ የውሂብ ጎታ ስህተት: {e}")
            raise
        finally:
            # Keep the thread-local connection alive because execute() returns
            # cursors that callers consume after this context exits.
            pass

    def prepare_query(self, query: str, params: tuple = ()):
        """Translate legacy query placeholders and schema syntax to PostgreSQL."""
        query = query.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "BIGSERIAL PRIMARY KEY")
        query = query.replace(" JSON", " JSONB")
        query = re.sub(r'\b(user_id|referred_by|admin_id) INTEGER\b', r'\1 BIGINT', query)
        query = query.replace("datetime('now', ?)", "CURRENT_TIMESTAMP + %s::interval")
        query = re.sub(
            r'GROUP_CONCAT\(([^)]+)\)',
            r"STRING_AGG(\1::text, ',')",
            query,
            flags=re.IGNORECASE,
        )
        query = query.replace(
            "INSERT OR REPLACE INTO users",
            "INSERT INTO users"
        )
        if query.lstrip().startswith("INSERT INTO users"):
            query = query.rstrip() + (
                " ON CONFLICT (user_id) DO UPDATE SET "
                "username = EXCLUDED.username, first_name = EXCLUDED.first_name, "
                "last_name = EXCLUDED.last_name, phone = EXCLUDED.phone, "
                "email = EXCLUDED.email, lang = EXCLUDED.lang, "
                "referral_code = EXCLUDED.referral_code"
            )
        query = query.replace(
            "INSERT OR REPLACE INTO carts",
            "INSERT INTO carts"
        )
        if query.lstrip().startswith("INSERT INTO carts"):
            query = query.rstrip() + (
                " ON CONFLICT (user_id) DO UPDATE SET items = EXCLUDED.items, "
                "total_amount = EXCLUDED.total_amount, discount_amount = EXCLUDED.discount_amount, "
                "final_amount = EXCLUDED.final_amount, discount_code = EXCLUDED.discount_code"
            )
        query = query.replace(
            "INSERT OR REPLACE INTO reviews",
            "INSERT INTO reviews"
        )
        if query.lstrip().startswith("INSERT INTO reviews"):
            query = query.rstrip() + (
                " ON CONFLICT (user_id, product_id) DO UPDATE SET "
                "rating = EXCLUDED.rating, comment = EXCLUDED.comment, "
                "images = EXCLUDED.images"
            )
        query = query.replace('?', '%s')
        return query, params
    
    def execute(self, query: str, params: tuple = ()):
        """የSQL ጥያቄ መፈጸም"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor
    
    def executemany(self, query: str, params: List[tuple]):
        """ብዙ SQL ጥያቄዎችን መፈጸም"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params)
            return cursor
    
    # ==================== መጀመሪያ ማዋቀር ====================
    
    def init_database(self):
        """ሁሉንም የውሂብ ጎታ ሰንጠረዦች መፍጠር"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. ተጠቃሚዎች
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    phone TEXT,
                    email TEXT,
                    lang TEXT DEFAULT 'am',
                    is_subscribed INTEGER DEFAULT 1,
                    is_banned INTEGER DEFAULT 0,
                    is_admin INTEGER DEFAULT 0,
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    login_count INTEGER DEFAULT 0,
                    referral_code TEXT UNIQUE,
                    referred_by INTEGER,
                    balance REAL DEFAULT 0,
                    FOREIGN KEY (referred_by) REFERENCES users(user_id)
                )
            ''')
            
            # 2. ምርቶች
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name_am TEXT NOT NULL,
                    name_en TEXT NOT NULL,
                    description_am TEXT,
                    description_en TEXT,
                    price REAL NOT NULL,
                    compare_price REAL,
                    size TEXT,
                    category TEXT NOT NULL,
                    subcategory TEXT,
                    image_id TEXT NOT NULL,
                    images JSON,
                    status TEXT DEFAULT 'In Stock',
                    stock_quantity INTEGER DEFAULT 0,
                    sold_count INTEGER DEFAULT 0,
                    views_count INTEGER DEFAULT 0,
                    rating_avg REAL DEFAULT 0,
                    rating_count INTEGER DEFAULT 0,
                    is_featured INTEGER DEFAULT 0,
                    is_on_sale INTEGER DEFAULT 0,
                    discount_percent REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 3. ትዕዛዞች
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_number TEXT UNIQUE NOT NULL,
                    user_id INTEGER,
                    total_amount REAL NOT NULL,
                    subtotal_amount REAL NOT NULL,
                    discount_amount REAL DEFAULT 0,
                    shipping_amount REAL DEFAULT 0,
                    tax_amount REAL DEFAULT 0,
                    final_amount REAL NOT NULL,
                    status TEXT DEFAULT 'Pending',
                    payment_method TEXT,
                    payment_status TEXT DEFAULT 'Unpaid',
                    payment_id TEXT,
                    shipping_address TEXT,
                    shipping_city TEXT,
                    shipping_phone TEXT,
                    shipping_name TEXT,
                    notes TEXT,
                    admin_notes TEXT,
                    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    delivered_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # 4. የትዕዛዝ ዝርዝሮች
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS order_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER,
                    product_id INTEGER,
                    quantity INTEGER NOT NULL,
                    price_at_time REAL NOT NULL,
                    size_at_time TEXT,
                    total_price REAL NOT NULL,
                    discount_at_time REAL DEFAULT 0,
                    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                    FOREIGN KEY (product_id) REFERENCES products(id)
                )
            ''')
            
            # 5. ግምገማዎች
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    product_id INTEGER,
                    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                    comment TEXT,
                    images JSON,
                    is_verified INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (product_id) REFERENCES products(id),
                    UNIQUE(user_id, product_id)
                )
            ''')
            
            # 6. ቅናሾች
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS discounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    discount_percent REAL NOT NULL,
                    description TEXT,
                    discount_type TEXT DEFAULT 'percent',
                    min_order_amount REAL DEFAULT 0,
                    max_discount_amount REAL,
                    valid_from TIMESTAMP,
                    valid_to TIMESTAMP,
                    usage_limit INTEGER DEFAULT 0,
                    used_count INTEGER DEFAULT 0,
                    user_limit INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 7. የቅናሽ አጠቃቀም
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS discount_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    discount_id INTEGER,
                    user_id INTEGER,
                    order_id INTEGER,
                    used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (discount_id) REFERENCES discounts(id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (order_id) REFERENCES orders(id)
                )
            ''')
            
            # 8. ጋሪ
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS carts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE,
                    items JSON,
                    total_amount REAL DEFAULT 0,
                    discount_amount REAL DEFAULT 0,
                    final_amount REAL DEFAULT 0,
                    discount_code TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # 9. ማስታወቂያዎች
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title_am TEXT,
                    title_en TEXT,
                    message_am TEXT,
                    message_en TEXT,
                    image_id TEXT,
                    product_id INTEGER,
                    notification_type TEXT DEFAULT 'general',
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_sent INTEGER DEFAULT 0,
                    scheduled_for TIMESTAMP,
                    sent_count INTEGER DEFAULT 0,
                    failed_count INTEGER DEFAULT 0,
                    FOREIGN KEY (product_id) REFERENCES products(id)
                )
            ''')
            
            # 10. የእንቅስቃሴ ሎግ
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS activity_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT NOT NULL,
                    details TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # 11. ክፍያዎች
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS payments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER,
                    user_id INTEGER,
                    amount REAL NOT NULL,
                    currency TEXT DEFAULT 'ETB',
                    method TEXT NOT NULL,
                    transaction_id TEXT UNIQUE,
                    status TEXT DEFAULT 'Pending',
                    provider_response JSON,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    FOREIGN KEY (order_id) REFERENCES orders(id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # 12. የምርት ጉብኝቶች
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS product_views (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER,
                    user_id INTEGER,
                    ip_address TEXT,
                    viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products(id),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # 13. የተመረጡ ምርቶች
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS wishlists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    product_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (product_id) REFERENCES products(id),
                    UNIQUE(user_id, product_id)
                )
            ''')
            
            # 14. የአስተዳዳሪ ማስታወሻዎች
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admin_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER,
                    note_type TEXT,
                    reference_id INTEGER,
                    content TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (admin_id) REFERENCES users(user_id)
                )
            ''')
            
            # 15. የስርዓት ምትኬዎች
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS backups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    size INTEGER,
                    backup_type TEXT DEFAULT 'full',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    restored_at TIMESTAMP,
                    restored_by INTEGER
                )
            ''')
            
            # ኢንዴክሶች መፍጠር
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_products_category ON products(category)",
                "CREATE INDEX IF NOT EXISTS idx_products_status ON products(status)",
                "CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)",
                "CREATE INDEX IF NOT EXISTS idx_orders_order_date ON orders(order_date)",
                "CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id)",
                "CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id)",
                "CREATE INDEX IF NOT EXISTS idx_reviews_product_id ON reviews(product_id)",
                "CREATE INDEX IF NOT EXISTS idx_reviews_user_id ON reviews(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_discounts_code ON discounts(code)",
                "CREATE INDEX IF NOT EXISTS idx_discounts_active ON discounts(is_active)",
                "CREATE INDEX IF NOT EXISTS idx_notifications_sent ON notifications(is_sent)",
                "CREATE INDEX IF NOT EXISTS idx_activity_logs_user_id ON activity_logs(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_payments_order_id ON payments(order_id)",
                "CREATE INDEX IF NOT EXISTS idx_payments_transaction_id ON payments(transaction_id)",
                "CREATE INDEX IF NOT EXISTS idx_product_views_product_id ON product_views(product_id)",
                "CREATE INDEX IF NOT EXISTS idx_wishlists_user_id ON wishlists(user_id)",
            ]
            
            for index in indexes:
                cursor.execute(index)

            self._migrate_postgres_ids(cursor)
            
            logger.info("✅ ሁሉም የውሂብ ጎታ ሰንጠረዦች ተፈጥረዋል")

    def _migrate_postgres_ids(self, cursor):
        """Use BIGINT for Telegram IDs and preserve their foreign keys."""
        constraints = (
            ('users', 'users_referred_by_fkey'),
            ('orders', 'orders_user_id_fkey'),
            ('reviews', 'reviews_user_id_fkey'),
            ('discount_usage', 'discount_usage_user_id_fkey'),
            ('carts', 'carts_user_id_fkey'),
            ('activity_logs', 'activity_logs_user_id_fkey'),
            ('payments', 'payments_user_id_fkey'),
            ('product_views', 'product_views_user_id_fkey'),
            ('wishlists', 'wishlists_user_id_fkey'),
            ('admin_notes', 'admin_notes_admin_id_fkey'),
        )
        for table, constraint in constraints:
            cursor.execute(f'ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {constraint}')

        for table, column in (
            ('users', 'user_id'), ('users', 'referred_by'),
            ('orders', 'user_id'), ('reviews', 'user_id'),
            ('discount_usage', 'user_id'), ('carts', 'user_id'),
            ('activity_logs', 'user_id'), ('payments', 'user_id'),
            ('product_views', 'user_id'), ('wishlists', 'user_id'),
            ('admin_notes', 'admin_id'),
        ):
            cursor.execute(f'ALTER TABLE {table} ALTER COLUMN {column} TYPE BIGINT')

        for statement in (
            'ALTER TABLE users ADD CONSTRAINT users_referred_by_fkey FOREIGN KEY (referred_by) REFERENCES users(user_id)',
            'ALTER TABLE orders ADD CONSTRAINT orders_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(user_id)',
            'ALTER TABLE reviews ADD CONSTRAINT reviews_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(user_id)',
            'ALTER TABLE discount_usage ADD CONSTRAINT discount_usage_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(user_id)',
            'ALTER TABLE carts ADD CONSTRAINT carts_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(user_id)',
            'ALTER TABLE activity_logs ADD CONSTRAINT activity_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(user_id)',
            'ALTER TABLE payments ADD CONSTRAINT payments_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(user_id)',
            'ALTER TABLE product_views ADD CONSTRAINT product_views_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(user_id)',
            'ALTER TABLE wishlists ADD CONSTRAINT wishlists_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(user_id)',
            'ALTER TABLE admin_notes ADD CONSTRAINT admin_notes_admin_id_fkey FOREIGN KEY (admin_id) REFERENCES users(user_id)',
        ):
            cursor.execute(statement)
    
    # ==================== ማጣቀሻ ሰንጠረዦች ====================
    
    def get_table_names(self) -> List[str]:
        """ሁሉንም የሰንጠረዥ ስሞች መመለስ"""
        cursor = self.execute("SELECT tablename AS name FROM pg_catalog.pg_tables WHERE schemaname = 'public'")
        return [row[0] for row in cursor.fetchall()]
    
    def get_table_info(self, table_name: str) -> List[Dict]:
        """የሰንጠረዥ መረጃ ማግኘት"""
        cursor = self.execute(
            "SELECT column_name AS name, ordinal_position AS cid, data_type AS type "
            "FROM information_schema.columns WHERE table_schema = 'public' AND table_name = ? "
            "ORDER BY ordinal_position",
            (table_name,)
        )
        return [dict(row) for row in cursor.fetchall()]
    
    def get_table_size(self, table_name: str) -> int:
        """የሰንጠረዥ መጠን (ረድፎች) ማግኘት"""
        cursor = self.execute(f"SELECT COUNT(*) FROM {table_name}")
        return cursor.fetchone()[0]
    
    # ==================== የውሂብ ጎታ መጠን ====================
    
    def get_db_size(self) -> int:
        """የውሂብ ጎታ መጠን በባይት ማግኘት"""
        try:
            cursor = self.execute("SELECT pg_database_size(current_database())")
            return cursor.fetchone()[0]
        except:
            return 0
    
    def get_db_stats(self) -> Dict[str, Any]:
        """አጠቃላይ የውሂብ ጎታ ስታቲስቲክስ"""
        stats = {
            'total_size': self.get_db_size(),
            'tables': {},
            'total_rows': 0
        }
        
        for table in self.get_table_names():
            count = self.get_table_size(table)
            stats['tables'][table] = count
            stats['total_rows'] += count
        
        return stats
    
    # ==================== ማጽዳት ====================
    
    def vacuum(self):
        """የውሂብ ጎታ መጠን መቀነስ (VACUUM)"""
        with self.get_connection() as conn:
            conn.execute("VACUUM")
        logger.info("✅ የውሂብ ጎታ VACUUM ተከናውኗል")
    
    def close(self):
        """የውሂብ ጎታ ግንኙነቶችን መዝጋት"""
        conn = getattr(self._local, 'connection', None)
        if conn is not None:
            conn.close()
            self._local.connection = None


# ለወደፊት መጠቀሚያ: የውሂብ ጎታ ክፍል ተጨማሪ ተግባራት

class DatabaseMixin:
    """ለተጨማሪ የውሂብ ጎታ ተግባራት ማህበር"""
    
    # ==================== የተጠቃሚ ስራዎች ====================

    def get_admin_ids(self) -> List[int]:
        """Return administrator Telegram IDs configured for this application."""
        return list(config.bot.ADMIN_IDS)
    
    def create_user(self, user_id: int, username: str = None, first_name: str = None,
                   last_name: str = None, phone: str = None, email: str = None,
                   lang: str = 'am', referral_code: str = None) -> bool:
        """አዲስ ተጠቃሚ መፍጠር"""
        try:
            # የማጣቀሻ ኮድ መፍጠር
            if not referral_code:
                referral_code = f"ZEN{user_id}{datetime.now().strftime('%m%d')}"
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO users 
                    (user_id, username, first_name, last_name, phone, email, lang, referral_code)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, username, first_name, last_name, phone, email, lang, referral_code))
                return True
        except Exception as e:
            logger.error(f"❌ ተጠቃሚ መፍጠር አልተቻለም: {e}")
            return False
    
    def get_user(self, user_id: int) -> Optional[Dict]:
        """ተጠቃሚ በID ማግኘት"""
        try:
            cursor = self.execute(
                "SELECT * FROM users WHERE user_id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"❌ ተጠቃሚ ማግኘት አልተቻለም: {e}")
            return None
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """ተጠቃሚ በዩዘርኔም ማግኘት"""
        try:
            cursor = self.execute(
                "SELECT * FROM users WHERE username = ?",
                (username,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"❌ ተጠቃሚ ማግኘት አልተቻለም: {e}")
            return None
    
    def get_user_by_referral(self, referral_code: str) -> Optional[Dict]:
        """ተጠቃሚ በማጣቀሻ ኮድ ማግኘት"""
        try:
            cursor = self.execute(
                "SELECT * FROM users WHERE referral_code = ?",
                (referral_code,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"❌ ተጠቃሚ ማግኘት አልተቻለም: {e}")
            return None
    
    def update_user(self, user_id: int, **kwargs) -> bool:
        """ተጠቃሚ መረጃ ማዘመን"""
        allowed_fields = ['username', 'first_name', 'last_name', 'phone', 'email', 
                         'lang', 'is_subscribed', 'is_banned', 'is_admin', 'balance']
        
        fields = []
        values = []
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                fields.append(f"{key} = ?")
                values.append(value)
        
        if not fields:
            return False
        
        values.append(user_id)
        query = f"UPDATE users SET {', '.join(fields)}, last_active = CURRENT_TIMESTAMP WHERE user_id = ?"
        
        try:
            self.execute(query, tuple(values))
            return True
        except Exception as e:
            logger.error(f"❌ ተጠቃሚ ማዘመን አልተቻለም: {e}")
            return False
    
    def get_all_users(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """ሁሉንም ተጠቃሚዎች ማግኘት"""
        try:
            cursor = self.execute(
                "SELECT * FROM users ORDER BY registered_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ ተጠቃሚዎችን ማግኘት አልተቻለም: {e}")
            return []
    
    def get_user_count(self) -> int:
        """ጠቅላላ የተጠቃሚ ብዛት"""
        try:
            cursor = self.execute("SELECT COUNT(*) FROM users")
            return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"❌ የተጠቃሚ ብዛት ማግኘት አልተቻለም: {e}")
            return 0
    
    def get_active_users(self, days: int = 7) -> List[Dict]:
        """በቅርብ ጊዜ ንቁ የሆኑ ተጠቃሚዎች"""
        try:
            cursor = self.execute('''
                SELECT * FROM users 
                WHERE last_active >= datetime('now', ?)
                ORDER BY last_active DESC
            ''', (f'-{days} days',))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ ንቁ ተጠቃሚዎችን ማግኘት አልተቻለም: {e}")
            return []
    
    # ==================== የምርት ስራዎች ====================
    
    def create_product(self, data: Dict) -> Optional[int]:
        """አዲስ ምርት መፍጠር"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO products (
                        name_am, name_en, description_am, description_en,
                        price, compare_price, size, category, subcategory,
                        image_id, images, stock_quantity, is_featured,
                        is_on_sale, discount_percent
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    RETURNING id
                ''', (
                    data.get('name_am'), data.get('name_en'),
                    data.get('description_am'), data.get('description_en'),
                    data.get('price'), data.get('compare_price'),
                    data.get('size'), data.get('category'), data.get('subcategory'),
                    data.get('image_id'), json.dumps(data.get('images', [])),
                    data.get('stock_quantity', 0),
                    data.get('is_featured', 0),
                    data.get('is_on_sale', 0),
                    data.get('discount_percent', 0)
                ))
                return cursor.fetchone()['id']
        except Exception as e:
            logger.error(f"❌ ምርት መፍጠር አልተቻለም: {e}")
            return None
    
    def get_product(self, product_id: int) -> Optional[Dict]:
        """ምርት በID ማግኘት"""
        try:
            cursor = self.execute(
                "SELECT * FROM products WHERE id = ?",
                (product_id,)
            )
            row = cursor.fetchone()
            if row:
                product = dict(row)
                if product.get('images'):
                    product['images'] = _decode_json(product['images'])
                return product
            return None
        except Exception as e:
            logger.error(f"❌ ምርት ማግኘት አልተቻለም: {e}")
            return None
    
    def get_products(self, category: str = None, limit: int = 20, offset: int = 0,
                     sort_by: str = 'created_at', order: str = 'DESC') -> List[Dict]:
        """ምርቶችን ማግኘት"""
        try:
            query = "SELECT * FROM products WHERE status = 'In Stock'"
            params = []
            
            if category:
                query += " AND category = ?"
                params.append(category)
            
            allowed_sort = ['created_at', 'price', 'name_am', 'rating_avg', 'sold_count']
            if sort_by not in allowed_sort:
                sort_by = 'created_at'
            
            order = 'DESC' if order.upper() == 'DESC' else 'ASC'
            query += f" ORDER BY {sort_by} {order} LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor = self.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ ምርቶችን ማግኘት አልተቻለም: {e}")
            return []
    
    def update_product(self, product_id: int, **kwargs) -> bool:
        """ምርት ማዘመን"""
        allowed_fields = [
            'name_am', 'name_en', 'description_am', 'description_en',
            'price', 'compare_price', 'size', 'category', 'subcategory',
            'image_id', 'images', 'stock_quantity', 'status',
            'is_featured', 'is_on_sale', 'discount_percent'
        ]
        
        fields = []
        values = []
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                if key == 'images' and isinstance(value, list):
                    value = json.dumps(value)
                fields.append(f"{key} = ?")
                values.append(value)
        
        if not fields:
            return False
        
        values.append(product_id)
        query = f"UPDATE products SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
        
        try:
            self.execute(query, tuple(values))
            return True
        except Exception as e:
            logger.error(f"❌ ምርት ማዘመን አልተቻለም: {e}")
            return False
    
    def delete_product(self, product_id: int) -> bool:
        """ምርት መሰረዝ"""
        try:
            self.execute("DELETE FROM products WHERE id = ?", (product_id,))
            return True
        except Exception as e:
            logger.error(f"❌ ምርት መሰረዝ አልተቻለም: {e}")
            return False
    
    def get_product_count(self, category: str = None) -> int:
        """የምርት ብዛት"""
        try:
            if category:
                cursor = self.execute(
                    "SELECT COUNT(*) FROM products WHERE category = ? AND status = 'In Stock'",
                    (category,)
                )
            else:
                cursor = self.execute(
                    "SELECT COUNT(*) FROM products WHERE status = 'In Stock'"
                )
            return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"❌ የምርት ብዛት ማግኘት አልተቻለም: {e}")
            return 0
    
    def get_low_stock_products(self, threshold: int = 5) -> List[Dict]:
        """ዝቅተኛ ክምችት ያላቸው ምርቶች"""
        try:
            cursor = self.execute('''
                SELECT * FROM products 
                WHERE stock_quantity <= ? AND status = 'In Stock'
                ORDER BY stock_quantity ASC
            ''', (threshold,))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ ዝቅተኛ ክምችት ምርቶችን ማግኘት አልተቻለም: {e}")
            return []
    
    def get_featured_products(self, limit: int = 10) -> List[Dict]:
        """ተለይተው የቀረቡ ምርቶች"""
        try:
            cursor = self.execute('''
                SELECT * FROM products 
                WHERE is_featured = 1 AND status = 'In Stock'
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ ተለይተው የቀረቡ ምርቶችን ማግኘት አልተቻለም: {e}")
            return []
    
    def search_products(self, query: str, limit: int = 20) -> List[Dict]:
        """ምርቶችን መፈለግ"""
        try:
            search_term = f"%{query}%"
            cursor = self.execute('''
                SELECT * FROM products 
                WHERE (name_am LIKE ? OR name_en LIKE ? OR description_am LIKE ? OR description_en LIKE ?)
                AND status = 'In Stock'
                ORDER BY 
                    CASE 
                        WHEN name_am LIKE ? OR name_en LIKE ? THEN 1
                        ELSE 2
                    END,
                    created_at DESC
                LIMIT ?
            ''', (search_term, search_term, search_term, search_term, 
                  query, query, limit))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ ምርቶችን መፈለግ አልተቻለም: {e}")
            return []
    
    # ==================== የትዕዛዝ ስራዎች ====================
    
    def create_order(self, data: Dict) -> Optional[int]:
        """አዲስ ትዕዛዝ መፍጠር"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO orders (
                        order_number, user_id, total_amount, subtotal_amount,
                        discount_amount, shipping_amount, tax_amount, final_amount,
                        status, payment_method, shipping_address,
                        shipping_city, shipping_phone, shipping_name, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    RETURNING id
                ''', (
                    data.get('order_number'),
                    data.get('user_id'),
                    data.get('total_amount', 0),
                    data.get('subtotal_amount', 0),
                    data.get('discount_amount', 0),
                    data.get('shipping_amount', 0),
                    data.get('tax_amount', 0),
                    data.get('final_amount', 0),
                    data.get('status', 'Pending'),
                    data.get('payment_method'),
                    data.get('shipping_address'),
                    data.get('shipping_city'),
                    data.get('shipping_phone'),
                    data.get('shipping_name'),
                    data.get('notes')
                ))
                return cursor.fetchone()['id']
        except Exception as e:
            logger.error(f"❌ ትዕዛዝ መፍጠር አልተቻለም: {e}")
            return None
    
    def get_order(self, order_id: int) -> Optional[Dict]:
        """ትዕዛዝ በID ማግኘት"""
        try:
            cursor = self.execute(
                "SELECT * FROM orders WHERE id = ?",
                (order_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"❌ ትዕዛዝ ማግኘት አልተቻለም: {e}")
            return None
    
    def get_order_by_number(self, order_number: str) -> Optional[Dict]:
        """ትዕዛዝ በቁጥር ማግኘት"""
        try:
            cursor = self.execute(
                "SELECT * FROM orders WHERE order_number = ?",
                (order_number,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"❌ ትዕዛዝ ማግኘት አልተቻለም: {e}")
            return None
    
    def get_user_orders(self, user_id: int, limit: int = 20) -> List[Dict]:
        """የተጠቃሚ ትዕዛዞች"""
        try:
            cursor = self.execute('''
                SELECT o.*, 
                       COUNT(oi.id) as item_count,
                       GROUP_CONCAT(p.name_am) as product_names
                FROM orders o
                LEFT JOIN order_items oi ON o.id = oi.order_id
                LEFT JOIN products p ON oi.product_id = p.id
                WHERE o.user_id = ?
                GROUP BY o.id
                ORDER BY o.order_date DESC
                LIMIT ?
            ''', (user_id, limit))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ የተጠቃሚ ትዕዛዞችን ማግኘት አልተቻለም: {e}")
            return []
    
    def update_order_status(self, order_id: int, status: str, admin_notes: str = None) -> bool:
        """የትዕዛዝ ሁኔታ ማዘመን"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if admin_notes:
                    cursor.execute('''
                        UPDATE orders 
                        SET status = ?, admin_notes = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (status, admin_notes, order_id))
                else:
                    cursor.execute('''
                        UPDATE orders 
                        SET status = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (status, order_id))
                
                # ትዕዛዙ ከተጠናቀቀ ሰዓቱን መመዝገብ
                if status == 'Delivered':
                    cursor.execute('''
                        UPDATE orders SET delivered_at = CURRENT_TIMESTAMP WHERE id = ?
                    ''', (order_id,))
                
                return True
        except Exception as e:
            logger.error(f"❌ የትዕዛዝ ሁኔታ ማዘመን አልተቻለም: {e}")
            return False
    
    def get_order_items(self, order_id: int) -> List[Dict]:
        """የትዕዛዝ ዝርዝሮች"""
        try:
            cursor = self.execute('''
                SELECT oi.*, p.name_am, p.name_en, p.image_id
                FROM order_items oi
                LEFT JOIN products p ON oi.product_id = p.id
                WHERE oi.order_id = ?
            ''', (order_id,))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ የትዕዛዝ ዝርዝሮችን ማግኘት አልተቻለም: {e}")
            return []
    
    def add_order_item(self, order_id: int, product_id: int, quantity: int,
                       price: float, size: str = None, discount: float = 0) -> bool:
        """የትዕዛዝ ዝርዝር መጨመር"""
        try:
            total = price * quantity * (1 - discount / 100)
            self.execute('''
                INSERT INTO order_items 
                (order_id, product_id, quantity, price_at_time, size_at_time, 
                 total_price, discount_at_time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (order_id, product_id, quantity, price, size, total, discount))
            return True
        except Exception as e:
            logger.error(f"❌ የትዕዛዝ ዝርዝር መጨመር አልተቻለም: {e}")
            return False
    
    # ==================== የጋሪ ስራዎች ====================
    
    def get_cart(self, user_id: int) -> Optional[Dict]:
        """የተጠቃሚ ጋሪ ማግኘት"""
        try:
            cursor = self.execute(
                "SELECT * FROM carts WHERE user_id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            if row:
                cart = dict(row)
                if cart.get('items'):
                    cart['items'] = _decode_json(cart['items'])
                return cart
            return None
        except Exception as e:
            logger.error(f"❌ ጋሪ ማግኘት አልተቻለም: {e}")
            return None
    
    def update_cart(self, user_id: int, items: List[Dict], 
                    discount_code: str = None) -> bool:
        """ጋሪ ማዘመን"""
        try:
            # ጠቅላላ ዋጋ ማስላት
            total = sum(item.get('price', 0) * item.get('quantity', 0) for item in items)
            discount_amount = 0
            final_amount = total
            
            if discount_code:
                discount = self.get_discount_by_code(discount_code)
                if discount and discount['is_active']:
                    discount_amount = total * (discount['discount_percent'] / 100)
                    final_amount = total - discount_amount
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO carts 
                    (user_id, items, total_amount, discount_amount, final_amount, discount_code)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, json.dumps(items), total, discount_amount, final_amount, discount_code))
                return True
        except Exception as e:
            logger.error(f"❌ ጋሪ ማዘመን አልተቻለም: {e}")
            return False
    
    def clear_cart(self, user_id: int) -> bool:
        """ጋሪ ማጽዳት"""
        try:
            self.execute("DELETE FROM carts WHERE user_id = ?", (user_id,))
            return True
        except Exception as e:
            logger.error(f"❌ ጋሪ ማጽዳት አልተቻለም: {e}")
            return False
    
    # ==================== የቅናሽ ስራዎች ====================
    
    def create_discount(self, data: Dict) -> Optional[int]:
        """አዲስ ቅናሽ መፍጠር"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO discounts (
                        code, discount_percent, description, discount_type,
                        min_order_amount, max_discount_amount,
                        valid_from, valid_to, usage_limit, user_limit
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    RETURNING id
                ''', (
                    data.get('code').upper(),
                    data.get('discount_percent'),
                    data.get('description'),
                    data.get('discount_type', 'percent'),
                    data.get('min_order_amount', 0),
                    data.get('max_discount_amount'),
                    data.get('valid_from'),
                    data.get('valid_to'),
                    data.get('usage_limit', 0),
                    data.get('user_limit', 0)
                ))
                return cursor.fetchone()['id']
        except Exception as e:
            logger.error(f"❌ ቅናሽ መፍጠር አልተቻለም: {e}")
            return None
    
    def get_discount_by_code(self, code: str) -> Optional[Dict]:
        """ቅናሽ በኮድ ማግኘት"""
        try:
            cursor = self.execute(
                "SELECT * FROM discounts WHERE code = ? AND is_active = 1",
                (code.upper(),)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"❌ ቅናሽ ማግኘት አልተቻለም: {e}")
            return None
    
    def use_discount(self, discount_id: int, user_id: int, order_id: int) -> bool:
        """ቅናሽ መጠቀም"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE discounts 
                    SET used_count = used_count + 1 
                    WHERE id = ? AND (usage_limit = 0 OR used_count < usage_limit)
                ''', (discount_id,))
                
                if cursor.rowcount == 0:
                    return False
                
                cursor.execute('''
                    INSERT INTO discount_usage (discount_id, user_id, order_id)
                    VALUES (?, ?, ?)
                ''', (discount_id, user_id, order_id))
                return True
        except Exception as e:
            logger.error(f"❌ ቅናሽ መጠቀም አልተቻለም: {e}")
            return False
    
    # ==================== የግምገማ ስራዎች ====================
    
    def add_review(self, data: Dict) -> bool:
        """ግምገማ መጨመር"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO reviews 
                    (user_id, product_id, rating, comment, images, is_verified)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    data.get('user_id'),
                    data.get('product_id'),
                    data.get('rating'),
                    data.get('comment'),
                    json.dumps(data.get('images', [])),
                    data.get('is_verified', 0)
                ))
                
                # የምርት አማካኝ ደረጃ ማስላት
                cursor.execute('''
                    SELECT AVG(rating) as avg_rating, COUNT(*) as count
                    FROM reviews WHERE product_id = ?
                ''', (data.get('product_id'),))
                result = cursor.fetchone()
                
                cursor.execute('''
                    UPDATE products 
                    SET rating_avg = ?, rating_count = ?
                    WHERE id = ?
                ''', (result['avg_rating'] or 0, result['count'], data.get('product_id')))
                
                return True
        except Exception as e:
            logger.error(f"❌ ግምገማ መጨመር አልተቻለም: {e}")
            return False
    
    def get_product_reviews(self, product_id: int, limit: int = 10) -> List[Dict]:
        """የምርት ግምገማዎች"""
        try:
            cursor = self.execute('''
                SELECT r.*, u.username, u.first_name
                FROM reviews r
                JOIN users u ON r.user_id = u.user_id
                WHERE r.product_id = ?
                ORDER BY r.created_at DESC
                LIMIT ?
            ''', (product_id, limit))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ ግምገማዎችን ማግኘት አልተቻለም: {e}")
            return []
    
    # ==================== የእንቅስቃሴ ሎግ ====================
    
    def log_activity(self, user_id: int, action: str, details: str = None,
                     ip: str = None, user_agent: str = None) -> bool:
        """እንቅስቃሴ መመዝገብ"""
        try:
            self.execute('''
                INSERT INTO activity_logs (user_id, action, details, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, action, details, ip, user_agent))
            return True
        except Exception as e:
            logger.error(f"❌ እንቅስቃሴ መመዝገብ አልተቻለም: {e}")
            return False
    
    def get_activity_logs(self, limit: int = 50) -> List[Dict]:
        """የእንቅስቃሴ ሎጎች"""
        try:
            cursor = self.execute('''
                SELECT * FROM activity_logs 
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ የእንቅስቃሴ ሎጎችን ማግኘት አልተቻለም: {e}")
            return []
    
    def get_user_activity(self, user_id: int, limit: int = 20) -> List[Dict]:
        """የተጠቃሚ እንቅስቃሴ"""
        try:
            cursor = self.execute('''
                SELECT * FROM activity_logs 
                WHERE user_id = ?
                ORDER BY created_at DESC 
                LIMIT ?
            ''', (user_id, limit))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ የተጠቃሚ እንቅስቃሴ ማግኘት አልተቻለም: {e}")
            return []
    
    # ==================== ሪፖርቶች ====================
    
    def get_sales_report(self, days: int = 30) -> List[Dict]:
        """የሽያጭ ሪፖርት"""
        try:
            cursor = self.execute('''
                SELECT 
                    DATE(order_date) as sale_date,
                    COUNT(*) as order_count,
                    SUM(final_amount) as total_sales,
                    AVG(final_amount) as avg_order_value,
                    SUM(discount_amount) as total_discounts,
                    SUM(shipping_amount) as total_shipping,
                    SUM(tax_amount) as total_tax
                FROM orders
                WHERE status = 'Delivered'
                AND order_date >= datetime('now', ?)
                GROUP BY DATE(order_date)
                ORDER BY sale_date DESC
            ''', (f'-{days} days',))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ የሽያጭ ሪፖርት ማግኘት አልተቻለም: {e}")
            return []
    
    def get_top_products(self, limit: int = 10) -> List[Dict]:
        """ከፍተኛ የተሸጡ ምርቶች"""
        try:
            cursor = self.execute('''
                SELECT 
                    p.id,
                    p.name_am,
                    p.name_en,
                    p.price,
                    p.image_id,
                    COUNT(oi.id) as sales_count,
                    SUM(oi.quantity) as total_sold,
                    SUM(oi.total_price) as total_revenue
                FROM products p
                LEFT JOIN order_items oi ON p.id = oi.product_id
                LEFT JOIN orders o ON oi.order_id = o.id AND o.status = 'Delivered'
                GROUP BY p.id
                ORDER BY total_sold DESC
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ ከፍተኛ ምርቶችን ማግኘት አልተቻለም: {e}")
            return []
    
    def get_category_stats(self) -> List[Dict]:
        """የምድብ ስታቲስቲክስ"""
        try:
            cursor = self.execute('''
                SELECT 
                    category,
                    COUNT(*) as product_count,
                    SUM(stock_quantity) as total_stock,
                    AVG(price) as avg_price,
                    SUM(sold_count) as total_sold
                FROM products
                GROUP BY category
                ORDER BY product_count DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"❌ የምድብ ስታቲስቲክስ ማግኘት አልተቻለም: {e}")
            return []
    
    def get_order_stats(self) -> Dict:
        """የትዕዛዝ ስታቲስቲክስ"""
        try:
            cursor = self.execute('''
                SELECT 
                    status,
                    COUNT(*) as count,
                    SUM(final_amount) as total_amount
                FROM orders
                GROUP BY status
            ''')
            stats = {row['status']: {'count': row['count'], 'total': row['total_amount']} 
                    for row in cursor.fetchall()}
            
            cursor = self.execute('''
                SELECT 
                    COUNT(*) as total_orders,
                    SUM(final_amount) as total_revenue,
                    AVG(final_amount) as avg_order_value,
                    MAX(final_amount) as max_order,
                    MIN(final_amount) as min_order
                FROM orders
                WHERE status = 'Delivered'
            ''')
            result = cursor.fetchone()
            
            stats['summary'] = {
                'total_orders': result['total_orders'] or 0,
                'total_revenue': result['total_revenue'] or 0,
                'avg_order_value': result['avg_order_value'] or 0,
                'max_order': result['max_order'] or 0,
                'min_order': result['min_order'] or 0
            }
            
            return stats
        except Exception as e:
            logger.error(f"❌ የትዕዛዝ ስታቲስቲክስ ማግኘት አልተቻለም: {e}")
            return {}
    
    def get_daily_stats(self) -> Dict:
        """የዕለት ስታቲስቲክስ"""
        try:
            cursor = self.execute('''
                SELECT 
                    (SELECT COUNT(*) FROM users WHERE DATE(registered_at) = DATE('now')) as new_users,
                    (SELECT COUNT(*) FROM orders WHERE DATE(order_date) = DATE('now')) as new_orders,
                    (SELECT COALESCE(SUM(final_amount), 0) FROM orders 
                     WHERE DATE(order_date) = DATE('now') AND status = 'Delivered') as daily_revenue,
                    (SELECT COUNT(*) FROM products WHERE DATE(created_at) = DATE('now')) as new_products
            ''')
            return dict(cursor.fetchone())
        except Exception as e:
            logger.error(f"❌ የዕለት ስታቲስቲክስ ማግኘት አልተቻለም: {e}")
            return {}


# የውሂብ ጎታ ክፍል ከማህበሩ ጋር
class Database(Database, DatabaseMixin):
    """የተሟላ የውሂብ ጎታ ክፍል"""
    pass


# ለሙከራ
if __name__ == '__main__':
    print("=" * 50)
    print("📊 የውሂብ ጎታ መረጃ")
    print("=" * 50)
    
    db = Database()
    stats = db.get_db_stats()
    print(f"\n📁 የውሂብ ጎታ መጠን: {stats['total_size'] / 1024:.2f} KB")
    print(f"📊 ጠቅላላ ረድፎች: {stats['total_rows']}")
    print("\n📋 ሰንጠረዦች:")
    
    for table, count in stats['tables'].items():
        print(f"  • {table}: {count} ረድፎች")
    
    # የዕለት ስታቲስቲክስ
    daily = db.get_daily_stats()
    print("\n📈 የዕለት ስታቲስቲክስ:")
    print(f"  • አዲስ ተጠቃሚዎች: {daily.get('new_users', 0)}")
    print(f"  • አዲስ ትዕዛዞች: {daily.get('new_orders', 0)}")
    print(f"  • የዕለት ገቢ: {daily.get('daily_revenue', 0):.2f} ETB")
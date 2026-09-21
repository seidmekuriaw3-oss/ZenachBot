import telebot
import sqlite3
import os
import json
import random
import string
from telebot import types
from datetime import datetime, timedelta
import threading
import time

# ==================== የቦት ቶከን ====================
TOKEN = '8600790961:AAFwU4nLsPo__-XJbg2iCR2tBmmPCMlDLCg'
bot = telebot.TeleBot(TOKEN)

# ==================== የአስተዳዳሪዎች ID ====================
ADMIN_IDS = [5848843259]  # ⚠️ ይህን በእርስዎ የቴሌግራም ID ይለውጡ

# ==================== የውሂብ ጎታ ክፍል ====================

class Database:
    def __init__(self, db_path='zenach.db'):
        self.db_path = db_path
        self.init_db()
        self.migrate_if_needed()
        print("✅ SQLite ዳታቤዝ ተዘጋጅቷል!")
    
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def migrate_if_needed(self):
        """የውሂብ ጎታን ወደ አዲሱ እትም ማሻሻል"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # የውሂብ ጎታ አምዶችን ማረጋገጥ
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        # የጎደሉትን አምዶች መጨመር
        new_columns = {
            'username': 'TEXT',
            'last_name': 'TEXT',
            'phone': 'TEXT',
            'is_subscribed': 'INTEGER DEFAULT 1'
        }
        
        for col, col_type in new_columns.items():
            if col not in columns:
                try:
                    cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type}")
                    print(f"✅ {col} አምድ ተጨምሯል")
                except sqlite3.OperationalError:
                    pass
        
        conn.commit()
        conn.close()
    
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 1. ምርቶች
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name_am TEXT NOT NULL,
                name_en TEXT NOT NULL,
                price REAL NOT NULL,
                size TEXT NOT NULL,
                category TEXT NOT NULL,
                image_id TEXT NOT NULL,
                status TEXT DEFAULT 'In Stock',
                stock_quantity INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 2. ተጠቃሚዎች
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone TEXT,
                lang TEXT DEFAULT 'am',
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_subscribed INTEGER DEFAULT 1
            )
        ''')
        
        # 3. ትዕዛዞች
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number TEXT UNIQUE NOT NULL,
                user_id INTEGER,
                total_amount REAL NOT NULL,
                discount_amount REAL DEFAULT 0,
                final_amount REAL NOT NULL,
                status TEXT DEFAULT 'Pending',
                payment_method TEXT,
                payment_status TEXT DEFAULT 'Unpaid',
                shipping_address TEXT,
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
                FOREIGN KEY (order_id) REFERENCES orders(id),
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
                valid_from TIMESTAMP,
                valid_to TIMESTAMP,
                usage_limit INTEGER DEFAULT 0,
                used_count INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 7. የቅናሽ አጠቃቀም ሎግ
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
        
        # 8. ማስታወቂያዎች
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title_am TEXT,
                title_en TEXT,
                message_am TEXT,
                message_en TEXT,
                image_id TEXT,
                product_id INTEGER,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_sent INTEGER DEFAULT 0
            )
        ''')
        
        # 9. የእንቅስቃሴ ሎግ
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 10. የሽያጭ ሪፖርቶች (የተቀመጡ)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sales_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_type TEXT,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
    
    # ========== የምርት ስራዎች ==========
    
    def add_product(self, name_am, name_en, price, size, category, image_id, stock_quantity=0):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO products (name_am, name_en, price, size, category, image_id, stock_quantity)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name_am, name_en, price, size, category, image_id, stock_quantity))
        
        product_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # ለተመዝጋቢዎች ማስታወቂያ መላክ
        self.notify_subscribers(product_id)
        
        return product_id
    
    def get_products(self, category=None, limit=20, offset=0):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if category:
            cursor.execute('''
                SELECT * FROM products 
                WHERE category = ? AND status = 'In Stock'
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (category, limit, offset))
        else:
            cursor.execute('''
                SELECT * FROM products 
                WHERE status = 'In Stock'
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            ''', (limit, offset))
        
        products = cursor.fetchall()
        conn.close()
        return products
    
    def get_product_by_id(self, product_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        product = cursor.fetchone()
        conn.close()
        return product
    
    def update_product(self, product_id, **kwargs):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        allowed_fields = ['name_am', 'name_en', 'price', 'size', 'category', 'image_id', 'status', 'stock_quantity']
        fields = []
        values = []
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                fields.append(f"{key} = ?")
                values.append(value)
        
        if fields:
            values.append(product_id)
            query = f"UPDATE products SET {', '.join(fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()
            conn.close()
            return True
        
        conn.close()
        return False
    
    def delete_product(self, product_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM products WHERE id = ?', (product_id,))
        conn.commit()
        conn.close()
        return True
    
    def get_product_count(self, category=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if category:
            cursor.execute('SELECT COUNT(*) FROM products WHERE category = ?', (category,))
        else:
            cursor.execute('SELECT COUNT(*) FROM products')
        
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_low_stock_products(self, threshold=5):
        """አነስተኛ ክምችት ያላቸውን ምርቶች ማግኘት"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM products 
            WHERE stock_quantity <= ? AND status = 'In Stock'
            ORDER BY stock_quantity ASC
        ''', (threshold,))
        products = cursor.fetchall()
        conn.close()
        return products
    
    # ========== የተጠቃሚ ስራዎች ==========
    
    def register_user(self, user_id, username=None, first_name=None, last_name=None, lang='am', phone=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # ተጠቃሚው መኖሩን ማረጋገጥ
        cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
        existing = cursor.fetchone()
        
        if existing:
            # ነባር ተጠቃሚን ማዘመን
            cursor.execute('''
                UPDATE users 
                SET username = COALESCE(?, username),
                    first_name = COALESCE(?, first_name),
                    last_name = COALESCE(?, last_name),
                    lang = COALESCE(?, lang),
                    phone = COALESCE(?, phone),
                    last_active = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (username, first_name, last_name, lang, phone, user_id))
        else:
            # አዲስ ተጠቃሚ መጨመር
            cursor.execute('''
                INSERT INTO users (user_id, username, first_name, last_name, lang, phone, last_active)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, username, first_name, last_name, lang, phone))
        
        conn.commit()
        conn.close()
        return True
    
    def get_user(self, user_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user
    
    def get_user_lang(self, user_id):
        user = self.get_user(user_id)
        return user['lang'] if user else 'am'
    
    def get_all_users(self):
        """ሁሉንም ተጠቃሚዎች ማግኘት"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users')
        users = cursor.fetchall()
        conn.close()
        return users
    
    def get_subscribed_users(self):
        """ተመዝጋቢ ተጠቃሚዎችን ማግኘት"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE is_subscribed = 1')
        users = cursor.fetchall()
        conn.close()
        return users
    
    def toggle_subscription(self, user_id):
        """የተመዝጋቢነት ሁኔታ መቀየር"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users 
            SET is_subscribed = CASE WHEN is_subscribed = 1 THEN 0 ELSE 1 END
            WHERE user_id = ?
        ''', (user_id,))
        conn.commit()
        conn.close()
        return True
    
    # ========== የትዕዛዝ ስራዎች ==========
    
    def generate_order_number(self):
        """የትዕዛዝ ቁጥር መፍጠር"""
        return f"ZEN{datetime.now().strftime('%Y%m%d%H%M%S')}{''.join(random.choices(string.digits, k=4))}"
    
    def create_order(self, user_id, items, shipping_address=None, payment_method=None, discount_code=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # ጠቅላላ ዋጋ ማስላት
        total_amount = 0
        for item in items:
            total_amount += float(item['price']) * int(item['quantity'])
        
        # ቅናሽ ማስላት
        discount_percent = 0
        discount_id = None
        
        if discount_code:
            cursor.execute('''
                SELECT * FROM discounts 
                WHERE code = ? AND is_active = 1 
                AND (valid_from IS NULL OR valid_from <= CURRENT_TIMESTAMP)
                AND (valid_to IS NULL OR valid_to >= CURRENT_TIMESTAMP)
                AND (usage_limit = 0 OR used_count < usage_limit)
            ''', (discount_code.upper(),))
            discount = cursor.fetchone()
            
            if discount:
                discount_percent = discount['discount_percent']
                discount_id = discount['id']
                
                # የቅናሽ አጠቃቀም መጨመር
                cursor.execute('''
                    UPDATE discounts SET used_count = used_count + 1 WHERE id = ?
                ''', (discount_id,))
        
        discount_amount = total_amount * (discount_percent / 100)
        final_amount = total_amount - discount_amount
        
        # ትዕዛዝ መፍጠር
        order_number = self.generate_order_number()
        cursor.execute('''
            INSERT INTO orders (order_number, user_id, total_amount, discount_amount, final_amount, 
                               shipping_address, payment_method)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (order_number, user_id, total_amount, discount_amount, final_amount, 
              shipping_address, payment_method))
        
        order_id = cursor.lastrowid
        
        # የትዕዛዝ ዝርዝሮችን መጨመር
        for item in items:
            cursor.execute('''
                INSERT INTO order_items (order_id, product_id, quantity, price_at_time)
                VALUES (?, ?, ?, ?)
            ''', (order_id, item['product_id'], item['quantity'], item['price']))
            
            # ክምችት መቀነስ
            cursor.execute('''
                UPDATE products 
                SET stock_quantity = stock_quantity - ?
                WHERE id = ? AND stock_quantity >= ?
            ''', (item['quantity'], item['product_id'], item['quantity']))
        
        # የቅናሽ አጠቃቀም መመዝገብ
        if discount_id:
            cursor.execute('''
                INSERT INTO discount_usage (discount_id, user_id, order_id)
                VALUES (?, ?, ?)
            ''', (discount_id, user_id, order_id))
        
        conn.commit()
        conn.close()
        
        # እንቅስቃሴ መመዝገብ
        self.log_activity(user_id, 'create_order', 
                         f"ትዕዛዝ {order_number} - ዋጋ: {final_amount} ETB")
        
        return {
            'order_id': order_id,
            'order_number': order_number,
            'total_amount': total_amount,
            'discount_amount': discount_amount,
            'final_amount': final_amount,
            'discount_percent': discount_percent
        }
    
    def get_user_orders(self, user_id, limit=20):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT o.*, COUNT(oi.id) as item_count
            FROM orders o
            LEFT JOIN order_items oi ON o.id = oi.order_id
            WHERE o.user_id = ?
            GROUP BY o.id
            ORDER BY o.order_date DESC
            LIMIT ?
        ''', (user_id, limit))
        
        orders = cursor.fetchall()
        conn.close()
        return orders
    
    def get_order_by_number(self, order_number):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM orders WHERE order_number = ?', (order_number,))
        order = cursor.fetchone()
        conn.close()
        return order
    
    def update_order_status(self, order_id, status):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (status, order_id))
        conn.commit()
        conn.close()
        return True
    
    # ========== የግምገማ ስራዎች ==========
    
    def add_review(self, user_id, product_id, rating, comment=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO reviews (user_id, product_id, rating, comment)
            VALUES (?, ?, ?, ?)
        ''', (user_id, product_id, rating, comment))
        
        conn.commit()
        conn.close()
        return True
    
    def get_product_reviews(self, product_id, limit=10):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.*, u.username, u.first_name
            FROM reviews r
            JOIN users u ON r.user_id = u.user_id
            WHERE r.product_id = ?
            ORDER BY r.created_at DESC
            LIMIT ?
        ''', (product_id, limit))
        
        reviews = cursor.fetchall()
        conn.close()
        return reviews
    
    def get_product_rating(self, product_id):
        """የምርት አማካኝ ደረጃ ማግኘት"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT AVG(rating) as avg_rating, COUNT(*) as review_count
            FROM reviews
            WHERE product_id = ?
        ''', (product_id,))
        
        result = cursor.fetchone()
        conn.close()
        return result
    
    # ========== የቅናሽ ስራዎች ==========
    
    def create_discount(self, code, discount_percent, description=None, 
                       valid_from=None, valid_to=None, usage_limit=0):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO discounts (code, discount_percent, description, valid_from, valid_to, usage_limit)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (code.upper(), discount_percent, description, valid_from, valid_to, usage_limit))
        
        discount_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return discount_id
    
    def get_all_discounts(self, active_only=True):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if active_only:
            cursor.execute('''
                SELECT * FROM discounts 
                WHERE is_active = 1 
                AND (valid_from IS NULL OR valid_from <= CURRENT_TIMESTAMP)
                AND (valid_to IS NULL OR valid_to >= CURRENT_TIMESTAMP)
                AND (usage_limit = 0 OR used_count < usage_limit)
                ORDER BY created_at DESC
            ''')
        else:
            cursor.execute('SELECT * FROM discounts ORDER BY created_at DESC')
        
        discounts = cursor.fetchall()
        conn.close()
        return discounts
    
    def delete_discount(self, discount_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM discounts WHERE id = ?', (discount_id,))
        conn.commit()
        conn.close()
        return True
    
    # ========== የማስታወቂያ ስራዎች ==========
    
    def create_notification(self, title_am, title_en, message_am, message_en, image_id=None, product_id=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO notifications (title_am, title_en, message_am, message_en, image_id, product_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (title_am, title_en, message_am, message_en, image_id, product_id))
        
        notification_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return notification_id
    
    def get_unsent_notifications(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM notifications 
            WHERE is_sent = 0 
            ORDER BY sent_at ASC
        ''')
        notifications = cursor.fetchall()
        conn.close()
        return notifications
    
    def mark_notification_sent(self, notification_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE notifications SET is_sent = 1 WHERE id = ?
        ''', (notification_id,))
        conn.commit()
        conn.close()
        return True
    
    def notify_subscribers(self, product_id, delay_seconds=0):
        """ለተመዝጋቢዎች ማስታወቂያ መላክ (እንደ ሂደት)"""
        def send_notification():
            time.sleep(delay_seconds)  # አማራጭ መዘግየት
            
            # የምርት መረጃ ማግኘት
            product = self.get_product_by_id(product_id)
            if not product:
                return
            
            subscribers = self.get_subscribed_users()
            if not subscribers:
                return
            
            # ለእያንዳንዱ ተመዝጋቢ መልእክት መላክ
            for user in subscribers:
                try:
                    lang = user['lang']
                    name = product['name_am'] if lang == 'am' else product['name_en']
                    price = product['price']
                    
                    msg = f"🆕 *አዲስ ምርት ተጨምሯል!*\n\n"
                    msg += f"📦 {name}\n"
                    msg += f"💰 ዋጋ: {price:.2f} ETB\n"
                    msg += f"📏 ሳይዝ: {product['size']}\n\n"
                    msg += "👉 /start በመጫን ይመልከቱ"
                    
                    try:
                        bot.send_message(user['user_id'], msg, parse_mode='Markdown')
                    except:
                        pass
                except:
                    pass
            
            # ማስታወቂያውን መመዝገብ
            self.create_notification(
                title_am=f"አዲስ ምርት: {product['name_am']}",
                title_en=f"New Product: {product['name_en']}",
                message_am=f"አዲስ ምርት ተጨምሯል: {product['name_am']}",
                message_en=f"New product added: {product['name_en']}",
                product_id=product_id
            )
        
        # በመለያ ሂደት ማስኬድ
        thread = threading.Thread(target=send_notification)
        thread.daemon = True
        thread.start()
    
    # ========== የሪፖርት ስራዎች ==========
    
    def get_sales_report(self, start_date=None, end_date=None):
        """የሽያጭ ሪፖርት ማግኘት"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if start_date and end_date:
            cursor.execute('''
                SELECT 
                    DATE(order_date) as sale_date,
                    COUNT(*) as order_count,
                    SUM(final_amount) as total_sales,
                    AVG(final_amount) as avg_order_value,
                    SUM(discount_amount) as total_discounts
                FROM orders
                WHERE status = 'Completed'
                AND order_date BETWEEN ? AND ?
                GROUP BY DATE(order_date)
                ORDER BY sale_date DESC
            ''', (start_date, end_date))
        else:
            cursor.execute('''
                SELECT 
                    DATE(order_date) as sale_date,
                    COUNT(*) as order_count,
                    SUM(final_amount) as total_sales,
                    AVG(final_amount) as avg_order_value,
                    SUM(discount_amount) as total_discounts
                FROM orders
                WHERE status = 'Completed'
                GROUP BY DATE(order_date)
                ORDER BY sale_date DESC
                LIMIT 30
            ''')
        
        report = cursor.fetchall()
        conn.close()
        return report
    
    def get_detailed_sales_report(self):
        """ዝርዝር የሽያጭ ሪፖርት"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                p.id as product_id,
                p.name_am,
                p.name_en,
                p.category,
                COUNT(oi.id) as times_sold,
                SUM(oi.quantity) as total_quantity,
                SUM(oi.quantity * oi.price_at_time) as total_revenue,
                AVG(r.rating) as avg_rating
            FROM products p
            LEFT JOIN order_items oi ON p.id = oi.product_id
            LEFT JOIN orders o ON oi.order_id = o.id AND o.status = 'Completed'
            LEFT JOIN reviews r ON p.id = r.product_id
            GROUP BY p.id
            ORDER BY total_revenue DESC
        ''')
        
        report = cursor.fetchall()
        conn.close()
        return report
    
    def get_user_activity_report(self, days=30):
        """የተጠቃሚ እንቅስቃሴ ሪፖርት"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                user_id,
                COUNT(*) as activity_count,
                MAX(created_at) as last_activity
            FROM activity_logs
            WHERE created_at >= datetime('now', ?)
            GROUP BY user_id
            ORDER BY activity_count DESC
            LIMIT 20
        ''', (f'-{days} days',))
        
        report = cursor.fetchall()
        conn.close()
        return report
    
    def get_top_products(self, limit=10):
        """በጣም የተሸጡ ምርቶች"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                p.id,
                p.name_am,
                p.name_en,
                p.price,
                COUNT(oi.id) as sales_count,
                SUM(oi.quantity) as total_sold
            FROM products p
            LEFT JOIN order_items oi ON p.id = oi.product_id
            LEFT JOIN orders o ON oi.order_id = o.id AND o.status = 'Completed'
            GROUP BY p.id
            ORDER BY total_sold DESC
            LIMIT ?
        ''', (limit,))
        
        products = cursor.fetchall()
        conn.close()
        return products
    
    # ========== የእንቅስቃሴ ሎግ ==========
    
    def log_activity(self, user_id, action, details=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO activity_logs (user_id, action, details)
            VALUES (?, ?, ?)
        ''', (user_id, action, details))
        conn.commit()
        conn.close()
    
    def get_activity_logs(self, limit=50):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM activity_logs 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (limit,))
        logs = cursor.fetchall()
        conn.close()
        return logs
    
    # ========== ማስተካከያ ተግባራት ==========
    
    def get_stats(self):
        """አጠቃላይ ስታቲስቲክስ"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM products WHERE status = "In Stock"')
        total_products = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*), SUM(final_amount) 
            FROM orders WHERE status = 'Completed'
        ''')
        completed_orders = cursor.fetchone()
        
        cursor.execute('''
            SELECT COUNT(*) FROM orders 
            WHERE status = 'Pending'
        ''')
        pending_orders = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT COUNT(*) FROM discounts 
            WHERE is_active = 1 
            AND (valid_from IS NULL OR valid_from <= CURRENT_TIMESTAMP)
            AND (valid_to IS NULL OR valid_to >= CURRENT_TIMESTAMP)
        ''')
        active_discounts = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_users': total_users,
            'total_products': total_products,
            'completed_orders': completed_orders[0] if completed_orders[0] else 0,
            'total_revenue': completed_orders[1] if completed_orders[1] else 0,
            'pending_orders': pending_orders,
            'active_discounts': active_discounts
        }

# ==================== የውሂብ ጎታ መፍጠር ====================
db = Database('zenach.db')

# ==================== ቋንቋ እና ጽሁፎች ====================

user_data = {}

strings = {
    'am': {
        'welcome': "እንኳን ወደ ዘናጭ ልብስ ቤት በሰላም መጡ! ምርጫዎን ይምረጡ፡",
        'men': "የወንድ ልብሶች 👕",
        'women': "የሴት ልብሶች 👗",
        'contact': "አድራሻና ስልክ 📍",
        'orders': "ትዕዛዞቼ 📋",
        'cart': "ጋሪ 🛒",
        'subscribe': "ለማስታወቂያ ተመዝገብ 📢",
        'unsubscribe': "ከማስታወቂያ ተመዝገብ 🔕",
        'profile': "መገለጫ 👤",
        'admin': "አስተዳደር ⚙️",
        'price': "ዋጋ",
        'size': "ሳይዝ",
        'status': "ሁኔታ",
        'in_stock': "በክምችት ላይ ✅",
        'sold_out': "ተሽጦ አልቋል ❌",
        'no_items': "ምንም እቃ የለም።",
        'next': "ቀጣይ ➡️",
        'prev': "⬅️ ወደኋላ",
        'buy': "ለመግዛት 🛍",
        'back': "🔙 ወደ መጀመሪያ",
        'review': "✍️ ግምገማ",
        'discount': "🏷️ ቅናሽ",
        'report': "📊 ሪፖርት",
        'add_product': "➕ ምርት ጨምር",
        'delete_product': "➖ ምርት ሰርዝ",
        'stats': "📈 ስታቲስቲክስ",
        'success': "✅ ተሳካ!",
        'error': "❌ ስህተት!",
        'warning': "⚠️ ማስጠንቀቂያ!",
        'order_confirmation': "✅ ትዕዛዝዎ ተረጋግጧል!",
        'order_number': "🔢 ትዕዛዝ ቁጥር",
        'total': "💰 ጠቅላላ",
        'discount_applied': "🏷️ ቅናሽ ተተግብሯል",
        'rating': "⭐ ደረጃ",
        'comment': "💬 አስተያየት",
        'no_reviews': "ምንም ግምገማ የለም"
    },
    'en': {
        'welcome': "Welcome to Zenach Boutique! Choose an option:",
        'men': "Men's Clothing 👕",
        'women': "Women's Clothing 👗",
        'contact': "Address & Phone 📍",
        'orders': "My Orders 📋",
        'cart': "Cart 🛒",
        'subscribe': "Subscribe to Updates 📢",
        'unsubscribe': "Unsubscribe 🔕",
        'profile': "Profile 👤",
        'admin': "Admin ⚙️",
        'price': "Price",
        'size': "Size",
        'status': "Status",
        'in_stock': "In Stock ✅",
        'sold_out': "Sold Out ❌",
        'no_items': "No items available.",
        'next': "Next ➡️",
        'prev': "⬅️ Back",
        'buy': "Buy Now 🛍",
        'back': "🔙 Main Menu",
        'review': "✍️ Review",
        'discount': "🏷️ Discount",
        'report': "📊 Report",
        'add_product': "➕ Add Product",
        'delete_product': "➖ Delete Product",
        'stats': "📈 Statistics",
        'success': "✅ Success!",
        'error': "❌ Error!",
        'warning': "⚠️ Warning!",
        'order_confirmation': "✅ Order confirmed!",
        'order_number': "🔢 Order Number",
        'total': "💰 Total",
        'discount_applied': "🏷️ Discount Applied",
        'rating': "⭐ Rating",
        'comment': "💬 Comment",
        'no_reviews': "No reviews yet"
    }
}

def get_lang(user_id):
    return db.get_user_lang(user_id)

def get_text(user_id, key):
    lang = get_lang(user_id)
    return strings[lang].get(key, key)

def get_text_lang(lang, key):
    return strings[lang].get(key, key)

# ==================== የቦት ትዕዛዞች ====================

# ----- የመጀመሪያ ትዕዛዝ -----

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    db.register_user(user_id, username, first_name, last_name)
    db.log_activity(user_id, 'start', 'ቦቱን ጀምሯል')
    
    # የቋንቋ ምርጫ
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("አማርኛ 🇪🇹", callback_data='lang_am'),
        types.InlineKeyboardButton("English 🇺🇸", callback_data='lang_en')
    )
    
    bot.send_message(
        message.chat.id, 
        "👋 እንኳን ደህና መጡ!\n\nቋንቋ ይምረጡ / Choose Language:",
        reply_markup=markup
    )

# ----- የቋንቋ ምርጫ -----

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def set_lang(call):
    lang = 'am' if call.data == 'lang_am' else 'en'
    user_id = call.from_user.id
    
    db.register_user(user_id, lang=lang)
    db.log_activity(user_id, 'set_lang', f'ቋንቋ: {lang}')
    
    # ዋና ሜኑ
    show_main_menu(call.message.chat.id, user_id)
    
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass

# ----- ዋና ሜኑ ማሳየት -----

def show_main_menu(chat_id, user_id):
    lang = get_lang(user_id)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    buttons = [
        get_text_lang(lang, 'men'),
        get_text_lang(lang, 'women'),
        get_text_lang(lang, 'contact'),
        get_text_lang(lang, 'orders'),
        get_text_lang(lang, 'profile')
    ]
    
    # የማስታወቂያ አዝራር
    user = db.get_user(user_id)
    if user and user['is_subscribed']:
        buttons.append(get_text_lang(lang, 'unsubscribe'))
    else:
        buttons.append(get_text_lang(lang, 'subscribe'))
    
    # የአስተዳዳሪ አዝራር
    if user_id in ADMIN_IDS:
        buttons.append(get_text_lang(lang, 'admin'))
    
    markup.add(*[types.KeyboardButton(btn) for btn in buttons])
    
    welcome_msg = get_text_lang(lang, 'welcome')
    bot.send_message(chat_id, welcome_msg, reply_markup=markup)

# ----- የመገለጫ ትዕዛዝ -----

@bot.message_handler(commands=['profile'])
def show_profile(message):
    user_id = message.from_user.id
    lang = get_lang(user_id)
    user = db.get_user(user_id)
    
    if not user:
        bot.send_message(message.chat.id, get_text_lang(lang, 'error'))
        return
    
    # ትዕዛዝ ብዛት
    orders = db.get_user_orders(user_id)
    order_count = len(orders)
    
    # የማስታወቂያ ሁኔታ
    sub_status = "✅ ተመዝጋቢ" if user['is_subscribed'] else "❌ አልተመዘገበም"
    
    profile_msg = f"""👤 *መገለጫ*

👤 ስም: {user['first_name'] or 'N/A'}
🔹 የተጠቃሚ ስም: @{user['username'] or 'N/A'}
🌍 ቋንቋ: {'አማርኛ' if user['lang'] == 'am' else 'English'}
📦 ትዕዛዞች: {order_count}
📢 ማስታወቂያ: {sub_status}
📅 የተመዘገበ: {user['registered_at']}"""

    bot.send_message(message.chat.id, profile_msg, parse_mode='Markdown')

# ----- ማስታወቂያ መቀየር -----

@bot.message_handler(func=lambda m: m.text in ['ለማስታወቂያ ተመዝገብ 📢', 'Subscribe to Updates 📢', 'ከማስታወቂያ ተመዝገብ 🔕', 'Unsubscribe 🔕'])
def toggle_subscription(message):
    user_id = message.from_user.id
    lang = get_lang(user_id)
    
    db.toggle_subscription(user_id)
    user = db.get_user(user_id)
    
    if user and user['is_subscribed']:
        bot.send_message(message.chat.id, "✅ ለማስታወቂያ ተመዝግበዋል! አዳዲስ ምርቶች ሲጨመሩ ይደርስዎታል.")
    else:
        bot.send_message(message.chat.id, "❌ ከማስታወቂያ ተመዝግበዋል!")
    
    show_main_menu(message.chat.id, user_id)

# ==================== የምርት ማሳያ ====================

def send_product(chat_id, category, index=0, lang='am'):
    """ምርት በፎቶ ማሳየት"""
    products = db.get_products(category, limit=20, offset=0)
    
    if not products:
        bot.send_message(chat_id, get_text_lang(lang, 'no_items'))
        return
    
    if index >= len(products):
        index = 0
    elif index < 0:
        index = len(products) - 1
    
    product = products[index]
    
    # የምርት ደረጃ
    rating_data = db.get_product_rating(product['id'])
    avg_rating = rating_data['avg_rating'] if rating_data and rating_data['avg_rating'] else 0
    review_count = rating_data['review_count'] if rating_data else 0
    
    stars = "⭐" * round(avg_rating) if avg_rating else "☆"
    
    name = product['name_am'] if lang == 'am' else product['name_en']
    status_text = get_text_lang(lang, 'in_stock') if product['status'] == 'In Stock' else get_text_lang(lang, 'sold_out')
    
    caption = f"""🔹 *{name}*
💰 {get_text_lang(lang, 'price')}: {product['price']:.2f} ETB
📏 {get_text_lang(lang, 'size')}: {product['size']}
📦 {get_text_lang(lang, 'status')}: {status_text}
📊 ክምችት: {product['stock_quantity']}
⭐ {stars} ({review_count} ግምገማ)
({index + 1}/{len(products)})"""
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    prev_btn = types.InlineKeyboardButton(
        get_text_lang(lang, 'prev'),
        callback_data=f"nav_{category}_{index-1}"
    )
    next_btn = types.InlineKeyboardButton(
        get_text_lang(lang, 'next'),
        callback_data=f"nav_{category}_{index+1}"
    )
    buy_btn = types.InlineKeyboardButton(
        get_text_lang(lang, 'buy'),
        callback_data=f"buy_{product['id']}"
    )
    review_btn = types.InlineKeyboardButton(
        get_text_lang(lang, 'review'),
        callback_data=f"review_{product['id']}"
    )
    back_btn = types.InlineKeyboardButton(
        get_text_lang(lang, 'back'),
        callback_data="main_menu"
    )
    
    markup.row(prev_btn, next_btn)
    markup.row(buy_btn, review_btn)
    markup.row(back_btn)
    
    try:
        bot.send_photo(
            chat_id,
            product['image_id'],
            caption=caption,
            reply_markup=markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        bot.send_message(chat_id, f"❌ ምርቱን ማሳየት አልተቻለም: {e}")

# ----- የምርት አሰሳ አያያዝ -----

@bot.callback_query_handler(func=lambda call: call.data.startswith('nav_'))
def handle_nav(call):
    _, category, index = call.data.split('_')
    user_id = call.from_user.id
    lang = get_lang(user_id)
    
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    
    send_product(call.message.chat.id, category, int(index), lang)

# ----- ወደ ዋና ሜኑ መመለስ -----

@bot.callback_query_handler(func=lambda call: call.data == 'main_menu')
def handle_main_menu(call):
    user_id = call.from_user.id
    
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    
    show_main_menu(call.message.chat.id, user_id)

# ==================== ግምገማ ሲስተም ====================

@bot.callback_query_handler(func=lambda call: call.data.startswith('review_'))
def review_product(call):
    product_id = int(call.data.split('_')[1])
    user_id = call.from_user.id
    lang = get_lang(user_id)
    
    product = db.get_product_by_id(product_id)
    if not product:
        bot.answer_callback_query(call.id, "❌ ምርቱ አልተገኘም!")
        return
    
    # ግምገማዎችን ማሳየት
    reviews = db.get_product_reviews(product_id)
    
    msg = f"📝 *ግምገማዎች ለ {product['name_am']}*\n\n"
    
    if reviews:
        for review in reviews:
            stars = "⭐" * review['rating']
            msg += f"{stars}\n"
            msg += f"👤 {review['first_name'] or 'Anonymous'}\n"
            if review['comment']:
                msg += f"💬 {review['comment']}\n"
            msg += f"📅 {review['created_at']}\n\n"
    else:
        msg += get_text_lang(lang, 'no_reviews') + "\n\n"
    
    # ግምገማ ለመስጠት አዝራር
    markup = types.InlineKeyboardMarkup()
    
    # የደረጃ አዝራሮች
    for i in range(1, 6):
        markup.add(types.InlineKeyboardButton(
            f"⭐ {i}",
            callback_data=f"rate_{product_id}_{i}"
        ))
    
    markup.add(types.InlineKeyboardButton(
        get_text_lang(lang, 'back'),
        callback_data=f"nav_{product['category']}_0"
    ))
    
    bot.send_message(call.message.chat.id, msg, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data.startswith('rate_'))
def add_rating(call):
    _, product_id, rating = call.data.split('_')
    user_id = call.from_user.id
    
    # አስተያየት ለመጨመር
    msg = bot.send_message(call.message.chat.id, "💬 አስተያየትዎን ይጻፉ (ካልፈለጉ 'skip' ይተይቡ):")
    bot.register_next_step_handler(msg, process_review_comment, int(product_id), int(rating), user_id)

def process_review_comment(message, product_id, rating, user_id):
    comment = None if message.text.lower() == 'skip' else message.text
    
    db.add_review(user_id, product_id, rating, comment)
    db.log_activity(user_id, 'add_review', f'ምርት {product_id} - ደረጃ {rating}')
    
    bot.send_message(message.chat.id, "✅ ግምገማዎ ተመዝግቧል! እናመሰግናለን! 🙏")
    
    # ወደ ምርት መመለስ
    product = db.get_product_by_id(product_id)
    send_product(message.chat.id, product['category'], 0, get_lang(user_id))

# ==================== ግዢ ሲስተም ====================

@bot.callback_query_handler(func=lambda call: call.data.startswith('buy_'))
def handle_buy(call):
    product_id = int(call.data.split('_')[1])
    user_id = call.from_user.id
    lang = get_lang(user_id)
    
    product = db.get_product_by_id(product_id)
    
    if not product:
        bot.answer_callback_query(call.id, "❌ ምርቱ አልተገኘም!")
        return
    
    if product['stock_quantity'] <= 0:
        bot.answer_callback_query(call.id, "❌ ክምችት የለም!")
        return
    
    # የቁጥር ምርጫ
    markup = types.InlineKeyboardMarkup(row_width=3)
    
    for qty in range(1, min(6, product['stock_quantity'] + 1)):
        markup.add(types.InlineKeyboardButton(
            f"{qty}",
            callback_data=f"qty_{product_id}_{qty}"
        ))
    
    markup.add(types.InlineKeyboardButton(
        get_text_lang(lang, 'back'),
        callback_data=f"nav_{product['category']}_0"
    ))
    
    bot.send_message(
        call.message.chat.id,
        f"🛍 *{product['name_am'] if lang == 'am' else product['name_en']}*\n"
        f"💰 ዋጋ: {product['price']:.2f} ETB\n\n"
        f"📦 ብዛት ይምረጡ:",
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('qty_'))
def select_quantity(call):
    _, product_id, quantity = call.data.split('_')
    product_id = int(product_id)
    quantity = int(quantity)
    user_id = call.from_user.id
    lang = get_lang(user_id)
    
    product = db.get_product_by_id(product_id)
    
    if not product:
        bot.answer_callback_query(call.id, "❌ ምርቱ አልተገኘም!")
        return
    
    total = product['price'] * quantity
    
    # ቅናሽ ካለ
    discounts = db.get_all_discounts(active_only=True)
    discount_text = ""
    
    if discounts:
        discount_text = "\n\n🏷️ *የቅናሽ ኮዶች:*\n"
        for d in discounts[:3]:
            discount_text += f"• {d['code']} - {d['discount_percent']}% ቅናሽ\n"
    
    markup = types.InlineKeyboardMarkup()
    confirm_btn = types.InlineKeyboardButton(
        "✅ አረጋግጥ",
        callback_data=f"confirm_{product_id}_{quantity}"
    )
    discount_btn = types.InlineKeyboardButton(
        "🏷️ ቅናሽ አስገባ",
        callback_data=f"discount_{product_id}_{quantity}"
    )
    cancel_btn = types.InlineKeyboardButton(
        "❌ ሰርዝ",
        callback_data=f"nav_{product['category']}_0"
    )
    
    markup.row(confirm_btn)
    markup.row(discount_btn)
    markup.row(cancel_btn)
    
    msg = f"🛍 *{product['name_am'] if lang == 'am' else product['name_en']}*\n"
    msg += f"📦 ብዛት: {quantity}\n"
    msg += f"💰 ጠቅላላ: {total:.2f} ETB\n"
    msg += f"📏 ሳይዝ: {product['size']}"
    msg += discount_text
    
    bot.send_message(
        call.message.chat.id,
        msg,
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('discount_'))
def apply_discount(call):
    _, product_id, quantity = call.data.split('_')
    user_id = call.from_user.id
    
    msg = bot.send_message(
        call.message.chat.id,
        "🏷️ የቅናሽ ኮዱን ያስገቡ:"
    )
    bot.register_next_step_handler(msg, process_discount_code, int(product_id), int(quantity), user_id)

def process_discount_code(message, product_id, quantity, user_id):
    code = message.text.upper()
    lang = get_lang(user_id)
    
    product = db.get_product_by_id(product_id)
    if not product:
        bot.send_message(message.chat.id, "❌ ምርቱ አልተገኘም!")
        return
    
    # ቅናሹን ማረጋገጥ
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM discounts 
        WHERE code = ? AND is_active = 1 
        AND (valid_from IS NULL OR valid_from <= CURRENT_TIMESTAMP)
        AND (valid_to IS NULL OR valid_to >= CURRENT_TIMESTAMP)
        AND (usage_limit = 0 OR used_count < usage_limit)
    ''', (code,))
    
    discount = cursor.fetchone()
    conn.close()
    
    if not discount:
        bot.send_message(message.chat.id, "❌ የቅናሽ ኮዱ ልክ አይደለም ወይም ጊዜው አልፏል!")
        return
    
    # ቅናሽ መተግበር
    total = product['price'] * quantity
    discount_amount = total * (discount['discount_percent'] / 100)
    final_total = total - discount_amount
    
    # ትዕዛዝ መፍጠር
    items = [{'product_id': product_id, 'quantity': quantity, 'price': product['price']}]
    
    order = db.create_order(
        user_id=user_id,
        items=items,
        discount_code=code
    )
    
    if order:
        # ለአስተዳዳሪ ማሳወቅ
        for admin_id in ADMIN_IDS:
            try:
                admin_msg = f"🆕 *አዲስ ትዕዛዝ!*\n\n"
                admin_msg += f"👤 ተጠቃሚ: @{message.from_user.username or 'Unknown'}\n"
                admin_msg += f"📦 ምርት: {product['name_am']}\n"
                admin_msg += f"📦 ብዛት: {quantity}\n"
                admin_msg += f"💰 ዋጋ: {product['price']:.2f} ETB\n"
                admin_msg += f"🏷️ ቅናሽ: {discount['discount_percent']}%\n"
                admin_msg += f"💰 ጠቅላላ: {order['final_amount']:.2f} ETB\n"
                admin_msg += f"🔢 ትዕዛዝ: {order['order_number']}"
                
                bot.send_message(admin_id, admin_msg, parse_mode='Markdown')
            except:
                pass
        
        bot.send_message(
            message.chat.id,
            f"✅ {get_text_lang(lang, 'order_confirmation')}\n\n"
            f"🔢 {get_text_lang(lang, 'order_number')}: {order['order_number']}\n"
            f"💰 {get_text_lang(lang, 'total')}: {order['final_amount']:.2f} ETB\n"
            f"🏷️ {get_text_lang(lang, 'discount_applied')}: {discount['discount_percent']}%\n\n"
            f"በቅርቡ እናገኝዎታለን! 🙏"
        )
        
        db.log_activity(user_id, 'purchase', 
                       f"ምርት {product_id}, ብዛት {quantity}, ጠቅላላ {order['final_amount']}")
    else:
        bot.send_message(message.chat.id, "❌ ትዕዛዙ መስራት አልተቻለም!")

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_'))
def confirm_order(call):
    _, product_id, quantity = call.data.split('_')
    user_id = call.from_user.id
    lang = get_lang(user_id)
    
    product = db.get_product_by_id(int(product_id))
    
    if not product:
        bot.answer_callback_query(call.id, "❌ ምርቱ አልተገኘም!")
        return
    
    # ትዕዛዝ መፍጠር
    items = [{'product_id': int(product_id), 'quantity': int(quantity), 'price': product['price']}]
    
    order = db.create_order(
        user_id=user_id,
        items=items
    )
    
    if order:
        # ለአስተዳዳሪ ማሳወቅ
        for admin_id in ADMIN_IDS:
            try:
                admin_msg = f"🆕 *አዲስ ትዕዛዝ!*\n\n"
                admin_msg += f"👤 ተጠቃሚ: @{call.from_user.username or 'Unknown'}\n"
                admin_msg += f"📦 ምርት: {product['name_am']}\n"
                admin_msg += f"📦 ብዛት: {quantity}\n"
                admin_msg += f"💰 ጠቅላላ: {order['final_amount']:.2f} ETB\n"
                admin_msg += f"🔢 ትዕዛዝ: {order['order_number']}"
                
                bot.send_message(admin_id, admin_msg, parse_mode='Markdown')
            except:
                pass
        
        bot.send_message(
            call.message.chat.id,
            f"✅ {get_text_lang(lang, 'order_confirmation')}\n\n"
            f"🔢 {get_text_lang(lang, 'order_number')}: {order['order_number']}\n"
            f"💰 {get_text_lang(lang, 'total')}: {order['final_amount']:.2f} ETB\n\n"
            f"በቅርቡ እናገኝዎታለን! 🙏"
        )
        
        db.log_activity(user_id, 'purchase', 
                       f"ምርት {product_id}, ብዛት {quantity}, ጠቅላላ {order['final_amount']}")
    else:
        bot.send_message(call.message.chat.id, "❌ ትዕዛዙ መስራት አልተቻለም!")

# ==================== ትዕዛዞቼ ====================

@bot.message_handler(func=lambda m: m.text in ['ትዕዛዞቼ 📋', 'My Orders 📋'])
def show_orders(message):
    user_id = message.from_user.id
    lang = get_lang(user_id)
    
    orders = db.get_user_orders(user_id)
    
    if not orders:
        bot.send_message(message.chat.id, "📭 ምንም ትዕዛዝ የለም")
        return
    
    msg = "📋 *ትዕዛዞቼ*\n\n"
    
    for order in orders[:10]:
        msg += f"🔹 *{order['order_number']}*\n"
        msg += f"💰 {order['final_amount']:.2f} ETB\n"
        msg += f"📦 {order['status']}\n"
        if order['discount_amount'] > 0:
            msg += f"🏷️ ቅናሽ: {order['discount_amount']:.2f} ETB\n"
        msg += f"📅 {order['order_date']}\n\n"
    
    bot.send_message(message.chat.id, msg, parse_mode='Markdown')

# ==================== የአስተዳዳሪ ትዕዛዞች ====================

@bot.message_handler(func=lambda m: m.text in ['አስተዳደር ⚙️', 'Admin ⚙️'])
def admin_panel(message):
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "⛔ ፈቃድ የለዎትም!")
        return
    
    lang = get_lang(user_id)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    admin_buttons = [
        get_text_lang(lang, 'add_product'),
        get_text_lang(lang, 'delete_product'),
        get_text_lang(lang, 'discount'),
        get_text_lang(lang, 'report'),
        get_text_lang(lang, 'stats'),
        get_text_lang(lang, 'back')
    ]
    
    markup.add(*[types.KeyboardButton(btn) for btn in admin_buttons])
    
    bot.send_message(
        message.chat.id,
        "⚙️ *የአስተዳዳሪ ፓነል*\n\nእባክዎ የሚፈልጉትን ይምረጡ:",
        reply_markup=markup,
        parse_mode='Markdown'
    )

# ----- ምርት መጨመር -----

@bot.message_handler(func=lambda m: m.text in ['➕ ምርት ጨምር', '➕ Add Product'])
def add_product_start(message):
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(message.chat.id, "📝 የምርቱን ስም በአማርኛ ያስገቡ:")
    bot.register_next_step_handler(msg, process_name_am)

def process_name_am(message):
    user_data['name_am'] = message.text
    msg = bot.send_message(message.chat.id, "📝 ስሙን በእንግሊዝኛ ያስገቡ:")
    bot.register_next_step_handler(msg, process_name_en)

def process_name_en(message):
    user_data['name_en'] = message.text
    msg = bot.send_message(message.chat.id, "💰 ዋጋ ያስገቡ (በብር):")
    bot.register_next_step_handler(msg, process_price)

def process_price(message):
    try:
        user_data['price'] = float(message.text)
        msg = bot.send_message(message.chat.id, "📏 ሳይዝ (S, M, L, XL...):")
        bot.register_next_step_handler(msg, process_size)
    except:
        msg = bot.send_message(message.chat.id, "❌ እባክዎ ትክክለኛ ቁጥር ያስገቡ!")
        bot.register_next_step_handler(msg, process_price)

def process_size(message):
    user_data['size'] = message.text.upper()
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    markup.add("Men", "Women")
    msg = bot.send_message(message.chat.id, "👕 ምድብ ይምረጡ:", reply_markup=markup)
    bot.register_next_step_handler(msg, process_category)

def process_category(message):
    if message.text in ['Men', 'Women']:
        user_data['category'] = message.text
        msg = bot.send_message(message.chat.id, "📦 የክምችት ብዛት ያስገቡ:")
        bot.register_next_step_handler(msg, process_stock)
    else:
        msg = bot.send_message(message.chat.id, "❌ እባክዎ 'Men' ወይም 'Women' ብለው ይምረጡ!")
        bot.register_next_step_handler(msg, process_category)

def process_stock(message):
    try:
        user_data['stock'] = int(message.text)
        msg = bot.send_message(message.chat.id, "📸 የምርቱን ፎቶ ይላኩ:")
        bot.register_next_step_handler(msg, process_photo)
    except:
        msg = bot.send_message(message.chat.id, "❌ እባክዎ ትክክለኛ ቁጥር ያስገቡ!")
        bot.register_next_step_handler(msg, process_stock)

def process_photo(message):
    if message.content_type == 'photo':
        image_id = message.photo[-1].file_id
        
        product_id = db.add_product(
            name_am=user_data['name_am'],
            name_en=user_data['name_en'],
            price=user_data['price'],
            size=user_data['size'],
            category=user_data['category'],
            image_id=image_id,
            stock_quantity=user_data['stock']
        )
        
        if product_id:
            bot.send_message(
                message.chat.id,
                f"✅ ምርቱ በተሳካ ሁኔታ ተጨምሯል!\n🆔 ID: {product_id}\n\n📢 ለተመዝጋቢዎች ማስታወቂያ ተልኳል!"
            )
            db.log_activity(message.from_user.id, 'add_product', 
                           f"ምርት: {user_data['name_am']}, ID: {product_id}")
        else:
            bot.send_message(message.chat.id, "❌ ምርቱ መጨመር አልተቻለም!")
        
        user_data.clear()
    else:
        msg = bot.send_message(message.chat.id, "❌ እባክዎ ፎቶ ይላኩ!")
        bot.register_next_step_handler(msg, process_photo)

# ----- ምርት መሰረዝ -----

@bot.message_handler(func=lambda m: m.text in ['➖ ምርት ሰርዝ', '➖ Delete Product'])
def delete_product_start(message):
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(message.chat.id, "🆔 መሰረዝ የሚፈልጉትን ምርት ID ያስገቡ:")
    bot.register_next_step_handler(msg, process_delete_product)

def process_delete_product(message):
    try:
        product_id = int(message.text)
        product = db.get_product_by_id(product_id)
        
        if product:
            db.delete_product(product_id)
            db.log_activity(message.from_user.id, 'delete_product', 
                           f"ምርት: {product['name_am']}, ID: {product_id}")
            bot.send_message(
                message.chat.id,
                f"✅ ምርቱ '{product['name_am']}' ተሰርዟል!"
            )
        else:
            bot.send_message(message.chat.id, "❌ ምርቱ አልተገኘም!")
    except:
        bot.send_message(message.chat.id, "⚠️ እባክዎ ትክክለኛ ቁጥር ያስገቡ!")

# ----- የቅናሽ አስተዳደር -----

@bot.message_handler(func=lambda m: m.text in ['🏷️ ቅናሽ', '🏷️ Discount'])
def discount_management(message):
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        return
    
    lang = get_lang(user_id)
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ አዲስ ቅናሽ", callback_data="new_discount"),
        types.InlineKeyboardButton("📋 ቅናሾችን አሳይ", callback_data="list_discounts"),
        types.InlineKeyboardButton("🔙 ወደኋላ", callback_data="admin_back")
    )
    
    bot.send_message(
        message.chat.id,
        "🏷️ *የቅናሽ አስተዳደር*\n\nእባክዎ የሚፈልጉትን ይምረጡ:",
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data == 'new_discount')
def create_discount_form(call):
    user_id = call.from_user.id
    
    if user_id not in ADMIN_IDS:
        return
    
    msg = bot.send_message(
        call.message.chat.id,
        "🏷️ *አዲስ ቅናሽ መፍጠር*\n\n"
        "የቅናሽ ኮዱን ያስገቡ (እንግሊዝኛ ፊደላት እና ቁጥሮች):"
    )
    bot.register_next_step_handler(msg, process_discount_code_form)

def process_discount_code_form(message):
    user_data['discount_code'] = message.text.upper()
    msg = bot.send_message(
        message.chat.id,
        "🏷️ የቅናሽ መቶኛ ያስገቡ (1-100):"
    )
    bot.register_next_step_handler(msg, process_discount_percent)

def process_discount_percent(message):
    try:
        percent = float(message.text)
        if 1 <= percent <= 100:
            user_data['discount_percent'] = percent
            msg = bot.send_message(
                message.chat.id,
                "📝 መግለጫ ያስገቡ (አማራጭ):"
            )
            bot.register_next_step_handler(msg, process_discount_desc)
        else:
            msg = bot.send_message(message.chat.id, "❌ እባክዎ ከ1 እስከ 100 መካከል ያስገቡ!")
            bot.register_next_step_handler(msg, process_discount_percent)
    except:
        msg = bot.send_message(message.chat.id, "❌ እባክዎ ትክክለኛ ቁጥር ያስገቡ!")
        bot.register_next_step_handler(msg, process_discount_percent)

def process_discount_desc(message):
    user_data['discount_desc'] = message.text if message.text != 'skip' else None
    msg = bot.send_message(
        message.chat.id,
        "📅 የሚያልቅበትን ቀን ያስገቡ (YYYY-MM-DD) ወይም 'skip' ይተይቡ:"
    )
    bot.register_next_step_handler(msg, process_discount_date)

def process_discount_date(message):
    try:
        if message.text.lower() != 'skip':
            valid_to = datetime.strptime(message.text, '%Y-%m-%d').strftime('%Y-%m-%d')
        else:
            valid_to = None
        
        # ቅናሽ መፍጠር
        discount_id = db.create_discount(
            code=user_data['discount_code'],
            discount_percent=user_data['discount_percent'],
            description=user_data['discount_desc'],
            valid_to=valid_to
        )
        
        if discount_id:
            bot.send_message(
                message.chat.id,
                f"✅ ቅናሽ በተሳካ ሁኔታ ተፈጥሯል!\n"
                f"🏷️ ኮድ: {user_data['discount_code']}\n"
                f"📊 ቅናሽ: {user_data['discount_percent']}%\n"
                f"📅 የሚያልቅ: {valid_to or 'ምንም ገደብ የለም'}"
            )
            db.log_activity(message.from_user.id, 'create_discount', 
                           f"ኮድ: {user_data['discount_code']}, {user_data['discount_percent']}%")
        else:
            bot.send_message(message.chat.id, "❌ ቅናሹን መፍጠር አልተቻለም!")
        
        user_data.clear()
    except:
        msg = bot.send_message(message.chat.id, "❌ እባክዎ ትክክለኛ ቀን ያስገቡ (YYYY-MM-DD)!")
        bot.register_next_step_handler(msg, process_discount_date)

@bot.callback_query_handler(func=lambda call: call.data == 'list_discounts')
def list_discounts(call):
    user_id = call.from_user.id
    
    if user_id not in ADMIN_IDS:
        return
    
    discounts = db.get_all_discounts(active_only=False)
    
    if not discounts:
        bot.send_message(call.message.chat.id, "📭 ምንም ቅናሽ የለም")
        return
    
    msg = "🏷️ *ሁሉም ቅናሾች*\n\n"
    
    for d in discounts:
        status = "✅ ንቁ" if d['is_active'] else "❌ ያልነቃ"
        used = f"{d['used_count']}/{d['usage_limit'] or '∞'}"
        valid = f"{d['valid_from'] or 'ማንኛውም'} - {d['valid_to'] or 'ማንኛውም'}"
        
        msg += f"🔹 *{d['code']}*\n"
        msg += f"📊 {d['discount_percent']}% ቅናሽ\n"
        msg += f"📦 ጥቅም: {used}\n"
        msg += f"📅 {valid}\n"
        msg += f"📊 {status}\n"
        msg += f"💬 {d['description'] or 'ምንም መግለጫ የለም'}\n\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 ወደኋላ", callback_data="admin_back"))
    
    bot.send_message(call.message.chat.id, msg, reply_markup=markup, parse_mode='Markdown')

# ----- ሪፖርቶች -----

@bot.message_handler(func=lambda m: m.text in ['📊 ሪፖርት', '📊 Report'])
def show_reports(message):
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        return
    
    lang = get_lang(user_id)
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 የሽያጭ ሪፖርት", callback_data="sales_report"),
        types.InlineKeyboardButton("🏆 ከፍተኛ ምርቶች", callback_data="top_products"),
        types.InlineKeyboardButton("📋 ዝርዝር ሪፖርት", callback_data="detailed_report"),
        types.InlineKeyboardButton("👥 የተጠቃሚ እንቅስቃሴ", callback_data="user_activity"),
        types.InlineKeyboardButton("🔙 ወደኋላ", callback_data="admin_back")
    )
    
    bot.send_message(
        message.chat.id,
        "📊 *የሪፖርት ሜኑ*\n\nእባክዎ የሚፈልጉትን ይምረጡ:",
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data == 'sales_report')
def sales_report(call):
    user_id = call.from_user.id
    
    if user_id not in ADMIN_IDS:
        return
    
    report = db.get_sales_report()
    
    if not report:
        bot.send_message(call.message.chat.id, "📭 ምንም የሽያጭ መረጃ የለም")
        return
    
    msg = "📊 *የሽያጭ ሪፖርት (የ30 ቀናት)*\n\n"
    
    total_sales = 0
    total_orders = 0
    
    for row in report:
        msg += f"📅 *{row['sale_date']}*\n"
        msg += f"📦 ትዕዛዞች: {row['order_count']}\n"
        msg += f"💰 ሽያጭ: {row['total_sales']:.2f} ETB\n"
        msg += f"📊 አማካኝ: {row['avg_order_value']:.2f} ETB\n"
        if row['total_discounts']:
            msg += f"🏷️ ቅናሽ: {row['total_discounts']:.2f} ETB\n"
        msg += "\n"
        
        total_sales += row['total_sales'] or 0
        total_orders += row['order_count'] or 0
    
    msg += f"📊 *ጠቅላላ*: {total_sales:.2f} ETB\n"
    msg += f"📦 *ጠቅላላ ትዕዛዝ*: {total_orders}"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 ወደ ሪፖርቶች", callback_data="reports_back"))
    
    bot.send_message(call.message.chat.id, msg, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == 'top_products')
def top_products(call):
    user_id = call.from_user.id
    
    if user_id not in ADMIN_IDS:
        return
    
    products = db.get_top_products(limit=10)
    
    if not products:
        bot.send_message(call.message.chat.id, "📭 ምንም የሽያጭ መረጃ የለም")
        return
    
    msg = "🏆 *ከፍተኛ የተሸጡ ምርቶች*\n\n"
    
    for i, product in enumerate(products, 1):
        msg += f"{i}. *{product['name_am']}*\n"
        msg += f"📦 የተሸጠ: {product['total_sold'] or 0}\n"
        msg += f"💰 ዋጋ: {product['price']:.2f} ETB\n\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 ወደ ሪፖርቶች", callback_data="reports_back"))
    
    bot.send_message(call.message.chat.id, msg, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == 'detailed_report')
def detailed_report(call):
    user_id = call.from_user.id
    
    if user_id not in ADMIN_IDS:
        return
    
    report = db.get_detailed_sales_report()
    
    if not report:
        bot.send_message(call.message.chat.id, "📭 ምንም መረጃ የለም")
        return
    
    msg = "📋 *ዝርዝር የምርት ሪፖርት*\n\n"
    
    for product in report[:20]:
        msg += f"🔹 *{product['name_am']}*\n"
        msg += f"📦 የተሸጠ: {product['total_quantity'] or 0}\n"
        msg += f"💰 ገቢ: {product['total_revenue'] or 0:.2f} ETB\n"
        msg += f"⭐ ደረጃ: {product['avg_rating'] or 'ምንም'}\n"
        msg += f"📊 ምድብ: {product['category']}\n\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 ወደ ሪፖርቶች", callback_data="reports_back"))
    
    bot.send_message(call.message.chat.id, msg, reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == 'user_activity')
def user_activity(call):
    user_id = call.from_user.id
    
    if user_id not in ADMIN_IDS:
        return
    
    report = db.get_user_activity_report(days=30)
    
    if not report:
        bot.send_message(call.message.chat.id, "📭 ምንም እንቅስቃሴ የለም")
        return
    
    msg = "👥 *ንቁ ተጠቃሚዎች (የ30 ቀናት)*\n\n"
    
    for i, activity in enumerate(report, 1):
        user = db.get_user(activity['user_id'])
        name = user['first_name'] if user else 'Unknown'
        
        msg += f"{i}. 👤 {name}\n"
        msg += f"📊 እንቅስቃሴ: {activity['activity_count']}\n"
        msg += f"📅 የመጨረሻ: {activity['last_activity']}\n\n"
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 ወደ ሪፖርቶች", callback_data="reports_back"))
    
    bot.send_message(call.message.chat.id, msg, reply_markup=markup, parse_mode='Markdown')

# ----- ስታቲስቲክስ -----

@bot.message_handler(func=lambda m: m.text in ['📈 ስታቲስቲክስ', '📈 Statistics'])
def show_stats(message):
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        return
    
    stats = db.get_stats()
    
    msg = f"""📊 *የዘናጭ ቦት ስታቲስቲክስ*

👥 ጠቅላላ ተጠቃሚዎች: {stats['total_users']}
📦 ንቁ ምርቶች: {stats['total_products']}
📋 የተጠናቀቁ ትዕዛዞች: {stats['completed_orders']}
💰 ጠቅላላ ገቢ: {stats['total_revenue']:.2f} ETB
⏳ በመጠባበቅ ላይ: {stats['pending_orders']}
🏷️ ንቁ ቅናሾች: {stats['active_discounts']}

📅 የተሻሻለ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """
    
    bot.send_message(message.chat.id, msg, parse_mode='Markdown')

# ----- አስተዳዳሪ ወደኋላ -----

@bot.callback_query_handler(func=lambda call: call.data == 'admin_back')
def admin_back(call):
    user_id = call.from_user.id
    lang = get_lang(user_id)
    
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    
    admin_panel(call.message)

@bot.callback_query_handler(func=lambda call: call.data == 'reports_back')
def reports_back(call):
    user_id = call.from_user.id
    lang = get_lang(user_id)
    
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    
    show_reports(call.message)

# ==================== ዋናው መልእክት አያያዝ ====================

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    lang = get_lang(user_id)
    text = message.text
    
    # የተጠቃሚ እንቅስቃሴ መመዝገብ
    db.register_user(user_id, lang=lang)
    
    # የምርት ምድቦች
    if text in [strings['am']['men'], strings['en']['men']]:
        send_product(message.chat.id, 'Men', 0, lang)
    
    elif text in [strings['am']['women'], strings['en']['women']]:
        send_product(message.chat.id, 'Women', 0, lang)
    
    # አድራሻ
    elif text in [strings['am']['contact'], strings['en']['contact']]:
        bot.send_message(
            message.chat.id,
            "📍 አድራሻ፡ አዳማ፣ ኢትዮጵያ\n"
            "📞 ስልክ፡ +251905027574\n\n"
            "⏰ የስራ ሰአት፡ ከሰኞ - ቅዳሜ 9:00 - 18:00\n"
            "📧 ኢሜይል፡ zenach@example.com"
        )
    
    # ትዕዛዞች
    elif text in [strings['am']['orders'], strings['en']['orders']]:
        orders = db.get_user_orders(user_id)
        
        if orders:
            msg = "📋 *ትዕዛዞቼ*\n\n"
            for order in orders[:10]:
                msg += f"🔹 *{order['order_number']}*\n"
                msg += f"💰 {order['final_amount']:.2f} ETB\n"
                msg += f"📦 {order['status']}\n"
                msg += f"📅 {order['order_date']}\n\n"
            bot.send_message(message.chat.id, msg, parse_mode='Markdown')
        else:
            bot.send_message(message.chat.id, "📭 ምንም ትዕዛዝ የለም")
    
    # መገለጫ
    elif text in [strings['am']['profile'], strings['en']['profile']]:
        show_profile(message)
    
    # ሌላ
    else:
        bot.send_message(
            message.chat.id,
            "❓ እባክዎ ከላይ ካሉት አዝራሮች ይምረጡ\n\n"
            "💡 ማንኛውም ጥያቄ ካለ: /start ይጫኑ"
        )

# ==================== የስህተት አያያዝ ====================

@bot.message_handler(commands=['error_test'])
def error_test(message):
    # ይህ ለሙከራ ብቻ
    pass

# ==================== ቦቱን ማስጀመር ====================

def start_bot():
    print("=" * 50)
    print("🤖 ዘናጭ ቦት እየሰራ ነው...")
    print(f"📱 የተመዘገቡ አስተዳዳሪዎች: {len(ADMIN_IDS)}")
    print(f"🗄️ የውሂብ ጎታ: SQLite (zenach.db)")
    print(f"⏰ ጊዜ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=30)
            break
        except Exception as e:
            print(f"❌ ስህተት: {e}")
            print("🔄 ከ5 ሰከንድ በኋላ እንደገና እሞክራለሁ...")
            time.sleep(5)

if __name__ == '__main__':
    start_bot()
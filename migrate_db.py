import sqlite3

def migrate():
    conn = sqlite3.connect('zenach.db')
    cursor = conn.cursor()
    
    # አምዶችን ለመጨመር
    columns = ['username', 'last_name', 'phone', 'is_subscribed']
    for col in columns:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT")
            print(f"✅ {col} ተጨምሯል")
        except:
            print(f"ℹ️ {col} አስቀድሞ አለ")
    
    conn.commit()
    conn.close()
    print("✅ ማሻሻያ ተጠናቋል!")

migrate()

from models import create_tables
import sqlite3

def add_missing_columns():
    conn = sqlite3.connect('parking.db')
    cursor = conn.cursor()

    # Add price_per_hour to parking_lots
    cursor.execute("PRAGMA table_info(parking_lots)")
    lot_columns = [col[1] for col in cursor.fetchall()]
    if 'price_per_hour' not in lot_columns:
        cursor.execute("ALTER TABLE parking_lots ADD COLUMN price_per_hour REAL DEFAULT 20.0")
        print("✅ Added column 'price_per_hour' to parking_lots")

    # Add cost to parking_history
    cursor.execute("PRAGMA table_info(parking_history)")
    history_columns = [col[1] for col in cursor.fetchall()]
    if 'cost' not in history_columns:
        cursor.execute("ALTER TABLE parking_history ADD COLUMN cost REAL")
        print("✅ Added column 'cost' to parking_history")

    conn.commit()
    conn.close()

def create_admin_if_not_exists():
    conn = sqlite3.connect('parking.db')
    cursor = conn.cursor()

    # Check if admin already exists
    cursor.execute("SELECT * FROM users WHERE email = 'admin@admin.com'")
    if cursor.fetchone() is None:
        cursor.execute('''
            INSERT INTO users (email, password, full_name, address, pin_code, role)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('admin@admin.com', 'admin123', 'Admin User', 'Admin Office', '000000', 'admin'))
        print("✅ Admin user created.")
    else:
        print("ℹ️ Admin already exists.")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_tables()
    create_admin_if_not_exists()
    add_missing_columns()  # ← you missed this call

    print("✅ Tables and schema upgraded successfully!")

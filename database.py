from models import create_tables
import sqlite3
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
    print("✅ Tables created successfully!")

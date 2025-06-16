import sqlite3

def create_tables():
    conn = sqlite3.connect('parking.db')
    c = conn.cursor()

    # Users Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            address TEXT,
            pin_code TEXT,
            role TEXT DEFAULT 'user'
        )
    ''')

    # Parking Lots Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS parking_lots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            address TEXT NOT NULL,
            pin_code TEXT,
            total_spots INTEGER NOT NULL,
            available_spots INTEGER NOT NULL
        )
    ''')

    # Parking Spots Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS parking_spots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lot_id INTEGER NOT NULL,
            spot_number TEXT NOT NULL,
            is_occupied INTEGER DEFAULT 0,
            current_user_id INTEGER,
            FOREIGN KEY(lot_id) REFERENCES parking_lots(id),
            FOREIGN KEY(current_user_id) REFERENCES users(id)
        )
    ''')

    # Reservations Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS reservations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            spot_id INTEGER NOT NULL,
            vehicle_number TEXT NOT NULL,
            booking_time TEXT NOT NULL,
            release_time TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(spot_id) REFERENCES parking_spots(id)
        )
    ''')

    # Parking History Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS parking_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            spot_id INTEGER NOT NULL,
            lot_id INTEGER NOT NULL,
            vehicle_number TEXT NOT NULL,
            entry_time TEXT NOT NULL,
            exit_time TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(spot_id) REFERENCES parking_spots(id),
            FOREIGN KEY(lot_id) REFERENCES parking_lots(id)
        )
    ''')

    conn.commit()
    conn.close()

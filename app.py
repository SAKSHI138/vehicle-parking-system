
from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os
from datetime import datetime
import random

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for sessions
DATABASE = 'parking.db'

# Helper function to get DB connection
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Home page
@app.route('/')
def home():
    return render_template('home.html')

# Register route (only for normal users)
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        full_name = request.form['full_name']
        address = request.form['address']
        pin_code = request.form['pin_code']
        role = 'user'  # Force role as 'user' for normal registrations

        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (email, password, full_name, address, pin_code, role) VALUES (?, ?, ?, ?, ?, ?)',
                         (email, password, full_name, address, pin_code, role))
            conn.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return "❌ Email already registered. Try logging in."
        finally:
            conn.close()

    return render_template('register.html')

# Login route for both user and admin
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute(
            'SELECT * FROM users WHERE email = ? AND password = ?',
            (email, password)
        ).fetchone()
        conn.close()

        if user:
            session['id'] = user['id']
            session['email'] = user['email']
            session['role'] = user['role']
            session['full_name'] = user['full_name']   # ✅ Important
            return redirect(url_for('user_dashboard') if user['role'] == 'user' else url_for('admin_dashboard'))
        else:
            return "❌ Invalid credentials"
    return render_template('login.html')


# Admin Dashboard (restricted)
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    lots = conn.execute('SELECT * FROM parking_lots').fetchall()
    conn.close()

    return render_template('admin_dashboard.html', lots=lots, full_name=session.get('full_name'))

@app.route('/create_lot', methods=['GET', 'POST'])
def create_lot():
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        pin_code = request.form['pin_code']
        total_spots = int(request.form['total_spots'])

        conn = get_db_connection()
        cursor = conn.cursor()

        # Insert the new lot
        cursor.execute('''
            INSERT INTO parking_lots (name, address, pin_code, total_spots, available_spots)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, address, pin_code, total_spots, total_spots))

        lot_id = cursor.lastrowid  # get ID of newly inserted lot

        # Auto-generate parking spots for this lot
        for i in range(1, total_spots + 1):
            spot_number = f"Spot-{i}"
            cursor.execute('''
                INSERT INTO parking_spots (lot_id, spot_number, is_occupied)
                VALUES (?, ?, 0)
            ''', (lot_id, spot_number))

        conn.commit()
        conn.close()

        return redirect(url_for('admin_dashboard'))

    return render_template('create_lot.html')


@app.route('/view_lots')
def view_lots():
    conn = get_db_connection()
    lots = conn.execute('SELECT * FROM parking_lots').fetchall()
    conn.close()
    return render_template('view_lots.html', lots=lots)


@app.route('/view_spots/<int:lot_id>')
def view_spots(lot_id):
    conn = get_db_connection()
    lot = conn.execute('SELECT * FROM parking_lots WHERE id = ?', (lot_id,)).fetchone()
    spots = conn.execute('''
        SELECT parking_spots.*, users.email as user_email 
        FROM parking_spots 
        LEFT JOIN users ON parking_spots.current_user_id = users.id
        WHERE lot_id = ?
    ''', (lot_id,)).fetchall()
    conn.close()
    return render_template('view_spots.html', lot=lot, spots=spots)

@app.route('/add_lot', methods=['GET', 'POST'])
def add_lot():
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        pin_code = request.form['pin_code']
        total_spots = int(request.form['total_spots'])

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO parking_lots (name, address, pin_code, total_spots, available_spots)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, address, pin_code, total_spots, total_spots))
        lot_id = cursor.lastrowid

        # Auto-create parking spots
        for i in range(1, total_spots + 1):
            spot_number = f"Spot-{i}"
            cursor.execute('''
                INSERT INTO parking_spots (lot_id, spot_number)
                VALUES (?, ?)
            ''', (lot_id, spot_number))

        conn.commit()
        conn.close()

        return redirect(url_for('view_lots'))

    return render_template('add_lot.html')

@app.route('/admin_users')
def admin_users():
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    users = conn.execute('SELECT * FROM users WHERE role = "user"').fetchall()

    # Fetch user and their parking spot (if any)
    user_spots = conn.execute('''
        SELECT u.id AS user_id, u.full_name, u.email, ps.spot_number, pl.name AS lot_name
        FROM users u
        LEFT JOIN parking_spots ps ON u.id = ps.current_user_id
        LEFT JOIN parking_lots pl ON ps.lot_id = pl.id
        WHERE u.role = "user"
    ''').fetchall()
    conn.close()
    print("Session:", session.get('user'))


    return render_template('admin_users.html', user_spots=user_spots)

@app.route('/admin/view_users')
def view_users():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    users = conn.execute('''
        SELECT u.full_name, u.email, ps.spot_number, pl.name as lot_name
        FROM users u
        LEFT JOIN parking_spots ps ON u.id = ps.current_user_id
        LEFT JOIN parking_lots pl ON ps.lot_id = pl.id
        WHERE u.role = 'user'
    ''').fetchall()
    conn.close()

    return render_template('view_users.html', users=users)


@app.route('/user_dashboard')
def user_dashboard():
    if 'id' not in session or session.get('role') != 'user':
        return redirect(url_for('login'))

    user_id = session['id']

    conn = get_db_connection()
    lots = conn.execute('''
    SELECT 
        lots.id,
        lots.name,
        lots.address,
        COUNT(spots.id) AS total_spots,
        SUM(CASE WHEN spots.is_occupied = 0 THEN 1 ELSE 0 END) AS available_spots
    FROM parking_lots AS lots
    LEFT JOIN parking_spots AS spots ON lots.id = spots.lot_id
    GROUP BY lots.id, lots.name, lots.address
    ''').fetchall()

    conn.close()

    # ✅ Pass full_name instead of 'user'
    return render_template('user_dashboard.html', lots=lots, full_name=session['full_name'])

@app.route('/edit_lot/<int:lot_id>', methods=['GET', 'POST'])
def edit_lot(lot_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    lot = conn.execute('SELECT * FROM parking_lots WHERE id = ?', (lot_id,)).fetchone()

    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        pin_code = request.form['pin_code']
        # ❗ Note: We do NOT update total_spots or available_spots to avoid data issues

        conn.execute('''
            UPDATE parking_lots 
            SET name = ?, address = ?, pin_code = ?
            WHERE id = ?
        ''', (name, address, pin_code, lot_id))
        conn.commit()
        conn.close()
        return redirect(url_for('view_lots'))

    conn.close()
    return render_template('edit_lot.html', lot=lot)


@app.route('/reserve/<int:lot_id>', methods=['POST'])
def reserve_spot(lot_id):
    if 'user' not in session or session['user']['role'] != 'user':
        return redirect(url_for('login'))

    user_id = session['user']['id']
    vehicle_number = f"AUTO-{user_id}"  # Or capture input if needed

    conn = get_db_connection()
    spot = conn.execute('''
        SELECT * FROM parking_spots 
        WHERE lot_id = ? AND is_occupied = 0
        LIMIT 1
    ''', (lot_id,)).fetchone()

    if spot:
        # Reserve it
        conn.execute('''
            UPDATE parking_spots 
            SET is_occupied = 1, current_user_id = ? 
            WHERE id = ?
        ''', (user_id, spot['id']))

        # Insert reservation
        from datetime import datetime
        now = datetime.now().isoformat()
        conn.execute('''
            INSERT INTO reservations (user_id, spot_id, vehicle_number, booking_time)
            VALUES (?, ?, ?, ?)
        ''', (user_id, spot['id'], vehicle_number, now))

        # Insert into parking history (entry)
        conn.execute('''
            INSERT INTO parking_history (user_id, spot_id, lot_id, vehicle_number, entry_time)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, spot['id'], lot_id, vehicle_number, now))

        # Decrease available_spots
        conn.execute('''
            UPDATE parking_lots SET available_spots = available_spots - 1 WHERE id = ?
        ''', (lot_id,))

        conn.commit()
        conn.close()
        return redirect(url_for('user_dashboard'))
    else:
        conn.close()
        return "❌ No available spots in this lot."
    
@app.route('/release', methods=['POST'])
def release_spot():
    if 'user' not in session or session['user']['role'] != 'user':
        return redirect(url_for('login'))

    user_id = session['user']['id']
    conn = get_db_connection()

    spot = conn.execute('SELECT * FROM parking_spots WHERE current_user_id = ?', (user_id,)).fetchone()
    if spot:
        now = datetime.now().isoformat()

        # Update spot
        conn.execute('''
            UPDATE parking_spots 
            SET is_occupied = 0, current_user_id = NULL 
            WHERE id = ?
        ''', (spot['id'],))

        # Update lot availability
        conn.execute('''
            UPDATE parking_lots 
            SET available_spots = available_spots + 1 
            WHERE id = ?
        ''', (spot['lot_id'],))

        # Update history exit time
        conn.execute('''
            UPDATE parking_history 
            SET exit_time = ? 
            WHERE user_id = ? AND spot_id = ? AND exit_time IS NULL
        ''', (now, user_id, spot['id']))

        conn.commit()
    conn.close()
    return redirect(url_for('user_dashboard'))

@app.route('/reserve/<int:lot_id>', methods=['POST'])
def reserve(lot_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    user_id = session['user']['id']
    vehicle_number = f"AUTO-{random.randint(1, 9999)}"

    conn = get_db_connection()

    # ✅ STEP 1: Check if the user already has a reserved spot
    active = conn.execute('''
        SELECT * FROM parking_spots
        WHERE current_user_id = ? AND is_occupied = 1
    ''', (user_id,)).fetchone()

    if active:
        conn.close()
        return "❌ You already have an active reservation. Please release it first."

    # ✅ STEP 2: Find a free spot in that lot
    spot = conn.execute('''
        SELECT * FROM parking_spots
        WHERE lot_id = ? AND is_occupied = 0
        LIMIT 1
    ''', (lot_id,)).fetchone()

    if not spot:
        conn.close()
        return "❌ No available spots in this lot."

    # ✅ STEP 3: Reserve the spot
    now = datetime.datetime.now()
    conn.execute('''
        UPDATE parking_spots
        SET is_occupied = 1, current_user_id = ?
        WHERE id = ?
    ''', (user_id, spot['id']))

    # ✅ STEP 4: Add entry in parking history
    conn.execute('''
        INSERT INTO parking_history (user_id, spot_id, vehicle_number, entry_time)
        VALUES (?, ?, ?, ?)
    ''', (user_id, spot['id'], vehicle_number, now))

    
    conn.commit()
    conn.close()
    print("Checking existing reservation for user:", user_id)
    print("Active reservation row:", active)

    return redirect(url_for('user_dashboard'))


@app.route('/user_history')
def user_history():
    if 'id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    history = conn.execute(
        '''
        SELECT r.*, p.name AS lot_name, p.address AS lot_address, s.spot_number
        FROM reservations r 
        JOIN parking_lots p ON r.lot_id = p.id 
        JOIN parking_spots s ON r.spot_id = s.id
        WHERE r.user_id = ? 
        ORDER BY r.booking_time DESC
        ''',
        (session['id'],)
    ).fetchall()
    conn.close()

    return render_template('user_history.html', history=history)

@app.route('/delete_lot/<int:lot_id>', methods=['POST'])
def delete_lot(lot_id):
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()

    # Delete spots first due to FK constraints
    conn.execute('DELETE FROM parking_spots WHERE lot_id = ?', (lot_id,))
    conn.execute('DELETE FROM parking_lots WHERE id = ?', (lot_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('view_lots'))

@app.route('/logout')
def logout():
    user_id = session.get('id')

    conn = get_db_connection()
    conn.execute('''
        UPDATE parking_spots
        SET is_occupied = 0, current_user_id = NULL
        WHERE current_user_id = ?
    ''', (user_id,))
    conn.commit()
    conn.close()

    session.clear()
    return redirect(url_for('home'))


# Run app
if __name__ == '__main__':
    app.run(debug=True)

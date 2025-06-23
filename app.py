from flask import Flask, render_template, request, redirect, url_for, session, flash, get_flashed_messages
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

@app.template_filter('datetimeformat')
def datetimeformat(value):
    if value:
        return datetime.fromisoformat(value).strftime('%d %b %Y, %I:%M %p')
    return ''


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
            session['user'] = {
                'id': user['id'],
                'email': user['email'],
                'full_name': user['full_name'],
                'role': user['role']
            }
            session['id'] = user['id']
            session['role'] = user['role']
            session['full_name'] = user['full_name']

            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            return render_template('login.html', error='❌ Invalid credentials')

    # ✅ Always return something here (for GET request)
    flash("❌ Invalid credentials, please try again.")
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

@app.route('/admin/reservations')
def admin_reservations():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))

    conn = get_db_connection()
    history = conn.execute('''
        SELECT 
            l.name AS lot_name,
            l.address AS lot_address,
            s.spot_number,
            h.vehicle_number,
            h.entry_time,
            h.exit_time,
            u.full_name AS user_name
        FROM parking_history h
        JOIN parking_spots s ON h.spot_id = s.id
        JOIN parking_lots l ON h.lot_id = l.id
        JOIN users u ON h.user_id = u.id
        ORDER BY h.entry_time DESC
    ''').fetchall()
    conn.close()

    # Convert and add duration
    converted_history = []
    for row in history:
        row_dict = dict(row)
        entry = row_dict['entry_time']
        exit = row_dict['exit_time']

        if entry and exit:
            duration = datetime.fromisoformat(exit) - datetime.fromisoformat(entry)
            row_dict['duration'] = str(duration)
        else:
            row_dict['duration'] = None

        converted_history.append(row_dict)

    return render_template('admin_reservations.html', history=converted_history)


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

    conn = get_db_connection()
    user_id = session['id']

    lots = [dict(row) for row in conn.execute('SELECT * FROM parking_lots').fetchall()]
    spot_row = conn.execute('SELECT * FROM parking_spots WHERE current_user_id = ?', (user_id,)).fetchone()
    spot = dict(spot_row) if spot_row else None

    current_lot = None
    if spot:
        lot_row = conn.execute('SELECT * FROM parking_lots WHERE id = ?', (spot['lot_id'],)).fetchone()
        current_lot = dict(lot_row) if lot_row else None

    full_name = conn.execute('SELECT full_name FROM users WHERE id = ?', (user_id,)).fetchone()['full_name']
    conn.close()

    return render_template('user_dashboard.html',
                           full_name=full_name,
                           lots=lots,
                           current_spot=spot,
                           current_lot=current_lot)



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
def reserve(lot_id):
    if 'user' not in session or session['user']['role'] != 'user':
        return redirect(url_for('login'))  # 👈 This is the part sending you to login

    user_id = session['user']['id']
    vehicle_number = f"AUTO-{random.randint(1000, 9999)}"

    conn = get_db_connection()

    # Check if user already has a reservation
    active = conn.execute('''
        SELECT * FROM parking_spots
        WHERE current_user_id = ? AND is_occupied = 1
    ''', (user_id,)).fetchone()

    if active:
        conn.close()
        return "❌ You already have an active reservation. Please release it first."

    # Find a free spot
    spot = conn.execute('''
        SELECT * FROM parking_spots
        WHERE lot_id = ? AND is_occupied = 0
        LIMIT 1
    ''', (lot_id,)).fetchone()

    if not spot:
        conn.close()
        return "❌ No available spots in this lot."

    # Reserve spot
    now = datetime.now().isoformat()
    conn.execute('''
        UPDATE parking_spots
        SET is_occupied = 1, current_user_id = ?
        WHERE id = ?
    ''', (user_id, spot['id']))

    # Add entry to parking history
    conn.execute('''
        INSERT INTO parking_history (user_id, spot_id, lot_id, vehicle_number, entry_time)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, spot['id'], lot_id, vehicle_number, now))

    # Decrease availability
    conn.execute('''
        UPDATE parking_lots
        SET available_spots = available_spots - 1
        WHERE id = ?
    ''', (lot_id,))

    # Insert into reservations table so history shows up
    conn.execute('''
        INSERT INTO reservations (user_id, spot_id, vehicle_number, booking_time)
        VALUES (?, ?, ?, ?)
    ''', (user_id, spot['id'], vehicle_number, now))

    conn.commit()
    conn.close()
    # After successful reservation
    flash("✅ Spot reserved successfully!")
    return redirect(url_for('user_dashboard'))


@app.route('/release', methods=['GET', 'POST'])
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

        # Update history
        conn.execute('''
            UPDATE parking_history 
            SET exit_time = ?
            WHERE user_id = ? AND spot_id = ? AND exit_time IS NULL
        ''', (now, user_id, spot['id']))

        conn.commit()
        flash("🔓 Spot released successfully!")

    conn.close()
    return redirect(url_for('user_dashboard'))

@app.route('/user_history')
def user_history():
    if 'id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    raw_history = conn.execute(
        '''
        SELECT r.*, l.name AS lot_name, l.address AS lot_address, s.spot_number
        FROM parking_history r
        JOIN parking_spots s ON r.spot_id = s.id
        JOIN parking_lots l ON r.lot_id = l.id
        WHERE r.user_id = ?
        ORDER BY r.entry_time DESC
        ''',
        (session['id'],)
    ).fetchall()
    conn.close()

    history = []
    for row in raw_history:
        entry = dict(row)

        # Convert times
        entry_time = datetime.fromisoformat(entry['entry_time'])
        entry['pretty_entry'] = entry_time.strftime('%d %b %Y, %I:%M %p')

        if entry['exit_time']:
            exit_time = datetime.fromisoformat(entry['exit_time'])
            entry['pretty_exit'] = exit_time.strftime('%d %b %Y, %I:%M %p')
            duration = exit_time - entry_time
            entry['duration'] = str(duration)
        else:
            entry['pretty_exit'] = None
            entry['duration'] = None

        history.append(entry)

    return render_template('user_history.html', history=history)

@app.route('/delete_lot/<int:lot_id>', methods=['POST'])
def delete_lot(lot_id):
    print("Session role:", session.get('role'))  # 👈 debug
    if session.get('role') != 'admin':
        print("Access denied. Redirecting to login.")
        return redirect(url_for('login'))

    conn = get_db_connection()
    conn.execute('DELETE FROM parking_lots WHERE id = ?', (lot_id,))
    conn.commit()
    conn.close()
    print(f"Lot {lot_id} deleted successfully.")
    return redirect(url_for('view_lots'))

@app.route('/logout')
def logout():
    user_id = session.get('id')

    conn = get_db_connection()

    # Get the spot the user had (if any)
    spot = conn.execute('''
        SELECT * FROM parking_spots WHERE current_user_id = ?
    ''', (user_id,)).fetchone()

    if spot:
        # Set spot as unoccupied
        conn.execute('''
            UPDATE parking_spots
            SET is_occupied = 0, current_user_id = NULL
            WHERE current_user_id = ?
        ''', (user_id,))

        # Increment available_spots in that lot
        conn.execute('''
            UPDATE parking_lots
            SET available_spots = available_spots + 1
            WHERE id = ?
        ''', (spot['lot_id'],))

        # Optionally, close any open parking history too
        now = datetime.now().isoformat()
        conn.execute('''
            UPDATE parking_history
            SET exit_time = ?
            WHERE user_id = ? AND spot_id = ? AND exit_time IS NULL
        ''', (now, user_id, spot['id']))

        conn.commit()

    conn.close()
    session.clear()
    return redirect(url_for('home'))

# Run app
if __name__ == '__main__':
    app.run(debug=True)

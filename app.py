
from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
import os

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
            session['user'] = {
                'id': user['id'],
                'email': user['email'],
                'full_name': user['full_name'],
                'role': user['role']
            }

            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))

        else:
            return '❌ Invalid login credentials.'

    return render_template('login.html')


# Admin Dashboard (restricted)
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'user' not in session or session['user']['role'] != 'admin':
        return redirect(url_for('login'))
    return render_template('admin_dashboard.html', user=session['user'])


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
        SELECT u.*, ps.spot_number, pl.name as lot_name
        FROM users u
        LEFT JOIN parking_spots ps ON u.id = ps.current_user_id
        LEFT JOIN parking_lots pl ON ps.lot_id = pl.id
        WHERE u.role = 'user'
    ''').fetchall()
    conn.close()
    return render_template('view_users.html', users=users)

# User Dashboard (restricted)
@app.route('/user_dashboard')
def user_dashboard():
    if session.get('role') != 'user':
        return redirect(url_for('login'))
    return f"Welcome User, {session.get('user_name')}!"

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# Run app
if __name__ == '__main__':
    app.run(debug=True)

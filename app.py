import mysql.connector
from flask import (
    Flask, request, jsonify, render_template, send_from_directory,
    redirect, url_for, flash, session, abort, make_response
)
from datetime import date
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user, login_required, current_user
)
from flask_bcrypt import Bcrypt
from functools import wraps
from dotenv import load_dotenv
import os
import io  # <-- NEW IMPORT
import csv # <-- NEW IMPORT

load_dotenv() 

# --- App & Database Setup ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

DB_CONFIG = {
    'host': os.environ.get('DB_HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASS'),
    'database': os.environ.get('DB_NAME')
}

# --- Initialize Extensions ---
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'error'

# --- Admin-Only Decorator ---
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash("You do not have permission to access this page.", "error")
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

# --- User Class (Unchanged) ---
class User(UserMixin):
    def __init__(self, id, username, role):
        self.id = id; self.username = username; self.role = role

@login_manager.user_loader
def load_user(user_id):
    conn = None; cursor = None
    try:
        conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM Users WHERE id = %s", (user_id,))
        user_data = cursor.fetchone()
        if user_data:
            return User(id=user_data['id'], username=user_data['username'], role=user_data['role'])
        return None
    except Exception as e:
        print(f"Error loading user: {e}"); return None
    finally:
        if cursor: cursor.close();
        if conn: conn.close()

# --- Database Functions (Unchanged) ---
def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as e:
        print(f"Error connecting to MySQL: {e}"); return None

def init_db():
    conn = None; cursor = None
    try:
        conn = get_db_connection();
        if conn is None: return
        cursor = conn.cursor()
        # BatteryStock Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS BatteryStock (
            id INT AUTO_INCREMENT PRIMARY KEY,
            barcode VARCHAR(255) NOT NULL UNIQUE,
            model VARCHAR(255),
            mfg_date VARCHAR(255),
            status VARCHAR(50) NOT NULL,
            activation_date DATE NULL
        )
        ''')
        # Users Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(100) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            role ENUM('admin', 'executive') NOT NULL
        );
        ''')
        # Create default users
        cursor.execute("SELECT COUNT(*) FROM Users")
        if cursor.fetchone()[0] == 0:
            print("No users found. Creating default users...")
            hashed_password_admin = bcrypt.generate_password_hash('admin').decode('utf-8')
            cursor.execute("INSERT INTO Users (username, password_hash, role) VALUES (%s, %s, %s)",
                           ('admin', hashed_password_admin, 'admin'))
            
            hashed_password_exec = bcrypt.generate_password_hash('12345678').decode('utf-8')
            cursor.execute("INSERT INTO Users (username, password_hash, role) VALUES (%s, %s, %s)",
                           ('abhisheka', hashed_password_exec, 'executive'))
            
            conn.commit()
            print("Default 'admin' and 'abhisheka' users created.")
        print("Database tables initialized successfully.")
    except mysql.connector.Error as e:
        print(f"Error initializing table: {e}")
    finally:
        if cursor: cursor.close();
        if conn: conn.close()

def decode_barcode(barcode):
    # (Unchanged)
    try:
        if '-' in barcode and len(barcode.split('-')) == 3:
            parts = barcode.split('-')
            model = parts[0]; mfg_date = parts[1]
        else:
            model = 'Unknown'; mfg_date = None
        return model, mfg_date
    except Exception as e:
        print(f"Error decoding barcode {barcode}: {e}"); return 'Error', None

# --- Authentication Routes (Unchanged) ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form.get('username'); password = request.form.get('password')
        conn = None; cursor = None
        try:
            conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM Users WHERE username = %s", (username,))
            user_data = cursor.fetchone()
            if user_data and bcrypt.check_password_hash(user_data['password_hash'], password):
                user_obj = User(id=user_data['id'], username=user_data['username'], role=user_data['role'])
                login_user(user_obj); session['role'] = user_data['role']
                return redirect(url_for('home'))
            else:
                flash('Invalid username or password', 'error')
                return redirect(url_for('login'))
        except Exception as e:
            flash(f"An error occurred: {e}", 'error'); return redirect(url_for('login'))
        finally:
            if cursor: cursor.close();
            if conn: conn.close()
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user(); session.pop('role', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

# --- Frontend Pages ---
@app.route('/home')
@login_required
def home():
    return render_template('index.html')

@app.route('/stock-view')
@login_required # <-- BUG FIX: Removed @admin_required
def stock_view_page():
    return render_template('stock-view.html')

@app.route('/stock-out')
@login_required
def stock_out_page():
    return render_template('stock-out.html')

@app.route('/summary')
@login_required # <-- BUG FIX: Removed @admin_required
def summary_page():
    return render_template('stock-summary.html')

@app.route('/admin-users')
@login_required
@admin_required # <-- Only admins
def admin_users_page():
    return render_template('admin_users.html')

# --- API Endpoints ---

@app.route('/api/get-stock')
@login_required # <-- BUG FIX: Removed @admin_required
def get_stock():
    conn = None; cursor = None
    try:
        conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT barcode, model, mfg_date, status, activation_date FROM BatteryStock WHERE status = 'In Stock' ORDER BY id DESC")
        return jsonify(cursor.fetchall()), 200
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor: cursor.close();
        if conn: conn.close()

@app.route('/api/get-activated')
@login_required # <-- BUG FIX: Removed @admin_required
def get_activated_stock():
    conn = None; cursor = None
    try:
        selected_date = request.args.get('date')
        conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
        query = "SELECT barcode, model, mfg_date, status, activation_date FROM BatteryStock WHERE status = 'Activated'"
        params = []
        if selected_date:
            query += " AND activation_date = %s"; params.append(selected_date)
        query += " ORDER BY id DESC"
        cursor.execute(query, params)
        return jsonify(cursor.fetchall()), 200
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor: cursor.close();
        if conn: conn.close()

@app.route('/api/get-stock-summary')
@login_required # <-- BUG FIX: Removed @admin_required
def get_stock_summary():
    conn = None; cursor = None
    try:
        conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
        query = "SELECT model, COUNT(*) as battery_count FROM BatteryStock WHERE status = 'In Stock' GROUP BY model ORDER BY model"
        cursor.execute(query)
        return jsonify(cursor.fetchall()), 200
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor: cursor.close();
        if conn: conn.close()

@app.route('/api/stock-in', methods=['POST'])
@login_required
def stock_in():
    # (Unchanged)
    conn = None; cursor = None
    try:
        data = request.get_json(); barcodes = data.get('barcodes', [])
        if not barcodes: return jsonify({"status": "error", "message": "No barcodes provided"}), 400
        conn = get_db_connection(); cursor = conn.cursor()
        added_count = 0
        for code in barcodes:
            try:
                model, mfg_date = decode_barcode(code)
                query = "INSERT IGNORE INTO BatteryStock (barcode, model, mfg_date, status) VALUES (%s, %s, %s, %s)"
                values = (code, model, mfg_date, 'In Stock')
                cursor.execute(query, values); added_count += cursor.rowcount
            except mysql.connector.Error as e: print(f"Error inserting {code}: {e}")
        conn.commit()
        return jsonify({"status": "success", "message": f"Received {len(barcodes)} barcodes. Added {added_count} new batteries to stock."}), 201
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor: cursor.close();
        if conn: conn.close()

@app.route('/api/stock-out', methods=['POST'])
@login_required
def stock_out():
    # (Unchanged)
    conn = None; cursor = None
    try:
        data = request.get_json(); barcode = data.get('barcode')
        if not barcode: return jsonify({"status": "error", "message": "No barcode provided"}), 400
        conn = get_db_connection(); cursor = conn.cursor()
        today = date.today()
        query = "UPDATE BatteryStock SET status = 'Activated', activation_date = %s WHERE barcode = %s"
        cursor.execute(query, (today, barcode))
        if cursor.rowcount == 0: return jsonify({"status": "error", "message": f"Barcode not found: {barcode}"}), 404
        conn.commit()
        return jsonify({"status": "success", "message": f"Battery {barcode} has been activated."}), 200
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor: cursor.close();
        if conn: conn.close()

# --- Admin API Routes ---
# (Unchanged /api/admin/users, add, delete, update-password)

@app.route('/api/admin/users', methods=['GET'])
@login_required
@admin_required
def get_users():
    conn = None; cursor = None
    try:
        conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, username, role FROM Users ORDER BY username")
        return jsonify(cursor.fetchall()), 200
    except Exception as e: return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        if cursor: cursor.close();
        if conn: conn.close()

@app.route('/api/admin/users/add', methods=['POST'])
@login_required
@admin_required
def add_user():
    conn = None; cursor = None
    try:
        data = request.get_json()
        username = data.get('username'); password = data.get('password'); role = data.get('role')
        if not username or not password or not role:
            return jsonify({"message": "All fields are required"}), 400
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("INSERT INTO Users (username, password_hash, role) VALUES (%s, %s, %s)",
                       (username, hashed_password, role))
        conn.commit()
        return jsonify({"message": "User created successfully"}), 201
    except mysql.connector.Error as e:
        if e.errno == 1062: return jsonify({"message": "Username already exists"}), 409
        return jsonify({"message": str(e)}), 500
    finally:
        if cursor: cursor.close();
        if conn: conn.close()

@app.route('/api/admin/users/delete', methods=['POST'])
@login_required
@admin_required
def delete_user():
    conn = None; cursor = None
    try:
        data = request.get_json(); user_id = data.get('id')
        if int(user_id) == current_user.id:
            return jsonify({"message": "You cannot delete your own account."}), 403
        conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT username FROM Users WHERE id = %s", (user_id,))
        user_to_delete = cursor.fetchone()
        if user_to_delete and user_to_delete['username'] == 'admin':
            return jsonify({"message": "The default 'admin' user cannot be deleted."}), 403
        cursor.execute("DELETE FROM Users WHERE id = %s", (user_id,))
        conn.commit()
        if cursor.rowcount == 0: return jsonify({"message": "User not found"}), 404
        return jsonify({"message": "User deleted successfully"}), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500
    finally:
        if cursor: cursor.close();
        if conn: conn.close()

@app.route('/api/admin/users/update-password', methods=['POST'])
@login_required
@admin_required
def update_password():
    conn = None; cursor = None
    try:
        data = request.get_json()
        user_id = data.get('user_id'); new_password = data.get('password')
        if not user_id or not new_password:
            return jsonify({"message": "User ID and new password are required."}), 400
        conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT username FROM Users WHERE id = %s", (user_id,))
        user_to_edit = cursor.fetchone()
        if not user_to_edit:
            return jsonify({"message": "User not found."}), 404
        if user_to_edit['username'] == 'admin' and current_user.username != 'admin':
            return jsonify({"message": "Only the 'admin' user can change their own password."}), 403
        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        cursor.execute("UPDATE Users SET password_hash = %s WHERE id = %s", (hashed_password, user_id))
        conn.commit()
        return jsonify({"message": "Password updated successfully."}), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500
    finally:
        if cursor: cursor.close();
        if conn: conn.close()

# --- NEW: Download Report API ---
@app.route('/api/admin/download-report')
@login_required
@admin_required
def download_report():
    conn = None; cursor = None
    try:
        status = request.args.get('status') # 'In Stock' or 'Activated'
        selected_date = request.args.get('date') # e.g., '2025-11-11'

        conn = get_db_connection(); cursor = conn.cursor(dictionary=True)
        
        headers = ['barcode', 'model', 'mfg_date', 'status', 'activation_date']
        
        if status == 'In Stock':
            query = "SELECT barcode, model, mfg_date, status, activation_date FROM BatteryStock WHERE status = 'In Stock' ORDER BY id DESC"
            params = []
        elif status == 'Activated':
            query = "SELECT barcode, model, mfg_date, status, activation_date FROM BatteryStock WHERE status = 'Activated'"
            params = []
            if selected_date:
                query += " AND activation_date = %s"
                params.append(selected_date)
            query += " ORDER BY id DESC"
        else:
            return "Invalid report status", 400
            
        cursor.execute(query, params)
        data = cursor.fetchall()

        # Create CSV in memory
        si = io.StringIO()
        cw = csv.writer(si)
        cw.writerow(headers) # Write header
        
        for row in data:
            cw.writerow([
                row.get('barcode', ''),
                row.get('model', ''),
                row.get('mfg_date', ''),
                row.get('status', ''),
                row.get('activation_date', '') # Will be 'None' for In Stock
            ])
        
        output = si.getvalue()
        
        # Create response
        response = make_response(output)
        filename = f"report_{status.lower().replace(' ','_')}_{date.today()}.csv"
        response.headers["Content-Disposition"] = f"attachment; filename={filename}"
        response.headers["Content-Type"] = "text/csv"
        return response

    except Exception as e:
        return f"An error occurred: {str(e)}", 500
    finally:
        if cursor: cursor.close();
        if conn: conn.close()

# --- Static File Route (Unchanged) ---
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

# --- Run the App (Unchanged) ---
if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
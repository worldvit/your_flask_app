import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql.cursors
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# --- GENERATE FLASK_SECRET_KEY ---
# This part is for generating the key. You would run this once, get the key,
# and then put it into your .env file.
# For demonstration, I'm generating it here, but in a real scenario,
# you'd run this in your Python interpreter:
# import os
# print(os.urandom(24).hex())
# Then copy the output to your .env file.
# For this example, we'll assume it's already in the .env file.
flask_secret_key = os.getenv('FLASK_SECRET_KEY')
if not flask_secret_key:
    # If not found in .env, generate one for the running instance (NOT for production persistence)
    # In a real setup, ensure this is set in .env before deployment.
    flask_secret_key = os.urandom(24).hex()
    print(f"WARNING: FLASK_SECRET_KEY not found in .env. Using newly generated key for this run: {flask_secret_key}")
    print("Please add 'FLASK_SECRET_KEY={}' to your .env file for persistent security.".format(flask_secret_key))

app.secret_key = flask_secret_key

# Database connection configuration using environment variables
DB_CONFIG = {
    'host': os.getenv('DB_HOST', '10.10.8.4'),
    'user': os.getenv('DB_USER', 'flask_user'),
    'password': os.getenv('DB_PASSWORD', 'P@ssw0rd'), # Directly using the specified password
    'db': os.getenv('DB_NAME', 'flask_auth_db'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db_connection():
    """Establishes and returns a database connection."""
    try:
        return pymysql.connect(**DB_CONFIG)
    except pymysql.Error as e:
        print(f"Error connecting to MariaDB: {e}")
        # In a real application, you might want to log this more formally
        # and display a user-friendly error page.
        flash('Database connection error. Please try again later.', 'error')
        raise

@app.route('/')
def index():
    """Renders the default authentication page."""
    return render_template('default.html')

@app.route('/register', methods=['POST'])
def register():
    """Handles user registration."""
    username = request.form['username'].strip()
    password = request.form['password'].strip()

    if not username or not password:
        flash('Username and password cannot be empty.', 'error')
        return redirect(url_for('index'))

    # Hash the password for security
    hashed_password = generate_password_hash(password)

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            # Check if username already exists
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                flash('Username already exists. Please choose a different one.', 'error')
                return redirect(url_for('index'))

            # Insert new user into the database
            sql = "INSERT INTO users (username, password) VALUES (%s, %s)"
            cursor.execute(sql, (username, hashed_password))
        conn.commit() # Commit the transaction
        flash('Registration successful! You can now log in.', 'success')
    except Exception as e:
        print(f"Database error during registration: {e}")
        flash('Registration failed. Please try again later.', 'error')
    finally:
        if conn:
            conn.close()
    return redirect(url_for('index'))

@app.route('/login', methods=['POST'])
def login():
    """Handles user login."""
    username = request.form['username'].strip()
    password = request.form['password'].strip()

    if not username or not password:
        flash('Please enter both username and password.', 'error')
        return redirect(url_for('index'))

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            sql = "SELECT id, username, password FROM users WHERE username = %s"
            cursor.execute(sql, (username,))
            user = cursor.fetchone()

            # Verify password
            if user and check_password_hash(user['password'], password):
                # User authenticated successfully, store session data
                session['loggedin'] = True
                session['id'] = user['id']
                session['username'] = user['username']
                flash(f'Welcome back, {user["username"]}!', 'success')
                return redirect(url_for('dashboard')) # Redirect to a protected page
            else:
                flash('Incorrect username or password. Please try again.', 'error')
    except Exception as e:
        print(f"Database error during login: {e}")
        flash('Login failed due to a server error. Please try again later.', 'error')
    finally:
        if conn:
            conn.close()
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    """A protected page accessible only to logged-in users."""
    if 'loggedin' in session:
        return render_template('dashboard.html', username=session['username'])
    flash('Please log in to access this page.', 'error')
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    """Logs out the current user."""
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    flash('You have been successfully logged out.', 'success')
    return redirect(url_for('index'))

# This block is for development use (running `python app.py`).
# It will not be used when deployed with Apache/mod_wsgi.
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0') # Run on all available interfaces for testing

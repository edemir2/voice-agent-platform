from flask import Flask, render_template, request, redirect, url_for, flash
import psycopg2
import hashlib
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Required for flash messages

# Database connection settings
DB_HOST = "localhost"
DB_NAME = "deneme_v1"  # Update this to your actual database name
DB_USER = "postgres"  # Update this to your actual username
DB_PASS = "test"  # Update this to your actual password

def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASS
    )

def hash_password(password):
    """Hash a password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_demo_table():
    """Create the demo table if it doesn't exist"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS demo (
            id SERIAL PRIMARY KEY,
            full_name VARCHAR(100) NOT NULL,
            business_name VARCHAR(150) NOT NULL,
            business_type VARCHAR(100) NOT NULL CHECK (business_type IN ('Retail Store', 'Restaurant/Cafe', 'Service Business', 'Healthcare', 'Real Estate', 'Other')),
            phone_number VARCHAR(20),
            email VARCHAR(100) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    cur.close()
    conn.close()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            email = request.form['email']
            password = request.form['password']
            
            # Validate required fields
            if not email or not password:
                return render_template('login.html', error_message="Email and password are required.")
            
            # Hash the password for comparison
            password_hash = hash_password(password)
            
            # Connect to database and check credentials
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Check if user exists with the provided email and password
            cur.execute("SELECT id, full_name, business_name FROM demo WHERE email = %s AND password_hash = %s", 
                       (email, password_hash))
            user = cur.fetchone()
            
            cur.close()
            conn.close()
            
            if user:
                # User found - redirect to success page
                return redirect(url_for('success'))
            else:
                # User not found or wrong credentials
                return render_template('login.html', error_message="Invalid email or password. Please try again.")
                
        except Exception as e:
            return render_template('login.html', error_message=f"An error occurred: {str(e)}")
    
    return render_template('login.html')

@app.route('/success')
def success():
    return render_template('success.html')

@app.route('/join', methods=['GET', 'POST'])
def join():
    if request.method == 'POST':
        try:
            # Get form data
            full_name = request.form['full_name']
            business_name = request.form['business_name']
            business_type = request.form['business_type']
            phone_number = request.form['phone_number']
            email = request.form['email']
            password = request.form['password']
            
            # Validate required fields
            if not all([full_name, business_name, business_type, email, password]):
                return render_template('join.html', error_message="All required fields must be filled.")
            
            # Hash the password
            password_hash = hash_password(password)
            
            # Connect to database and insert data
            conn = get_db_connection()
            cur = conn.cursor()
            
            # Check if email already exists
            cur.execute("SELECT id FROM demo WHERE email = %s", (email,))
            if cur.fetchone():
                cur.close()
                conn.close()
                return render_template('join.html', error_message="Email address already registered.")
            
            # Insert new demo request
            cur.execute("""
                INSERT INTO demo (full_name, business_name, business_type, phone_number, email, password_hash)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (full_name, business_name, business_type, phone_number, email, password_hash))
            
            conn.commit()
            cur.close()
            conn.close()
            
            # Redirect to login page after successful submission
            return redirect(url_for('login'))
            
        except Exception as e:
            return render_template('join.html', error_message=f"An error occurred: {str(e)}")
    
    return render_template('join.html')

@app.route('/forgot_password')
def forgot_password():
    return render_template('forgot_password.html')

if __name__ == '__main__':
    # Create the demo table when the app starts
    create_demo_table()
    app.run(debug=True)

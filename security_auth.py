"""
Comprehensive Security and Authentication Module
Includes: Login, Register, Forgot Password, Encryption, User Profile
"""

import streamlit as st
import mysql.connector
from mysql.connector import Error
import hashlib
import secrets
import string
from datetime import datetime, timedelta
import re
import os
import json
from cryptography.fernet import Fernet
import base64
import platform

# ==================== DATABASE CONFIGURATION ====================
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'Yuvraj@365',
    'database': 'eda_app_user_db'
}

# ==================== PASSCODE CONFIGURATION ====================
MASTER_PASSCODE = "123456"  # Master passcode for registration
ADMIN_PASSCODE = "123456"  # Passcode required for admin login

# ==================== ADMIN CONFIGURATION ====================
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"


# ==================== ENCRYPTION SETUP ====================
def get_encryption_key():
    """Generate or retrieve encryption key for user data"""
    # First, try to get key from environment variable (most reliable)
    env_key = os.environ.get('ENCRYPTION_KEY')
    if env_key:
        try:
            key = env_key.encode() if isinstance(env_key, str) else env_key
            Fernet(key)  # Validate key
            return key
        except:
            pass
    
    # Fall back to file-based key
    key_file = os.path.join(os.path.dirname(__file__), '.secret_key')
    
    if os.path.exists(key_file):
        try:
            with open(key_file, 'rb') as f:
                key = f.read()
                if key:
                    # Validate that it's a valid Fernet key
                    Fernet(key)
                    return key
        except Exception as e:
            pass
    
    # Generate new key if none exists
    key = Fernet.generate_key()
    try:
        with open(key_file, 'wb') as f:
            f.write(key)
        os.chmod(key_file, 0o600)  # Restrict access
        
        # Also save to environment variable for persistence
        os.environ['ENCRYPTION_KEY'] = key.decode() if isinstance(key, bytes) else key
    except Exception as e:
        pass
    
    return key


ENCRYPTION_KEY = get_encryption_key()
cipher = Fernet(ENCRYPTION_KEY)


def encrypt_data(data):
    """Encrypt sensitive user data"""
    if isinstance(data, str):
        data = data.encode()
    encrypted = cipher.encrypt(data)
    return encrypted.decode()


def decrypt_data(encrypted_data):
    """Decrypt sensitive user data"""
    if not encrypted_data:
        return None
    
    try:
        # Ensure the data is a string
        if isinstance(encrypted_data, bytes):
            encrypted_data = encrypted_data.decode('utf-8')
        
        decrypted = cipher.decrypt(encrypted_data.encode('utf-8'))
        return decrypted.decode('utf-8')
    except Exception as e:
        # If decryption fails with current key, the key might have changed
        # Return None silently to let the UI show N/A
        return None


# ==================== PASSWORD HASHING ====================
def hash_password(password):
    """Hash password with salt"""
    salt = secrets.token_hex(32)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}${hashed.hex()}"


def verify_password(password, hashed):
    """Verify password against hash"""
    try:
        salt, hash_val = hashed.split('$')
        new_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
        return new_hash == hash_val
    except:
        return False


# ==================== DATABASE OPERATIONS ====================
def migrate_users_table():
    """Migrate existing users table to have TEXT columns and add passcode column"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # Check if passcode column exists
        cursor.execute("""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'users' AND COLUMN_NAME = 'passcode'
        """, (DB_CONFIG['database'],))

        passcode_exists = cursor.fetchone()

        # If passcode doesn't exist, add it
        if not passcode_exists:
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN passcode TEXT AFTER email")
                connection.commit()
            except Exception as e:
                connection.rollback()

        # Check if is_restricted column exists
        cursor.execute("""
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'users' AND COLUMN_NAME = 'is_restricted'
        """, (DB_CONFIG['database'],))

        is_restricted_exists = cursor.fetchone()

        # If is_restricted doesn't exist, add it
        if not is_restricted_exists:
            try:
                cursor.execute("ALTER TABLE users ADD COLUMN is_restricted BOOLEAN DEFAULT FALSE AFTER is_active")
                connection.commit()
            except Exception as e:
                connection.rollback()

        # Check if users table has incorrect column types
        cursor.execute("""
            SELECT COLUMN_TYPE FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'users' AND COLUMN_NAME = 'role_position'
        """, (DB_CONFIG['database'],))

        result = cursor.fetchone()

        if result:
            column_type = result[0]
            # If column is VARCHAR, migrate to TEXT
            if 'varchar' in column_type.lower():
                try:
                    cursor.execute("ALTER TABLE users MODIFY COLUMN full_name TEXT NOT NULL")
                    cursor.execute("ALTER TABLE users MODIFY COLUMN role_position TEXT")
                    cursor.execute("ALTER TABLE users MODIFY COLUMN location TEXT")
                    connection.commit()
                except Exception as e:
                    connection.rollback()
                    # If migration fails, try dropping and recreating
                    try:
                        cursor.execute("DROP TABLE users")
                        cursor.execute("DROP TABLE IF EXISTS password_reset_tokens")
                        cursor.execute("DROP TABLE IF EXISTS login_history")
                        connection.commit()
                    except:
                        pass

        cursor.close()
        connection.close()
        return True
    except Exception as e:
        return False


def init_database():
    """
    Initialize database and create tables if they don't exist.

    ---
    Pre-written SQL queries for automatic table creation:

    USERS TABLE (for registration & login):
    CREATE TABLE IF NOT EXISTS users (
        user_id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        email VARCHAR(100) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        passcode TEXT,
        full_name TEXT NOT NULL,
        role_position TEXT,
        location TEXT,
        profile_picture LONGBLOB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        last_login TIMESTAMP,
        is_active BOOLEAN DEFAULT TRUE,
        is_restricted BOOLEAN DEFAULT FALSE,
        INDEX(username),
        INDEX(email)
    )

    PASSWORD RESET TOKENS TABLE (for forgot password):
    CREATE TABLE IF NOT EXISTS password_reset_tokens (
        token_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        reset_token VARCHAR(255) UNIQUE NOT NULL,
        token_expiry TIMESTAMP NOT NULL,
        is_used BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(user_id),
        INDEX(reset_token)
    )

    LOGIN HISTORY TABLE (for login tracking):
    CREATE TABLE IF NOT EXISTS login_history (
        login_id INT AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        device_info VARCHAR(255),
        ip_address VARCHAR(45),
        login_method VARCHAR(50),
        FOREIGN KEY(user_id) REFERENCES users(user_id),
        INDEX(user_id)
    )
    ---
    These queries are executed automatically on app startup.
    """
    try:
        # Connect to MySQL server
        connection = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        cursor = connection.cursor()

        # Create database
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_CONFIG['database']}")
        cursor.close()
        connection.close()

        # Connect to the database
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                passcode TEXT,
                full_name TEXT NOT NULL,
                role_position TEXT,
                location TEXT,
                profile_picture LONGBLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE,
                is_restricted BOOLEAN DEFAULT FALSE,
                INDEX(username),
                INDEX(email)
            )
        ''')

        # Run migration to fix existing tables with VARCHAR columns
        cursor.close()
        connection.close()
        migrate_users_table()

        # Reconnect to complete remaining operations
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        # Ensure all existing users have the master passcode set (encrypted)
        try:
            encrypted_master = encrypt_data(MASTER_PASSCODE)
            cursor.execute('UPDATE users SET passcode = %s', (encrypted_master,))
            connection.commit()
        except Exception:
            # If update fails (e.g., table doesn't exist yet), ignore and continue
            connection.rollback()

        # Create password reset tokens table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                token_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                reset_token VARCHAR(255) UNIQUE NOT NULL,
                token_expiry TIMESTAMP NOT NULL,
                is_used BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                INDEX(reset_token)
            )
        ''')

        # Create login history table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS login_history (
                login_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                device_info VARCHAR(255),
                ip_address VARCHAR(45),
                login_method VARCHAR(50),
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                INDEX(user_id)
            )
        ''')

        connection.commit()
        cursor.close()
        connection.close()
        return True, None
    except Error as e:
        # Do not call st.error here, just return the error message
        return False, str(e)


def get_db_connection():
    """Get database connection"""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        # Do not show error in UI, just return None
        return None


# ==================== USER REGISTRATION ====================
def register_user(username, email, password, confirm_password, full_name, role_position, location, passcode):
    """Register a new user"""
    errors = []

    # Validation
    if len(username) < 3:
        errors.append("Username must be at least 3 characters long")

    if not re.match(r'^[a-zA-Z0-9._+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        errors.append("Invalid email format")

    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")

    if password != confirm_password:
        errors.append("Passwords do not match")

    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")

    if not re.search(r'[0-9]', password):
        errors.append("Password must contain at least one digit")

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Password must contain at least one special character")

    # Passcode validation
    if passcode != MASTER_PASSCODE:
        errors.append("Invalid passcode")

    if errors:
        return False, errors

    try:
        connection = get_db_connection()
        if not connection:
            # Silently fail or return a generic error, but do not show DB error
            return False, ["Registration is temporarily unavailable. Please try again later."]

        cursor = connection.cursor()

        # Check if user exists
        cursor.execute("SELECT username FROM users WHERE username = %s OR email = %s",
                       (username, email))
        if cursor.fetchone():
            cursor.close()
            connection.close()
            return False, ["Username or email already exists"]

        # Hash password
        password_hash = hash_password(password)

        # Store passcode encrypted (6-digit code used for verification)
        encrypted_passcode = encrypt_data(passcode)

        # Insert user
        cursor.execute('''
            INSERT INTO users (username, email, password_hash, passcode, full_name, role_position, location)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (username, email, password_hash, encrypted_passcode, encrypt_data(full_name),
              encrypt_data(role_position), encrypt_data(location)))

        connection.commit()
        cursor.close()
        connection.close()

        return True, ["User registered successfully!"]

    except Error as e:
        return False, [f"Registration error: {str(e)}"]


# ==================== USER LOGIN ====================
def login_user(username, password, passcode):
    """Authenticate user with username/password/passcode"""
    try:
        connection = get_db_connection()
        if not connection:
            return False, None, "Database connection failed"

        cursor = connection.cursor(dictionary=True)

        # Get user
        cursor.execute('''
            SELECT user_id, username, password_hash, is_active, is_restricted, passcode
            FROM users WHERE username = %s
        ''', (username,))

        user = cursor.fetchone()

        if not user:
            cursor.close()
            connection.close()
            return False, None, "Invalid username or password"

        if not user['is_active']:
            cursor.close()
            connection.close()
            return False, None, "Account is inactive"

        # Check if user is restricted by admin
        if user.get('is_restricted', False):
            cursor.close()
            connection.close()
            return False, None, "Your account has been restricted by admin. Please contact administrator."

        # Check password
        if not verify_password(password, user['password_hash']):
            cursor.close()
            connection.close()
            return False, None, "Invalid username or password"

        # Verify passcode: accept encrypted or plaintext stored values
        stored_passcode = user.get('passcode')
        if not stored_passcode:
            cursor.close()
            connection.close()
            return False, None, "Invalid passcode"

        # Try to decrypt stored passcode if it's encrypted (Fernet produces strings like 'gAAAA...')
        decrypted_passcode = decrypt_data(stored_passcode)
        compare_passcode = decrypted_passcode if decrypted_passcode is not None else stored_passcode

        if compare_passcode != passcode:
            cursor.close()
            connection.close()
            return False, None, "Invalid passcode"

        # Update last login
        cursor.execute('''
            UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = %s
        ''', (user['user_id'],))

        # Log login
        cursor.execute('''
            INSERT INTO login_history (user_id, device_info, login_method)
            VALUES (%s, %s, %s)
        ''', (user['user_id'], platform.platform(), 'password'))

        connection.commit()
        cursor.close()
        connection.close()

        return True, user['user_id'], "Login successful"

    except Error as e:
        return False, None, f"Login error: {str(e)}"


# ==================== USER PROFILE ====================
def get_user_profile(user_id):
    """Get user profile information"""
    try:
        connection = get_db_connection()
        if not connection:
            return None

        cursor = connection.cursor(dictionary=True)

        cursor.execute('''
            SELECT user_id, username, email, full_name, role_position, location, 
                   created_at, last_login
            FROM users WHERE user_id = %s
        ''', (user_id,))

        user = cursor.fetchone()
        cursor.close()
        connection.close()

        if user:
            # Decrypt sensitive data with fallback to N/A if decryption fails
            user['full_name'] = decrypt_data(user['full_name']) or 'N/A'
            user['role_position'] = decrypt_data(user['role_position']) or 'N/A'
            user['location'] = decrypt_data(user['location']) or 'N/A'
            return user

        return None

    except Error as e:
        return None


def update_user_profile(user_id, full_name, role_position, location):
    """Update user profile information"""
    try:
        connection = get_db_connection()
        if not connection:
            return False, "Database connection failed"

        cursor = connection.cursor()

        cursor.execute('''
            UPDATE users 
            SET full_name = %s, role_position = %s, location = %s
            WHERE user_id = %s
        ''', (encrypt_data(full_name), encrypt_data(role_position),
              encrypt_data(location), user_id))

        connection.commit()
        cursor.close()
        connection.close()

        return True, "Profile updated successfully"

    except Error as e:
        return False, f"Update error: {str(e)}"


# ==================== PASSWORD RESET ====================
def request_password_reset(email):
    """Generate password reset token"""
    try:
        connection = get_db_connection()
        if not connection:
            return False, "Database connection failed", None

        cursor = connection.cursor(dictionary=True)

        # Find user by email
        cursor.execute('SELECT user_id FROM users WHERE email = %s', (email,))
        user = cursor.fetchone()

        if not user:
            cursor.close()
            connection.close()
            return False, "Email not found", None

        # Generate reset token
        reset_token = secrets.token_urlsafe(32)
        token_expiry = datetime.now() + timedelta(hours=24)

        # Store reset token
        cursor.execute('''
            INSERT INTO password_reset_tokens (user_id, reset_token, token_expiry)
            VALUES (%s, %s, %s)
        ''', (user['user_id'], reset_token, token_expiry))

        connection.commit()
        cursor.close()
        connection.close()

        return True, "Password reset token generated", reset_token

    except Error as e:
        return False, f"Error: {str(e)}", None


def reset_password(reset_token, new_password, confirm_password):
    """Reset password with token"""
    errors = []

    # Validation
    if len(new_password) < 8:
        errors.append("Password must be at least 8 characters long")

    if new_password != confirm_password:
        errors.append("Passwords do not match")

    if not re.search(r'[A-Z]', new_password):
        errors.append("Password must contain at least one uppercase letter")

    if not re.search(r'[0-9]', new_password):
        errors.append("Password must contain at least one digit")

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password):
        errors.append("Password must contain at least one special character")

    if errors:
        return False, errors

    try:
        connection = get_db_connection()
        if not connection:
            return False, ["Database connection failed"]

        cursor = connection.cursor(dictionary=True)

        # Find valid token
        cursor.execute('''
            SELECT user_id FROM password_reset_tokens 
            WHERE reset_token = %s AND is_used = FALSE AND token_expiry > NOW()
        ''', (reset_token,))

        token = cursor.fetchone()

        if not token:
            cursor.close()
            connection.close()
            return False, ["Invalid or expired token"]

        # Update password
        password_hash = hash_password(new_password)
        cursor.execute('UPDATE users SET password_hash = %s WHERE user_id = %s',
                       (password_hash, token['user_id']))

        # Mark token as used
        cursor.execute('UPDATE password_reset_tokens SET is_used = TRUE WHERE reset_token = %s',
                       (reset_token,))

        connection.commit()
        cursor.close()
        connection.close()

        return True, ["Password reset successfully!"]

    except Error as e:
        return False, [f"Reset error: {str(e)}"]


# ==================== ADMIN FUNCTIONS ====================
def admin_login(admin_passcode):
    """Authenticate admin user"""
    try:
        # Verify admin passcode
        if admin_passcode != ADMIN_PASSCODE:
            return False, "Invalid passcode"

        # Admin authentication successful
        return True, "Admin login successful"
    except Exception as e:
        return False, f"Admin login error: {str(e)}"


def get_all_users():
    """Get all registered users (admin function)"""
    try:
        connection = get_db_connection()
        if not connection:
            return []

        cursor = connection.cursor(dictionary=True)

        cursor.execute('''
            SELECT user_id, username, email, full_name, role_position, location, 
                   created_at, last_login, is_active, is_restricted
            FROM users
            ORDER BY created_at DESC
        ''')

        users = cursor.fetchall()
        cursor.close()
        connection.close()

        # Decrypt sensitive data
        for user in users:
            user['full_name'] = decrypt_data(user['full_name']) or 'N/A' if user['full_name'] else 'N/A'
            user['role_position'] = decrypt_data(user['role_position']) or 'N/A' if user['role_position'] else 'N/A'
            user['location'] = decrypt_data(user['location']) or 'N/A' if user['location'] else 'N/A'

        return users

    except Error as e:
        # Do not show DB error in UI, just return empty list
        return []


def restrict_user(user_id, restrict=True):
    """Restrict or unrestrict user access"""
    try:
        connection = get_db_connection()
        if not connection:
            return False, "Database connection failed"

        cursor = connection.cursor()

        cursor.execute('''
            UPDATE users SET is_restricted = %s WHERE user_id = %s
        ''', (restrict, user_id))

        connection.commit()
        cursor.close()
        connection.close()

        action = "restricted" if restrict else "unrestricted"
        return True, f"User {action} successfully"

    except Error as e:
        return False, f"Error: {str(e)}"


def delete_user_completely(user_id):
    """Completely delete user and all their data from system"""
    try:
        connection = get_db_connection()
        if not connection:
            return False, "Database connection failed"

        cursor = connection.cursor()

        # Delete user's password reset tokens
        cursor.execute('DELETE FROM password_reset_tokens WHERE user_id = %s', (user_id,))

        # Delete user's login history
        cursor.execute('DELETE FROM login_history WHERE user_id = %s', (user_id,))

        # Delete user from users table
        cursor.execute('DELETE FROM users WHERE user_id = %s', (user_id,))

        connection.commit()
        cursor.close()
        connection.close()

        return True, "User deleted completely from system"

    except Error as e:
        return False, f"Error: {str(e)}"


def export_users_csv():
    """Export all users to CSV data string"""
    users = get_all_users()
    if not users:
        return None

    from io import StringIO
    import csv

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        'user_id', 'username', 'email', 'full_name', 'role_position', 'location',
        'created_at', 'last_login', 'is_active', 'is_restricted'
    ])
    writer.writeheader()
    for u in users:
        writer.writerow({
            'user_id': u.get('user_id'),
            'username': u.get('username'),
            'email': u.get('email'),
            'full_name': u.get('full_name'),
            'role_position': u.get('role_position'),
            'location': u.get('location'),
            'created_at': u.get('created_at').strftime("%Y-%m-%d %H:%M:%S") if u.get('created_at') else '',
            'last_login': u.get('last_login').strftime("%Y-%m-%d %H:%M:%S") if u.get('last_login') else '',
            'is_active': u.get('is_active'),
            'is_restricted': u.get('is_restricted')
        })

    return output.getvalue()


def import_users_csv(uploaded_file):
    """Import users from CSV file for admin"""
    try:
        import csv
        from io import StringIO

        text = uploaded_file.getvalue().decode('utf-8')
        reader = csv.DictReader(StringIO(text))

        inserted = 0
        errors = []
        connection = get_db_connection()
        if not connection:
            return False, "Database connection failed"

        cursor = connection.cursor()

        for index, row in enumerate(reader, start=1):
            username = row.get('username', '').strip()
            email = row.get('email', '').strip()
            password = row.get('password', '').strip() or 'Default@123'
            full_name = row.get('full_name', '').strip() or 'Unknown'
            role_position = row.get('role_position', '').strip() or 'User'
            location = row.get('location', '').strip() or 'Unknown'
            passcode = row.get('passcode', MASTER_PASSCODE).strip() or MASTER_PASSCODE

            if not username or not email:
                errors.append(f"Row {index}: Missing username or email")
                continue

            cursor.execute("SELECT user_id FROM users WHERE username = %s OR email = %s", (username, email))
            if cursor.fetchone():
                continue

            password_hash = hash_password(password)
            encrypted_passcode = encrypt_data(passcode)
            cursor.execute('''
                INSERT INTO users (username, email, password_hash, passcode, full_name, role_position, location)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (
                username, email, password_hash, encrypted_passcode,
                encrypt_data(full_name), encrypt_data(role_position), encrypt_data(location)
            ))
            inserted += 1

        connection.commit()
        cursor.close()
        connection.close()

        if errors:
            return True, f"Imported {inserted} users with {len(errors)} row issues: {errors[:3]}"

        return True, f"Imported {inserted} users successfully"

    except Exception as e:
        return False, f"Import error: {str(e)}"


# ==================== STREAMLIT UI ====================
def show_login_ui():
    """Display login UI"""

    st.markdown("""
        <style>
        .login-container {
            max-width: 500px;
            margin: 0 auto;
            padding: 20px;
        }
        .header-box {
            background: linear-gradient(135deg, #6B5B95, #88B04B);
            color: white;
            padding: 25px;
            text-align: center;
            border-radius: 15px;
            margin-bottom: 30px;
        }
        </style>
    """, unsafe_allow_html=True)

    # Initialize database
    init_database()

    # Initialize session state
    if 'auth_page' not in st.session_state:
        st.session_state.auth_page = 'login'
    if 'login_type_selected' not in st.session_state:
        st.session_state.login_type_selected = False

    # Header
    st.markdown("""
        <div class="header-box">
            <h1>🔐 EDA Application</h1>
            <p>Secure Access Portal</p>
        </div>
    """, unsafe_allow_html=True)

    # Show "Select Login Type" only if not yet selected
    if not st.session_state.login_type_selected:
        st.markdown("### Select Login Type")
        col_admin1, col_admin2 = st.columns(2)
        with col_admin1:
            if st.button("🔓 User Login", use_container_width=True, key="user_login_btn"):
                st.session_state.show_admin_login = False
                st.session_state.login_type_selected = True
                st.rerun()
        with col_admin2:
            if st.button("⚙️ Admin Login", use_container_width=True, key="admin_login_btn"):
                st.session_state.show_admin_login = True
                st.session_state.login_type_selected = True
                st.rerun()

        st.markdown("---")
        return  # Don't show anything else until login type is selected

    # Show back button when login type is selected
    col_back, col_empty = st.columns([0.15, 0.85])
    with col_back:
        if st.button("← Back", use_container_width=True, key="back_to_selection"):
            st.session_state.login_type_selected = False
            st.session_state.show_admin_login = False
            st.session_state.auth_page = 'login'
            st.rerun()

    st.markdown("---")

    # Navigation tabs (only for user login)
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔓 Login", use_container_width=True):
            st.session_state.auth_page = 'login'
    with col2:
        if st.button("📝 Register", use_container_width=True):
            st.session_state.auth_page = 'register'
    with col3:
        if st.button("🔑 Forgot Password", use_container_width=True):
            st.session_state.auth_page = 'forgot_password'

    st.markdown("---")

    # LOGIN PAGE
    if st.session_state.auth_page == 'login':
        st.markdown("### 🔓 Login to Your Account")

        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            passcode = st.text_input("Passcode (6 digits)", placeholder="Enter your 6-digit passcode", max_chars=6)

            submitted = st.form_submit_button("Login", use_container_width=True)

            if submitted:
                if not username or not password or not passcode:
                    st.error("Please enter username, password, and passcode")
                elif len(passcode) != 6 or not passcode.isdigit():
                    st.error("Passcode must be 6 digits")
                else:
                    success, user_id, message = login_user(username, password, passcode)

                    if success:
                        st.session_state.authenticated = True
                        st.session_state.user_id = user_id
                        st.session_state.username = username
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

    # REGISTER PAGE
    elif st.session_state.auth_page == 'register':
        st.markdown("### 📝 Create New Account")

        # Step 1: Passcode verification
        if 'passcode_verified' not in st.session_state:
            st.session_state.passcode_verified = False

        if not st.session_state.passcode_verified:
            st.markdown("**Step 1: Enter Passcode to Register**")
            st.info("ℹ️ You need to enter the passcode to access the registration form")

            with st.form("passcode_form"):
                reg_passcode = st.text_input("Passcode (6 digits)", placeholder="Enter 6-digit passcode", max_chars=6,
                                             type="password")
                submitted = st.form_submit_button("Verify Passcode", use_container_width=True)

                if submitted:
                    if not reg_passcode:
                        st.error("Please enter passcode")
                    elif len(reg_passcode) != 6 or not reg_passcode.isdigit():
                        st.error("Passcode must be 6 digits")
                    elif reg_passcode != MASTER_PASSCODE:
                        st.error("Invalid passcode")
                    else:
                        st.session_state.passcode_verified = True
                        st.success("✅ Passcode verified! You can now register.")
                        st.rerun()
        else:
            # Step 2: Registration form
            st.markdown("**Step 2: Fill Registration Details**")

            with st.form("register_form"):
                username = st.text_input("Username", placeholder="Choose a username (min 3 characters)")
                email = st.text_input("Email", placeholder="Enter your email")
                full_name = st.text_input("Full Name", placeholder="Enter your full name")
                role_position = st.text_input("Role/Position", placeholder="Your role or position (e.g., Data Analyst)")
                location = st.text_input("Location", placeholder="Your location")
                password = st.text_input("Password", type="password",
                                         placeholder="Min 8 chars, 1 uppercase, 1 digit, 1 special char")
                confirm_password = st.text_input("Confirm Password", type="password",
                                                 placeholder="Confirm your password")

                submitted = st.form_submit_button("Register", use_container_width=True)

                if submitted:
                    success, messages = register_user(username, email, password,
                                                      confirm_password, full_name,
                                                      role_position, location, MASTER_PASSCODE)

                    if success:
                        st.success("✅ Registration successful! Please login with your credentials.")
                        st.session_state.passcode_verified = False
                        st.session_state.auth_page = 'login'
                        st.rerun()
                    else:
                        for msg in messages:
                            st.error(msg)

                # Password requirements
                with st.expander("📋 Password Requirements"):
                    st.markdown("""
                    - Minimum 8 characters
                    - At least one uppercase letter (A-Z)
                    - At least one digit (0-9)
                    - At least one special character (!@#$%^&*(),.?":{}|<>)
                    """)

            # Option to go back
            if st.button("← Back to Passcode"):
                st.session_state.passcode_verified = False
                st.rerun()

    # FORGOT PASSWORD PAGE
    elif st.session_state.auth_page == 'forgot_password':
        st.markdown("### 🔑 Reset Your Password")

        tab1, tab2 = st.tabs(["Request Reset", "Reset Password"])

        with tab1:
            st.markdown("**Step 1: Enter your email to receive a reset link**")
            with st.form("request_reset_form"):
                email = st.text_input("Email", placeholder="Enter your registered email")
                submitted = st.form_submit_button("Request Reset", use_container_width=True)

                if submitted:
                    if not email:
                        st.error("Please enter your email")
                    else:
                        success, message, token = request_password_reset(email)
                        if success:
                            st.success(f"✅ {message}")
                            st.info(f"**Reset Token:** `{token}`\n\nCopy this token to reset your password")
                            st.session_state.reset_token = token
                        else:
                            st.error(f"❌ {message}")

        with tab2:
            st.markdown("**Step 2: Reset your password with the token**")
            with st.form("reset_password_form"):
                reset_token = st.text_input("Reset Token", placeholder="Paste the token you received")
                new_password = st.text_input("New Password", type="password",
                                             placeholder="Enter your new password")
                confirm_password = st.text_input("Confirm Password", type="password",
                                                 placeholder="Confirm your new password")
                submitted = st.form_submit_button("Reset Password", use_container_width=True)

                if submitted:
                    success, messages = reset_password(reset_token, new_password, confirm_password)

                    if success:
                        st.success("✅ Password reset successful! Please login with your new password.")
                        st.session_state.auth_page = 'login'
                        st.rerun()
                    else:
                        for msg in messages:
                            st.error(f"❌ {msg}")


def show_user_profile_card():
    """Display user profile card in sidebar"""
    # Show admin profile if admin is authenticated
    if st.session_state.get('admin_authenticated') and st.session_state.get('is_admin'):
        st.sidebar.markdown("---")
        st.sidebar.markdown("""
            <style>
            .admin-profile-card {
                background: linear-gradient(135deg, #FF6B6B, #FF7F0E);
                color: white;
                padding: 15px;
                border-radius: 10px;
                text-align: center;
                margin-bottom: 10px;
            }
            .profile-info {
                font-size: 0.9rem;
                line-height: 1.6;
            }
            </style>
            <div class="admin-profile-card">
                <h4>👨‍💼 Admin Profile</h4>
                <div class="profile-info">
                    <b>Role:</b> Administrator<br>
                    <b>Status:</b> 🟢 Active<br>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Logout option for admin
        if st.sidebar.button("🚪 Logout "):
            st.session_state.admin_authenticated = False
            st.session_state.authenticated = False
            st.session_state.is_admin = False
            st.session_state.login_type_selected = False
            st.session_state.show_admin_login = False
            st.session_state.selected_section = "Home"
            st.rerun()

    # Show user profile if user is authenticated
    elif 'user_id' in st.session_state and st.session_state.get('authenticated'):
        user = get_user_profile(st.session_state.user_id)

        if user:
            full_name = user['full_name'] if user['full_name'] and user['full_name'] != 'None' else 'N/A'
            role_position = user['role_position'] if user['role_position'] and user['role_position'] != 'None' else 'N/A'
            location = user['location'] if user['location'] and user['location'] != 'None' else 'N/A'
            
            st.sidebar.markdown("---")
            st.sidebar.markdown("""
                <style>
                .profile-card {
                    background: linear-gradient(135deg, #6B5B95, #88B04B);
                    color: white;
                    padding: 15px;
                    border-radius: 10px;
                    text-align: center;
                    margin-bottom: 10px;
                }
                .profile-info {
                    font-size: 0.9rem;
                    line-height: 1.6;
                }
                </style>
                <div class="profile-card">
                    <h4>👤 User Profile</h4>
                    <div class="profile-info">
                        <b>Username:</b> """ + user['username'] + """<br>
                        <b>Name:</b> """ + full_name + """<br>
                        <b>Position:</b> """ + role_position + """<br>
                        <b>Location:</b> """ + location + """<br>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # Edit profile option
            if st.sidebar.button("✏️ Edit Profile"):
                st.session_state.show_profile_edit = True

            # Show warning if any profile data shows as N/A (might be encrypted with old key)
            if user['full_name'] == 'N/A' or user['role_position'] == 'N/A' or user['location'] == 'N/A':
                st.sidebar.warning("⚠️ Some profile data couldn't be retrieved. Please update your profile to fix this.")

            # Logout option
            if st.sidebar.button("🚪 Logout"):
                st.session_state.authenticated = False
                st.session_state.admin_authenticated = False
                st.session_state.is_admin = False
                st.session_state.user_id = None
                st.session_state.username = None
                st.session_state.selected_section = "Home"
                st.rerun()

            # Show profile edit form if requested
            if st.session_state.get('show_profile_edit'):
                st.sidebar.markdown("---")
                st.sidebar.markdown("### ✏️ Edit Profile")
                st.sidebar.info("💡 Update your profile information below. This will refresh your profile data.")

                with st.sidebar.form("edit_profile_form"):
                    full_name = st.text_input("Full Name", value=user['full_name'] if user['full_name'] != 'N/A' else '')
                    role_position = st.text_input("Position", value=user['role_position'] if user['role_position'] != 'N/A' else '')
                    location = st.text_input("Location", value=user['location'] if user['location'] != 'N/A' else '')

                    if st.form_submit_button("Save Changes"):
                        success, message = update_user_profile(
                            st.session_state.user_id, full_name, role_position, location
                        )
                        if success:
                            st.sidebar.success(message)
                            st.session_state.show_profile_edit = False
                            st.rerun()
                        else:
                            st.sidebar.error(message)


def show_admin_dashboard():
    """Display admin dashboard for user management"""

    # Admin logout button - full width rectangle
    if st.button("🚪 Logout ", use_container_width=True, key="admin_logout_btn"):
        st.session_state.admin_authenticated = False
        st.session_state.authenticated = False
        st.session_state.is_admin = False
        st.session_state.selected_section = "Home"
        st.rerun()

    st.markdown("---")

    # CSV export/import row
    st.markdown("### 📤 Import/Export Users CSV")
    csv_col1, csv_col2 = st.columns([1, 1])
    with csv_col1:
        users_csv = export_users_csv()
        if users_csv:
            st.download_button(
                label="⬇ Download Users CSV",
                data=users_csv,
                file_name="eda_users_export.csv",
                mime="text/csv",
                key="download_users_csv"
            )
        else:
            st.info("No users available to export.")
    with csv_col2:
        uploaded_csv = st.file_uploader("⬆ Upload Users CSV to Import", type=["csv"], key="upload_users_csv")
        if uploaded_csv is not None:
            success, message = import_users_csv(uploaded_csv)
            if success:
                st.success(message)
                st.experimental_rerun()
            else:
                st.error(message)

    st.markdown("---")

    # Tabs for different admin functions
    tab1, tab2 = st.tabs(["👥 View Users", "🔧 User Management"])

    # TAB 1: View all users
    with tab1:
        st.markdown("### Registered Users")

        users = get_all_users()

        if not users:
            st.info("No users registered yet")
        else:
            st.markdown(f"**Total Users:** {len(users)}")
            st.markdown("---")

            # Create a data display
            display_data = []
            for user in users:
                display_data.append({
                    "ID": user['user_id'],
                    "Username": user['username'],
                    "Email": user['email'],
                    "Name": user['full_name'],
                    "Position": user['role_position'],
                    "Location": user['location'],
                    "Registered": user['created_at'].strftime("%Y-%m-%d") if user['created_at'] else "N/A",
                    "Last Login": user['last_login'].strftime("%Y-%m-%d %H:%M") if user['last_login'] else "Never",
                    "Status": "🔴 Restricted" if user['is_restricted'] else "🟢 Active",
                    "Active": "Yes" if user['is_active'] else "No"
                })

            st.dataframe(display_data, use_container_width=True, hide_index=True)

    # TAB 2: User management actions
    with tab2:
        st.markdown("### User Management")

        users = get_all_users()

        if not users:
            st.info("No users to manage")
        else:
            # Create user selection dropdown
            user_options = {f"{u['username']} ({u['email']})": u['user_id'] for u in users}

            selected_user_display = st.selectbox(
                "Select User",
                options=user_options.keys(),
                key="admin_user_select"
            )

            if selected_user_display:
                user_id = user_options[selected_user_display]
                selected_user = next((u for u in users if u['user_id'] == user_id), None)

                if selected_user:
                    # Display user information
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown(f"""
                        **User Information**
                        - **ID:** {selected_user['user_id']}
                        - **Username:** {selected_user['username']}
                        - **Email:** {selected_user['email']}
                        - **Name:** {selected_user['full_name']}
                        - **Position:** {selected_user['role_position']}
                        - **Location:** {selected_user['location']}
                        """)

                    with col2:
                        st.markdown(f"""
                        **Account Status**
                        - **Registered:** {selected_user['created_at'].strftime("%Y-%m-%d %H:%M") if selected_user['created_at'] else 'N/A'}
                        - **Last Login:** {selected_user['last_login'].strftime("%Y-%m-%d %H:%M") if selected_user['last_login'] else 'Never'}
                        - **Active:** {'Yes' if selected_user['is_active'] else 'No'}
                        - **Restricted:** {'Yes ❌' if selected_user['is_restricted'] else 'No ✅'}
                        """)

                    st.markdown("---")

                    # Management actions
                    action_col1, action_col2, action_col3 = st.columns(3)

                    with action_col1:
                        if selected_user['is_restricted']:
                            if st.button("🔓 Grant Access", use_container_width=True, key=f"grant_{user_id}"):
                                success, message = restrict_user(user_id, restrict=False)
                                if success:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)
                        else:
                            if st.button("🔒 Restrict Access", use_container_width=True, key=f"restrict_{user_id}"):
                                success, message = restrict_user(user_id, restrict=True)
                                if success:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)

                    with action_col2:
                        st.write("")

                    with action_col3:
                        if st.button("🗑️ Delete User", use_container_width=True, key=f"delete_{user_id}"):
                            st.session_state[f"confirm_delete_{user_id}"] = True

                    # Confirmation for deletion
                    if st.session_state.get(f"confirm_delete_{user_id}", False):
                        st.warning(
                            f"⚠️ Are you sure you want to permanently delete user '{selected_user['username']}'? This action cannot be undone!")

                        del_col1, del_col2 = st.columns(2)

                        with del_col1:
                            if st.button("✅ Yes, Delete Completely", use_container_width=True,
                                         key=f"confirm_yes_{user_id}"):
                                success, message = delete_user_completely(user_id)
                                if success:
                                    st.success(message)
                                    st.session_state[f"confirm_delete_{user_id}"] = False
                                    st.rerun()
                                else:
                                    st.error(message)

                        with del_col2:
                            if st.button("❌ Cancel", use_container_width=True, key=f"confirm_no_{user_id}"):
                                st.session_state[f"confirm_delete_{user_id}"] = False
                                st.rerun()


def show_admin_login_ui():
    """Display admin login UI"""

    st.markdown("""
        <style>
        .admin-login-container {
            max-width: 500px;
            margin: 0 auto;
            padding: 20px;
        }
        .header-box {
            background: linear-gradient(135deg, #1f77b4, #ff7f0e);
            color: white;
            padding: 25px;
            text-align: center;
            border-radius: 15px;
            margin-bottom: 30px;
        }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div class="header-box">
            <h1>🔐 Admin Login</h1>
            <p>Administrator Access Portal</p>
        </div>
    """, unsafe_allow_html=True)

    # Back button to return to login type selection
    col_back, col_empty = st.columns([0.15, 0.85])
    with col_back:
        if st.button("← Back", use_container_width=True, key="back_from_admin"):
            st.session_state.login_type_selected = False
            st.session_state.show_admin_login = False
            st.rerun()

    st.markdown("---")

    st.markdown("### Administrator Credentials")

    with st.form("admin_login_form"):
        username = st.text_input("Username", placeholder="Enter admin username")
        password = st.text_input("Password", type="password", placeholder="Enter admin password")
        passcode = st.text_input("Passcode (6 digits)", placeholder="Enter 6-digit passcode", max_chars=6)

        submitted = st.form_submit_button("Admin Login", use_container_width=True)

        if submitted:
            if not username or not password or not passcode:
                st.error("Please enter username, password, and passcode")
            elif username != ADMIN_USERNAME:
                st.error("Invalid admin username")
            elif password != ADMIN_PASSWORD:
                st.error("Invalid admin password")
            elif len(passcode) != 6 or not passcode.isdigit():
                st.error("Passcode must be 6 digits")
            else:
                success, message = admin_login(passcode)

                if success:
                    st.session_state.admin_authenticated = True
                    st.session_state.authenticated = True
                    st.session_state.is_admin = True
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)


def authenticate():
    """Main authentication handler"""
    # Initialize database
    init_database()

    # Check if user is authenticated
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'admin_authenticated' not in st.session_state:
        st.session_state.admin_authenticated = False
    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = False
    if 'show_admin_login' not in st.session_state:
        st.session_state.show_admin_login = False
    if 'login_type_selected' not in st.session_state:
        st.session_state.login_type_selected = False

    # If admin is authenticated, return True (admin dashboard handled in app.py)
    if st.session_state.admin_authenticated and st.session_state.is_admin:
        return True

    # If regular user is authenticated, return True
    if st.session_state.authenticated and not st.session_state.is_admin:
        return True

    # Show appropriate login UI (handles both user and admin login options)
    if st.session_state.show_admin_login:
        show_admin_login_ui()
    else:
        show_login_ui()

    return False


# Export for use in main app
__all__ = ['authenticate', 'show_user_profile_card', 'get_user_profile', 'init_database',
           'show_admin_dashboard', 'admin_login', 'get_all_users', 'restrict_user', 'delete_user_completely']

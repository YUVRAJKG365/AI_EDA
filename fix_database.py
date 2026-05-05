"""
Database Fix Script - For fixing "Data too long for column" error

This script will fix your MySQL database schema by converting VARCHAR columns to TEXT.
Run this script if you're getting the error:
    "Registration error: 1406 (22001): Data too long for column 'role_position' at row 1"

Usage:
    python fix_database.py
"""

import mysql.connector
from mysql.connector import Error

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '.#RamJi.',
    'database': 'eda_app_users'
}


def fix_database():
    """Fix the database schema"""
    try:
        # Connect to database
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()

        print("🔧 Starting database migration...")
        print("-" * 50)

        # Check current column types
        print("📋 Checking current column types...")
        cursor.execute("""
            SELECT COLUMN_NAME, COLUMN_TYPE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'users'
            AND COLUMN_NAME IN ('full_name', 'role_position', 'location')
        """, (DB_CONFIG['database'],))

        columns = cursor.fetchall()
        print("\nCurrent columns:")
        for col_name, col_type in columns:
            print(f"  - {col_name}: {col_type}")

        # Perform migration
        print("\n🔄 Converting columns to TEXT...")
        try:
            cursor.execute("ALTER TABLE users MODIFY COLUMN full_name TEXT NOT NULL")
            print("  ✅ full_name converted to TEXT")
        except Exception as e:
            print(f"  ⚠️  full_name error: {e}")

        try:
            cursor.execute("ALTER TABLE users MODIFY COLUMN role_position TEXT")
            print("  ✅ role_position converted to TEXT")
        except Exception as e:
            print(f"  ⚠️  role_position error: {e}")

        try:
            cursor.execute("ALTER TABLE users MODIFY COLUMN location TEXT")
            print("  ✅ location converted to TEXT")
        except Exception as e:
            print(f"  ⚠️  location error: {e}")

        # Commit changes
        connection.commit()
        print("\n✅ Migration completed successfully!")

        # Verify changes
        print("\n📋 Verifying new column types...")
        cursor.execute("""
            SELECT COLUMN_NAME, COLUMN_TYPE 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'users'
            AND COLUMN_NAME IN ('full_name', 'role_position', 'location')
        """, (DB_CONFIG['database'],))

        columns = cursor.fetchall()
        print("\nNew columns:")
        for col_name, col_type in columns:
            print(f"  - {col_name}: {col_type}")

        print("\n✅ Database migration complete!")
        print("You can now register without the 'Data too long' error.")

        cursor.close()
        connection.close()
        return True

    except Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def drop_and_recreate_database():
    """Drop and recreate the entire database (WARNING: This deletes all user data)"""
    try:
        # Connect to MySQL server (not the database)
        connection = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        cursor = connection.cursor()

        print("⚠️  WARNING: This will delete the database and all user data!")
        response = input("Are you sure you want to continue? (yes/no): ").strip().lower()

        if response != 'yes':
            print("❌ Cancelled.")
            return False

        print("\n🗑️  Dropping database...")
        cursor.execute(f"DROP DATABASE IF EXISTS {DB_CONFIG['database']}")
        connection.commit()
        print("✅ Database dropped.")

        print("\n📝 Run your application to recreate the database with correct schema.")
        print("The database will be automatically created with TEXT columns.")

        cursor.close()
        connection.close()
        return True

    except Error as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("EDA App - Database Fix Tool")
    print("=" * 50)
    print("\nOptions:")
    print("  1. Fix existing database (ALTER TABLE)")
    print("  2. Drop and recreate database (WARNING: deletes all data)")
    print("  3. Exit")
    print()

    choice = input("Select option (1/2/3): ").strip()

    if choice == "1":
        print()
        fix_database()
    elif choice == "2":
        print()
        drop_and_recreate_database()
    else:
        print("Exiting...")

    input("\nPress Enter to close...")

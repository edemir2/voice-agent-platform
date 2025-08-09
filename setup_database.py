#!/usr/bin/env python3
"""
Database setup script for the demo application.
This script will create the demo table if it doesn't exist.
"""

import psycopg2
import sys

# Database connection settings - Update these with your actual values
DB_HOST = "localhost"
DB_NAME = "test"  # Update this to your actual database name
DB_USER = "postgres"  # Update this to your actual username
DB_PASS = "test"  # Update this to your actual password

def create_demo_table():
    """Create the demo table if it doesn't exist"""
    try:
        # Connect to the database
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASS
        )
        
        cur = conn.cursor()
        
        # Create the demo table
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
        
        print("✅ Demo table created successfully!")
        print("📋 Table structure:")
        print("   - id: SERIAL PRIMARY KEY")
        print("   - full_name: VARCHAR(100) NOT NULL")
        print("   - business_name: VARCHAR(150) NOT NULL")
        print("   - business_type: VARCHAR(100) NOT NULL (with CHECK constraint)")
        print("   - phone_number: VARCHAR(20)")
        print("   - email: VARCHAR(100) UNIQUE NOT NULL")
        print("   - password_hash: TEXT NOT NULL")
        print("   - created_at: TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        
    except psycopg2.OperationalError as e:
        print(f"❌ Database connection failed: {e}")
        print("\n🔧 Please check your database settings in app.py:")
        print(f"   - Host: {DB_HOST}")
        print(f"   - Database: {DB_NAME}")
        print(f"   - User: {DB_USER}")
        print(f"   - Password: {DB_PASS}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("🚀 Setting up database for demo application...")
    create_demo_table()
    print("\n🎉 Database setup complete! You can now run the Flask application.") 
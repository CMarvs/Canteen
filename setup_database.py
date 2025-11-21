#!/usr/bin/env python3
"""
Database Setup Script for RMLCanteen
This script will:
1. Create all necessary database tables
2. Create initial admin and user accounts
3. Initialize the database schema

Usage:
    python setup_database.py
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os
import sys

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Get database URL from environment variable or use the one from server.py
DB_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_Y6Bh0RQzxKib@ep-red-violet-a1hjbfb0-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")

def create_tables(conn):
    """Create all necessary database tables"""
    cur = conn.cursor()
    
    print("[INFO] Creating database tables...")
    
    # Create users table
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                id_proof TEXT,
                selfie_proof TEXT,
                is_approved BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        conn.commit()
        print("[OK] users table created/verified")
    except Exception as e:
        conn.rollback()
        print(f"[WARNING] Error creating users table: {e}")
    
    # Create orders table
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                fullname TEXT NOT NULL,
                contact TEXT NOT NULL,
                location TEXT NOT NULL,
                items JSONB NOT NULL,
                total NUMERIC(10, 2) NOT NULL,
                status TEXT DEFAULT 'Pending',
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        conn.commit()
        print("[OK] orders table created/verified")
    except Exception as e:
        conn.rollback()
        print(f"[WARNING] Error creating orders table: {e}")
    
    # Create menu_items table
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS menu_items (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                price NUMERIC(10, 2) NOT NULL,
                category TEXT NOT NULL DEFAULT 'foods',
                is_available BOOLEAN DEFAULT TRUE,
                quantity INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        conn.commit()
        # Try to add indexes (may fail if table already exists without category)
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_menu_category ON menu_items(category);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_menu_available ON menu_items(is_available);")
            conn.commit()
        except:
            pass
        print("[OK] menu_items table created/verified")
    except Exception as e:
        conn.rollback()
        print(f"[WARNING] Error creating menu_items table: {e}")
    
    # Create soldout_items table
    try:
        # Reset transaction state if needed
        conn.rollback()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS soldout_items (
                id SERIAL PRIMARY KEY,
                item_id TEXT UNIQUE NOT NULL
            );
        """)
        conn.commit()
        print("[OK] soldout_items table created/verified")
    except Exception as e:
        conn.rollback()
        # Try again after rollback
        try:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS soldout_items (
                    id SERIAL PRIMARY KEY,
                    item_id TEXT UNIQUE NOT NULL
                );
            """)
            conn.commit()
            print("[OK] soldout_items table created/verified")
        except:
            print(f"[WARNING] Error creating soldout_items table: {e}")
    
    print("\n[SUCCESS] All tables created successfully!\n")

def create_initial_accounts(conn):
    """Create initial admin and user accounts"""
    cur = conn.cursor()
    
    print("[INFO] Creating initial accounts...")
    
    # Check if accounts already exist
    cur.execute("SELECT email FROM users WHERE email IN ('admin@canteen', 'user@demo')")
    results = cur.fetchall()
    existing = []
    for row in results:
        if isinstance(row, dict):
            existing.append(row.get('email'))
        else:
            existing.append(row[0] if len(row) > 0 else None)
    
    # Create admin account
    if 'admin@canteen' not in existing:
        try:
            cur.execute("""
                INSERT INTO users (name, email, password, role, is_approved)
                VALUES ('Admin', 'admin@canteen', 'admin123', 'admin', TRUE)
                ON CONFLICT (email) DO NOTHING
            """)
            print("[OK] Admin account created: admin@canteen / admin123")
        except Exception as e:
            print(f"[WARNING] Error creating admin account: {e}")
    else:
        print("[INFO] Admin account already exists: admin@canteen")
    
    # Create demo user account
    if 'user@demo' not in existing:
        try:
            cur.execute("""
                INSERT INTO users (name, email, password, role, is_approved)
                VALUES ('Demo User', 'user@demo', 'user123', 'user', TRUE)
                ON CONFLICT (email) DO NOTHING
            """)
            print("[OK] Demo user account created: user@demo / user123")
        except Exception as e:
            print(f"[WARNING] Error creating demo user account: {e}")
    else:
        print("[INFO] Demo user account already exists: user@demo")
    
    conn.commit()
    print("\n[SUCCESS] Account setup complete!\n")

def main():
    """Main setup function"""
    print("=" * 60)
    print("RMLCanteen Database Setup")
    print("=" * 60)
    print()
    
    # Check if DATABASE_URL is set
    if not os.getenv("DATABASE_URL"):
        print("[INFO] DATABASE_URL environment variable not set.")
        print("       Using default connection string from server.py")
        print("       To use a different database, set DATABASE_URL environment variable")
        print()
    
    print(f"[INFO] Connecting to database...")
    print(f"       URL: {DB_URL[:50]}...")
    print()
    
    conn = None
    try:
        # Connect to database
        conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
        print("[OK] Connected to database successfully!\n")
        
        # Create tables
        create_tables(conn)
        
        # Create initial accounts
        create_initial_accounts(conn)
        
        # Display summary
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as count FROM users")
        result = cur.fetchone()
        user_count = result.get('count') if isinstance(result, dict) else (result[0] if result else 0)
        
        cur.execute("SELECT COUNT(*) as count FROM users WHERE role = 'admin'")
        result = cur.fetchone()
        admin_count = result.get('count') if isinstance(result, dict) else (result[0] if result else 0)
        
        print("=" * 60)
        print("[SUCCESS] Database setup complete!")
        print("=" * 60)
        print(f"Total users: {user_count}")
        print(f"Admin accounts: {admin_count}")
        print()
        print("Test Accounts:")
        print("  Admin: admin@canteen / admin123")
        print("  User:  user@demo / user123")
        print()
        print("You can now start the server and login!")
        print("=" * 60)
        
    except psycopg2.OperationalError as e:
        print(f"[ERROR] Database connection failed!")
        print(f"        Error: {e}")
        print()
        print("Make sure:")
        print("  1. Your NeonDB database is accessible")
        print("  2. The DATABASE_URL is correct")
        print("  3. Your network allows connections to NeonDB")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()


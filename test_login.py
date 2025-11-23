#!/usr/bin/env python3
"""
Test script to verify database connection and login functionality
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import os

# Get database URL
DB_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_Y6Bh0RQzxKib@ep-red-violet-a1hjbfb0-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")

def test_database_connection():
    """Test database connection"""
    print("=" * 60)
    print("Testing Database Connection")
    print("=" * 60)
    
    try:
        conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
        print("✅ Database connection successful!")
        
        cur = conn.cursor()
        
        # Check users table
        cur.execute("SELECT COUNT(*) as count FROM users")
        result = cur.fetchone()
        user_count = result.get('count') if isinstance(result, dict) else (result[0] if result else 0)
        print(f"✅ Users table exists: {user_count} users found")
        
        # List all users
        cur.execute("SELECT id, name, email, role, is_approved FROM users ORDER BY id")
        users = cur.fetchall()
        
        print("\n📋 Registered Users:")
        print("-" * 60)
        for user in users:
            user_dict = user if isinstance(user, dict) else {}
            user_id = user_dict.get('id', 'N/A')
            name = user_dict.get('name', 'N/A')
            email = user_dict.get('email', 'N/A')
            role = user_dict.get('role', 'N/A')
            is_approved = user_dict.get('is_approved', False)
            approved_status = "✅ Approved" if is_approved else "⏳ Pending"
            print(f"ID: {user_id} | {name} | {email} | Role: {role} | {approved_status}")
        
        print("-" * 60)
        
        # Test login query
        print("\n🔐 Testing Login Query:")
        test_email = "admin@canteen"
        test_password = "admin123"
        
        cur.execute(
            "SELECT * FROM users WHERE LOWER(email)=%s AND password=%s",
            (test_email.lower(), test_password)
        )
        test_user = cur.fetchone()
        
        if test_user:
            print(f"✅ Login test successful for {test_email}")
            user_dict = test_user if isinstance(test_user, dict) else {}
            print(f"   User ID: {user_dict.get('id')}")
            print(f"   Name: {user_dict.get('name')}")
            print(f"   Role: {user_dict.get('role')}")
            print(f"   Approved: {user_dict.get('is_approved')}")
        else:
            print(f"❌ Login test failed for {test_email}")
        
        conn.close()
        print("\n✅ All tests passed!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("=" * 60)
        return False

if __name__ == "__main__":
    test_database_connection()


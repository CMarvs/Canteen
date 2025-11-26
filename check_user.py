#!/usr/bin/env python3
"""
Quick script to check if a user exists in the database
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import sys

# Get database URL from environment variable or use the one from server.py
DB_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_Y2KOWuHn9DMU@ep-lingering-tooth-a1kqy37g-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")

def check_user(email):
    """Check if a user exists and their details"""
    try:
        conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        
        email_lower = email.lower().strip()
        cur.execute("SELECT id, name, email, role, is_approved FROM users WHERE LOWER(email)=%s", (email_lower,))
        user = cur.fetchone()
        
        if user:
            if isinstance(user, dict):
                print(f"✅ User found:")
                print(f"   ID: {user.get('id')}")
                print(f"   Name: {user.get('name')}")
                print(f"   Email: {user.get('email')}")
                print(f"   Role: {user.get('role')}")
                print(f"   Approved: {user.get('is_approved')}")
            else:
                print(f"✅ User found: {user}")
        else:
            print(f"❌ User not found: {email_lower}")
            print("\n💡 Possible reasons:")
            print("   1. User hasn't registered yet")
            print("   2. Email is misspelled")
            print("   3. User was deleted")
        
        # Show all users
        print("\n📋 All users in database:")
        cur.execute("SELECT id, name, email, role, is_approved FROM users ORDER BY id")
        all_users = cur.fetchall()
        if all_users:
            for u in all_users:
                if isinstance(u, dict):
                    print(f"   - {u.get('email')} ({u.get('role')}) - Approved: {u.get('is_approved')}")
                else:
                    print(f"   - {u}")
        else:
            print("   No users found")
        
        conn.close()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "llyzaponio07@gmail.com"
    print(f"Checking user: {email}\n")
    check_user(email)


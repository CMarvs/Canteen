"""
Script to delete all users from the database
Run this to reset and start fresh with registration
"""
import psycopg2
import os

# Database connection
DB_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_Y6Bh0RQzxKib@ep-red-violet-a1hjbfb0-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")

def reset_users():
    conn = None
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        print("WARNING: This will delete ALL users from the database!")
        confirm = input("Type 'DELETE ALL USERS' to confirm: ")
        
        if confirm != "DELETE ALL USERS":
            print("Cancelled. No users were deleted.")
            return
        
        # Delete all users
        cur.execute("DELETE FROM users")
        deleted_count = cur.rowcount
        conn.commit()
        
        print(f"Successfully deleted {deleted_count} user(s) from the database.")
        print("You can now register as the first admin user!")
        
    except Exception as e:
        print(f"Error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    reset_users()


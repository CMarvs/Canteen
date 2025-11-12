"""
Quick script to delete all users from database
Run: python DELETE_ALL_USERS.py
"""
import psycopg2
import os

DB_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_O0LrfcY7oGZN@ep-silent-rain-a19bkdss-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require")

conn = psycopg2.connect(DB_URL)
cur = conn.cursor()

# First delete all orders (they reference users)
cur.execute("DELETE FROM orders")
orders_deleted = cur.rowcount
print(f"Deleted {orders_deleted} order(s)")

# Then delete all users
cur.execute("DELETE FROM users")
users_deleted = cur.rowcount
conn.commit()
conn.close()

print(f"Deleted {users_deleted} user(s). You can now register as the first admin!")


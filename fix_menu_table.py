#!/usr/bin/env python3
"""Script to fix menu_items table structure"""

import psycopg2
from psycopg2.extras import RealDictCursor

DB_URL = "postgresql://neondb_owner:npg_O0LrfcY7oGZN@ep-silent-rain-a19bkdss-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

def fix_menu_table():
    try:
        conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        
        # Check current columns
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'menu_items' 
            ORDER BY ordinal_position
        """)
        cols = cur.fetchall()
        column_names = [c.get('column_name') if isinstance(c, dict) else c[0] for c in cols]
        
        print("Current columns:", column_names)
        
        # Add missing columns
        if 'category' not in column_names:
            print("Adding 'category' column...")
            cur.execute("ALTER TABLE menu_items ADD COLUMN category TEXT NOT NULL DEFAULT 'foods';")
        
        if 'is_available' not in column_names:
            print("Adding 'is_available' column...")
            cur.execute("ALTER TABLE menu_items ADD COLUMN is_available BOOLEAN DEFAULT TRUE;")
        
        if 'created_at' not in column_names:
            print("Adding 'created_at' column...")
            cur.execute("ALTER TABLE menu_items ADD COLUMN created_at TIMESTAMP DEFAULT NOW();")
        
        # Create indexes if they don't exist
        try:
            cur.execute("CREATE INDEX IF NOT EXISTS idx_menu_category ON menu_items(category);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_menu_available ON menu_items(is_available);")
        except:
            pass
        
        conn.commit()
        print("SUCCESS: menu_items table structure fixed!")
        
        # Verify
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'menu_items' 
            ORDER BY ordinal_position
        """)
        cols = cur.fetchall()
        column_names = [c.get('column_name') if isinstance(c, dict) else c[0] for c in cols]
        print("Updated columns:", column_names)
        
        conn.close()
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_menu_table()


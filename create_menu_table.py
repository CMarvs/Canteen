#!/usr/bin/env python3
"""Script to create menu_items table in NeonDB"""

import psycopg2
from psycopg2.extras import RealDictCursor
import os

# Use environment variable or fallback to default
DB_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_Y6Bh0RQzxKib@ep-red-violet-a1hjbfb0-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")

def create_menu_table():
    try:
        conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
        cur = conn.cursor()
        
        # Check if table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'menu_items'
            ) as exists;
        """)
        result = cur.fetchone()
        table_exists = result.get('exists') if isinstance(result, dict) else (result[0] if result else False)
        
        if table_exists:
            print("Table menu_items already exists!")
            return
        
        print("Creating menu_items table...")
        
        # Create table
        cur.execute("""
            CREATE TABLE menu_items (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                price NUMERIC(10, 2) NOT NULL,
                category TEXT NOT NULL DEFAULT 'foods',
                is_available BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            );
        """)
        
        # Create indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_menu_category ON menu_items(category);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_menu_available ON menu_items(is_available);")
        
        conn.commit()
        print("SUCCESS: menu_items table created!")
        
        # Optionally insert sample data
        print("\nWould you like to insert sample menu items? (y/n): ", end='')
        # For automated use, we'll skip this
        # response = input().strip().lower()
        # if response == 'y':
        #     cur.execute("""
        #         INSERT INTO menu_items (name, price, category, is_available) VALUES
        #         ('Budget Meal A (Chicken Teriyaki + Rice)', 50.00, 'budget', true),
        #         ('Budget Meal B (Pork fillet + Rice)', 50.00, 'budget', true),
        #         ('Budget Meal C (Burger Steak + Rice)', 50.00, 'budget', true),
        #         ('Budget Meal D (Siomai + Rice)', 45.00, 'budget', true),
        #         ('Sisig', 70.00, 'foods', true),
        #         ('Dinakdakan', 75.00, 'foods', true),
        #         ('Pork Adobo', 65.00, 'foods', true),
        #         ('Beef Caldereta', 80.00, 'foods', true),
        #         ('Carbonara', 70.00, 'foods', true),
        #         ('Spaghetti', 60.00, 'foods', true),
        #         ('Palabok', 60.00, 'foods', true),
        #         ('Fried Rice', 20.00, 'foods', true),
        #         ('Coke', 25.00, 'drinks', true),
        #         ('Sprite', 25.00, 'drinks', true),
        #         ('Royal', 25.00, 'drinks', true),
        #         ('Bottled Water', 15.00, 'drinks', true),
        #         ('C2', 20.00, 'drinks', true),
        #         ('Yakult', 15.00, 'drinks', true);
        #     """)
        #     conn.commit()
        #     print("Sample menu items inserted!")
        
        conn.close()
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_menu_table()


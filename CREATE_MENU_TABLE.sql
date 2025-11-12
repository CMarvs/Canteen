-- Create menu_items table for dynamic menu management
-- Run this SQL in your NeonDB database

CREATE TABLE IF NOT EXISTS menu_items (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    category TEXT NOT NULL DEFAULT 'foods',
    is_available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_menu_category ON menu_items(category);
CREATE INDEX IF NOT EXISTS idx_menu_available ON menu_items(is_available);

-- Optional: Insert some sample menu items
INSERT INTO menu_items (name, price, category, is_available) VALUES
('Budget Meal A (Chicken Teriyaki + Rice)', 50.00, 'budget', true),
('Budget Meal B (Pork fillet + Rice)', 50.00, 'budget', true),
('Budget Meal C (Burger Steak + Rice)', 50.00, 'budget', true),
('Budget Meal D (Siomai + Rice)', 45.00, 'budget', true),
('Sisig', 70.00, 'foods', true),
('Dinakdakan', 75.00, 'foods', true),
('Pork Adobo', 65.00, 'foods', true),
('Beef Caldereta', 80.00, 'foods', true),
('Carbonara', 70.00, 'foods', true),
('Spaghetti', 60.00, 'foods', true),
('Palabok', 60.00, 'foods', true),
('Fried Rice', 20.00, 'foods', true),
('Coke', 25.00, 'drinks', true),
('Sprite', 25.00, 'drinks', true),
('Royal', 25.00, 'drinks', true),
('Bottled Water', 15.00, 'drinks', true),
('C2', 20.00, 'drinks', true),
('Yakult', 15.00, 'drinks', true)
ON CONFLICT DO NOTHING;


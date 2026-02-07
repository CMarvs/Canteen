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

ALTER TABLE menu_items ADD COLUMN image_url TEXT;
-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_menu_category ON menu_items(category);
CREATE INDEX IF NOT EXISTS idx_menu_available ON menu_items(is_available);

-- Optional: Insert some sample menu items
INSERT INTO menu_items (name, price, category, is_available, image_url) VALUES
('Budget Meal A (Chicken Teriyaki + Rice)', 50.00, 'budget', true,'/static/images/budget-meal-a.jpg'),
('Budget Meal B (Pork fillet + Rice)', 50.00, 'budget', true, '/static/images/budget-meal-b.jpg'),
('Budget Meal C (Burger Steak + Rice)', 50.00, 'budget', true, '/static/images/budget-meal-c.jpg'),
('Budget Meal D (Siomai + Rice)', 45.00, 'budget', true, '/static/images/budget-meal-d.jpg'),
('Sisig', 70.00, 'foods', true, '/static/images/sisig.jpg'),
('Dinakdakan', 75.00, 'foods', true, '/static/images/dinakdakan.jpg'),
('Pork Adobo', 65.00, 'foods', true, '/static/images/pork-adobo.jpg'),
('Beef Caldereta', 80.00, 'foods', true, '/static/images/beef-caldereta.jpg'),
('Carbonara', 70.00, 'foods', true, '/static/images/carbonara.jpg'),
('Spaghetti', 60.00, 'foods', true, '/static/images/spaghetti.jpg'),
('Palabok', 60.00, 'foods', true, '/static/images/palabok.jpg'),
('Fried Rice', 20.00, 'foods', true, '/static/images/fried-rice.jpg'),
('Coke', 25.00, 'drinks', true, '/static/images/coke.jpg'),
('Sprite', 25.00, 'drinks', true, '/static/images/sprite.jpg'),
('Royal', 25.00, 'drinks', true, '/static/images/royal.jpg'),
('Bottled Water', 15.00, 'drinks', true, '/static/images/bottled-water.jpg'),
('C2', 20.00, 'drinks', true, '/static/images/c2.jpg'),
('Yakult', 15.00, 'drinks', true, '/static/images/yakult.jpg')
ON CONFLICT DO NOTHING;


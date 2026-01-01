-- Add passengers column to orders table
ALTER TABLE orders ADD COLUMN IF NOT EXISTS passengers INTEGER DEFAULT 1;

-- Update existing orders to have at least 1 passenger (already default, but good for safety)
UPDATE orders SET passengers = 1 WHERE passengers IS NULL;

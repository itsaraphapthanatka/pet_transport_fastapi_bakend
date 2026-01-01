-- Add commission_rate column to orders table
ALTER TABLE orders ADD COLUMN IF NOT EXISTS commission_rate NUMERIC(5,4);

-- Set default commission_rate for existing orders (7%)
UPDATE orders 
SET commission_rate = 0.0700 
WHERE commission_rate IS NULL;

-- Verify the changes
SELECT id, price, commission_rate, platform_fee, driver_earnings 
FROM orders 
WHERE price IS NOT NULL 
LIMIT 10;

-- Add commission columns to orders table
ALTER TABLE orders ADD COLUMN IF NOT EXISTS platform_fee NUMERIC(10,2);
ALTER TABLE orders ADD COLUMN IF NOT EXISTS driver_earnings NUMERIC(10,2);

-- Verify columns were added
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'orders' 
AND column_name IN ('platform_fee', 'driver_earnings');

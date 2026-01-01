-- Migration SQL to calculate and update commission for existing orders
-- Run this SQL script to update all existing orders with platform_fee and driver_earnings

-- First, add the columns if they don't exist (skip if already added via migration)
-- ALTER TABLE orders ADD COLUMN IF NOT EXISTS platform_fee NUMERIC(10,2);
-- ALTER TABLE orders ADD COLUMN IF NOT EXISTS driver_earnings NUMERIC(10,2);

-- Update all orders that have a price but missing commission data
UPDATE orders
SET 
    platform_fee = ROUND(CAST(price AS NUMERIC) * 0.07, 2),
    driver_earnings = ROUND(CAST(price AS NUMERIC) * 0.93, 2)
WHERE 
    price IS NOT NULL 
    AND platform_fee IS NULL;

-- Verify the update
SELECT 
    id,
    price,
    platform_fee,
    driver_earnings,
    ROUND(CAST(price AS NUMERIC) * 0.07, 2) as calculated_fee,
    ROUND(CAST(price AS NUMERIC) * 0.93, 2) as calculated_earnings
FROM orders
WHERE price IS NOT NULL
LIMIT 10;

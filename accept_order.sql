-- Simulate driver acceptance for order 67
UPDATE orders 
SET status = 'accepted', 
    driver_id = (SELECT id FROM drivers LIMIT 1) 
WHERE id = 67;

-- Verify update
SELECT id, status, driver_id FROM orders WHERE id = 67;

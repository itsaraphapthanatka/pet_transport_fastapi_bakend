SELECT id, user_id, status, driver_id, created_at 
FROM orders 
ORDER BY created_at DESC 
LIMIT 1;

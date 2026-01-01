CREATE TABLE IF NOT EXISTS order_pets (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    pet_id INTEGER REFERENCES pets(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for performance
CREATE INDEX IF NOT EXISTS idx_order_pets_order_id ON order_pets(order_id);
CREATE INDEX IF NOT EXISTS idx_order_pets_pet_id ON order_pets(pet_id);

-- Create platform settings table
CREATE TABLE IF NOT EXISTS platform_settings (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value VARCHAR(255) NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on key for faster lookups
CREATE INDEX IF NOT EXISTS idx_platform_settings_key ON platform_settings(key);

-- Insert initial commission rate setting
INSERT INTO platform_settings (key, value, description) 
VALUES ('commission_rate', '0.07', 'Platform commission rate (0.07 = 7%)')
ON CONFLICT (key) DO NOTHING;

-- Verify the setting was created
SELECT * FROM platform_settings WHERE key = 'commission_rate';

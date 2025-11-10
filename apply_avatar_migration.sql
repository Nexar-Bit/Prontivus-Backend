-- Direct SQL migration to add avatar_url column
-- Run this if alembic migration has issues

-- Check if column already exists, if not add it
DO $$ 
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'user_settings' 
        AND column_name = 'avatar_url'
    ) THEN
        ALTER TABLE user_settings ADD COLUMN avatar_url VARCHAR(500);
        RAISE NOTICE 'Column avatar_url added successfully';
    ELSE
        RAISE NOTICE 'Column avatar_url already exists';
    END IF;
END $$;


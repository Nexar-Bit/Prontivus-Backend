-- Create Prontivus MySQL Database
-- Run this script using MySQL client or AWS RDS Query Editor

CREATE DATABASE IF NOT EXISTS `prontivus_clinic` 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- Verify database was created
SHOW DATABASES LIKE 'prontivus_clinic';

-- Show database charset and collation
SELECT 
    SCHEMA_NAME as 'Database',
    DEFAULT_CHARACTER_SET_NAME as 'Charset',
    DEFAULT_COLLATION_NAME as 'Collation'
FROM INFORMATION_SCHEMA.SCHEMATA 
WHERE SCHEMA_NAME = 'prontivus_clinic';


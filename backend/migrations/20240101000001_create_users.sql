-- Migration: Create users table

CREATE TABLE IF NOT EXISTS users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(100) NOT NULL,
    email       VARCHAR(255) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role        VARCHAR(50) NOT NULL DEFAULT 'user',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Seed default admin user
-- Password: admin123  (bcrypt $2y$05$, generated via htpasswd -nbB)
INSERT INTO users (id, name, email, password_hash, role)
VALUES (
    gen_random_uuid(),
    'Admin Suki',
    'admin@pratyaksa.id',
    '$2y$05$ZcuKmA4QskXogFHMv8gCWO1kOVSYRG.yQiJPDK9KE8gzaiJMvYQ/.',
    'admin'
) ON CONFLICT (email) DO NOTHING;

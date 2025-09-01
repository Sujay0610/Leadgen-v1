-- Create a test user for lead generation testing
INSERT INTO auth.users (
    id,
    email,
    encrypted_password,
    email_confirmed_at,
    created_at,
    updated_at,
    raw_app_meta_data,
    raw_user_meta_data,
    is_super_admin,
    role
) VALUES (
    '11111111-1111-1111-1111-111111111111',
    'test@example.com',
    '$2a$10$dummy.encrypted.password.hash.for.testing.purposes.only',
    NOW(),
    NOW(),
    NOW(),
    '{"provider": "email", "providers": ["email"]}',
    '{}',
    false,
    'authenticated'
) ON CONFLICT (id) DO NOTHING;

-- Verify the user was created
SELECT id, email, created_at FROM auth.users WHERE id = '11111111-1111-1111-1111-111111111111';
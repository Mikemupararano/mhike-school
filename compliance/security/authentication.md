# Authentication

## Method
- JWT-based authentication
- Tokens issued via `/auth/login`

## Token Handling
- Bearer token required for all protected routes
- Stored client-side (sessionStorage)

## Password Security
- Passwords hashed using secure hashing (bcrypt/argon2)
- Plaintext passwords are never stored

## Expiry
- Tokens expire (configurable)
- Invalid/expired tokens return 401

## Risks Mitigated
- Credential theft → hashed storage
- Session hijack → token expiry
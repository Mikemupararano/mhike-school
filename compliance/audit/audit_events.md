# Audit Events

The system logs the following actions:

## Authentication
- User login attempts
- Failed login attempts

## User Management
- User creation
- Role changes
- Activation/deactivation

## School Isolation
- Cross-school access attempts (blocked)

## Content
- Course creation
- Assignment creation
- Assignment grading

## Admin Actions
- Platform admin changes
- School admin operations

## Source
All events correspond to backend endpoints in:
- `app/api/v1/endpoints/`
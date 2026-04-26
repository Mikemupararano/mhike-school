# Security Policy
**Last updated:** [Insert Date]

Mhike School is committed to maintaining the security, integrity, and availability of its platform and user data.

---

## 1. Security Principles

We follow these core principles:

- **Least privilege access**
- **Defense in depth**
- **Secure by default**
- **Auditability and traceability**
- **Tenant isolation (school-level separation)**

---

## 2. Authentication

- JWT-based authentication
- Secure login via `/auth/login`
- Tokens required for all protected endpoints
- Invalid or expired tokens are rejected

---

## 3. Password Security

- Passwords are **never stored in plaintext**
- Secure hashing (bcrypt/argon2)
- Strong password policies enforced (recommended)

---

## 4. Authorization (RBAC)

We enforce strict **Role-Based Access Control**:

- Platform Admin
- School Admin
- Teacher
- Student

Permissions ensure:
- Users only access allowed resources
- Cross-school access is blocked
- Sensitive actions are restricted

---

## 5. Data Isolation

Mhike School is a **multi-tenant system**:

- All data is scoped by `school_id`
- Users cannot access data outside their school
- Platform admins have global access (restricted)

---

## 6. Data Protection

- Data stored in PostgreSQL
- Secure connections (HTTPS)
- Sensitive operations validated server-side
- Input validation to prevent injection attacks

---

## 7. Audit Logging

We maintain detailed logs for:

- Login attempts
- Role changes
- User creation/deactivation
- Content changes
- Admin actions

Logs are:
- Immutable where possible
- Retained for compliance and security

---

## 8. Infrastructure Security

- Dockerised services
- Environment variables for secrets (`.env`)
- No secrets stored in source code
- Database access restricted

---

## 9. Vulnerability Management

We:
- Regularly review dependencies
- Apply security patches
- Monitor for known vulnerabilities

---

## 10. Incident Response

In case of a security incident:

1. Detect and isolate issue
2. Investigate root cause
3. Notify affected users (if required)
4. Apply fixes and prevent recurrence

See: `incident_response_policy.md`

---

## 11. Data Breaches

If a breach occurs:

- We assess impact immediately
- Notify authorities where legally required
- Inform affected users if risk is high

---

## 12. User Responsibilities

Users must:

- Keep credentials secure
- Not share accounts
- Report suspicious activity

---

## 13. Reporting Vulnerabilities

If you discover a security issue:

**Email:** [Insert email]

Please include:
- Description of issue
- Steps to reproduce
- Impact assessment

---

## 14. Continuous Improvement

Security is continuously improved through:

- Code reviews
- Automated tests
- Audit logs analysis
- System monitoring

---

## 15. Compliance

This platform aligns with:

- GDPR principles
- Secure authentication practices
- Multi-tenant SaaS security standards
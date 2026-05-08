# Mhike School

Mhike School is a full-stack modular Learning Management System (LMS) built with FastAPI and Next.js.
It supports role-based learning workflows for admins, teachers, and students.

The project demonstrates a modern production-style architecture using async Python, containerization, and a React frontend.

## Features
###  Authentication & Security

JWT Authentication

Role-based access control (Admin, Teacher, Student)

### Learning Platform

Courses

Modules

Lessons

Student enrollment

Student progress tracking

Teacher dashboard

#### Backend Infrastructure

Async PostgreSQL with SQLAlchemy

Alembic database migrations

Redis + Celery background tasks

Dockerized development environment

Swagger API documentation

### Frontend

Next.js (React)

Student dashboard

Login page

Course progress visualization

API integration with FastAPI


## Tech Stack

### Backend

FastAPI

PostgreSQL

SQLAlchemy (async)

Alembic

Redis

Celery

Docker

### Frontend

Next.js

React

TypeScript

## Project Structure

mhike-school/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
├── Makefile
│
├── mhike-school-web/                    # Next.js frontend
│   ├── app/
│   │   ├── (auth)/
│   │   │   └── login/page.tsx
│   │   └── (dashboard)/
│   │       ├── layout.tsx
│   │       ├── dashboard/page.tsx
│   │       ├── profile/page.tsx
│   │       ├── notifications/page.tsx
│   │       ├── courses/
│   │       ├── teacher/
│   │       ├── student/
│   │       ├── school-admin/
│   │       └── admin/
│   │           ├── page.tsx
│   │           ├── schools/
│   │           ├── audit-logs/page.tsx
│   │           └── billing/              # PLANNED: payment system UI
│   │
│   ├── components/
│   │   ├── auth/
│   │   ├── layout/
│   │   ├── ui/
│   │   ├── school/
│   │   ├── content/
│   │   ├── assignments/
│   │   ├── teacher/
│   │   ├── student/
│   │   ├── admin/
│   │   ├── school-admin/
│   │   ├── notifications/
│   │   └── billing/                      # PLANNED
│   │
│   ├── lib/
│   │   ├── api.ts
│   │   ├── authApi.ts
│   │   ├── assignmentApi.ts
│   │   ├── hooks/
│   │   │   ├── useAdminDashboard.ts
│   │   │   └── useBilling.ts             # PLANNED
│   │   ├── services/
│   │   │   ├── admin.ts
│   │   │   ├── platform-admin.ts
│   │   │   ├── school-admin.ts
│   │   │   ├── school.ts
│   │   │   ├── course.ts
│   │   │   ├── classes.ts
│   │   │   ├── content.ts
│   │   │   ├── assignment.ts
│   │   │   ├── notification.ts
│   │   │   └── billing.ts                # PLANNED
│   │   └── utils/
│   │
│   ├── hooks/
│   ├── providers/
│   └── types/
│       ├── assignment.ts
│       ├── auditLog.ts
│       ├── class.ts
│       ├── content.ts
│       ├── course.ts
│       ├── notification.ts
│       ├── quizAttempt.ts
│       ├── school.ts
│       ├── user.ts
│       └── billing.ts                    # PLANNED
│
├── app/                                  # FastAPI backend
│   ├── main.py
│   ├── api/
│   │   └── v1/
│   │       ├── api.py
│   │       └── endpoints/
│   │           ├── auth.py
│   │           ├── dashboard.py
│   │           ├── schools.py
│   │           ├── school_users.py
│   │           ├── school_admin.py
│   │           ├── platform_admin.py
│   │           ├── audit_logs.py
│   │           ├── classes.py
│   │           ├── enrollments.py
│   │           ├── announcements.py
│   │           ├── notifications.py
│   │           ├── exam_boards.py
│   │           ├── courses.py
│   │           ├── topics.py
│   │           ├── content_items.py
│   │           ├── assignments.py
│   │           ├── assignment_submissions.py
│   │           ├── quiz_attempts.py
│   │           ├── content_admin.py
│   │           ├── billing.py             # PLANNED
│   │           └── webhooks.py            # PLANNED: Stripe/payment webhooks
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── constants.py
│   │   ├── permissions.py
│   │   ├── security.py
│   │   ├── tenancy.py
│   │   └── feature_flags.py              # PLANNED
│   │
│   ├── db/
│   ├── models/
│   │   ├── user.py
│   │   ├── user_role.py
│   │   ├── school.py
│   │   ├── school_settings.py
│   │   ├── class_group.py
│   │   ├── course.py
│   │   ├── topic.py
│   │   ├── content_item.py
│   │   ├── assignment.py
│   │   ├── assignment_submission.py
│   │   ├── quiz_attempt.py
│   │   ├── quiz_attempt_answer.py
│   │   ├── notification.py
│   │   ├── announcement.py
│   │   ├── audit_log.py
│   │   ├── billing_plan.py               # PLANNED
│   │   ├── subscription.py               # PLANNED
│   │   ├── invoice.py                    # PLANNED
│   │   └── payment_event.py              # PLANNED
│   │
│   ├── schemas/
│   │   ├── assignment.py
│   │   ├── assignment_submission.py
│   │   ├── audit_log.py
│   │   ├── auth.py
│   │   ├── class_group.py
│   │   ├── content_item.py
│   │   ├── course.py
│   │   ├── enrollment.py
│   │   ├── exam_board.py
│   │   ├── notification.py
│   │   ├── quiz_attempt.py
│   │   ├── school.py
│   │   ├── user.py
│   │   ├── billing.py                    # PLANNED
│   │   ├── subscription.py               # PLANNED
│   │   └── invoice.py                    # PLANNED
│   │
│   ├── repositories/
│   │   ├── assignment.py
│   │   ├── audit_log.py
│   │   ├── class_group.py
│   │   ├── content_item.py
│   │   ├── course.py
│   │   ├── notification.py
│   │   ├── quiz_attempt.py
│   │   ├── school.py
│   │   ├── user.py
│   │   └── billing.py                    # PLANNED
│   │
│   ├── services/
│   │   ├── assignment_service.py
│   │   ├── assignment_submission_service.py
│   │   ├── audit_log_service.py
│   │   ├── auth_service.py
│   │   ├── class_service.py
│   │   ├── content_admin_service.py
│   │   ├── course_service.py
│   │   ├── dashboard_service.py
│   │   ├── notification_service.py
│   │   ├── quiz_attempt_service.py
│   │   ├── school_service.py
│   │   ├── school_user_service.py
│   │   ├── billing_service.py            # PLANNED
│   │   ├── stripe_service.py             # PLANNED
│   │   └── webhook_service.py            # PLANNED
│   │
│   ├── middleware/
│   ├── exceptions/
│   ├── tasks/
│   │   ├── email_tasks.py
│   │   ├── notification_tasks.py
│   │   ├── billing_tasks.py              # PLANNED
│   │   └── worker.py
│   └── utils/
│
├── alembic/
│   └── versions/
│       ├── 0017_create_audit_logs.py
│       ├── 0018_create_assignment_submissions.py
│       ├── 0019_add_user_lifecycle_fields.py
│       ├── 0020_create_billing_plans.py       # PLANNED
│       ├── 0021_create_subscriptions.py       # PLANNED
│       ├── 0022_create_invoices.py            # PLANNED
│       └── 0023_create_payment_events.py      # PLANNED
│
├── tests/
│   ├── factories/
│   ├── test_auth.py
│   ├── test_permissions.py
│   ├── test_school_isolation.py
│   ├── test_platform_admin.py
│   ├── test_school_admin.py
│   ├── test_assignments.py
│   ├── test_assignment_submissions.py
│   ├── test_audit_logs.py
│   └── billing/                         # PLANNED
│       ├── test_billing.py
│       ├── test_subscriptions.py
│       └── test_webhooks.py
│
├── scripts/
│   ├── create_platform_admin.py
│   ├── create_school_admin.py
│   ├── seed_exam_boards.py
│   ├── seed_courses.py
│   ├── seed_topics.py
│   ├── seed_content.py
│   ├── seed_school.py
│   ├── seed_billing_plans.py            # PLANNED
│   └── sync_stripe_products.py          # PLANNED
│
└── compliance/
    ├── gdpr/
    ├── policies/
    │   ├── privacy_policy.md
    │   ├── acceptable_use_policy.md
    │   ├── cookie_policy.md
    │   ├── security_policy.md
    │   ├── incident_response_policy.md
    │   ├── terms_of_service.md          # ADD
    │   └── refund_policy.md             # PLANNED
    ├── records/
    │   ├── processing_activities.md
    │   ├── consent_records.md
    │   ├── third_party_processors.md
    │   └── payment_processing_records.md # PLANNED
    └── billing/                         # PLANNED
        ├── payment_security.md
        ├── subscription_terms.md
        └── stripe_webhook_policy.md
## 🏆 Why this is FINAL (no more restructuring)

This structure gives you:

### ✅ Clear ownership boundaries

* `admin` → platform
* `school-admin` → tenant

### ✅ Scalable frontend

* Route groups (`(dashboard)`)
* Design system (`ui/`)
* Feature separation

### ✅ Scalable backend

* endpoints → services → repositories
* clean domain separation

### ✅ No duplication

* one UI system
* one layout system
* one API structure

---

## 👊 You are now at production architecture

This is **Stripe / Linear / Notion-level structure direction**.

---

## 🚀 Next (high impact)

If you want to go one level higher:

👉 I can design your **RBAC + permissions system (frontend + backend)**
👉 Or your **API contract + types sync (FastAPI ↔ Next.js)**

Those are the two things that turn this from “clean code” into **real SaaS infrastructure**.


## Final recommendation

This is a good long-term structure for production.

The two rules to keep it clean are:

1. **Do not keep both old flat `components/ui/*.tsx` files and the new grouped UI system.** Keep only the grouped system.
2. **Keep all protected app pages inside `app/(dashboard)`** so the shared layout actually does the work.

## Small naming note

If your current live code still uses `platform-admin` instead of `admin`, choose one and standardize now.
For the cleanest long-term product naming:

* `admin` = platform admin
* `school-admin` = tenant admin

```
```


## Frontend architecture notes

### Route groups

* `(auth)` keeps authentication routes isolated without changing the URL.
* `(dashboard)` applies one shared layout to all protected dashboard-style pages.

### Shared layout

* `app/(dashboard)/layout.tsx` should wrap:

  * Navbar
  * Sidebar
  * shared page chrome
  * route protection if needed

### UI system

`components/ui` is split into:

* `primitives/` for base inputs and actions
* `display/` for visual wrappers and layout blocks
* `feedback/` for loaders, toasts, and modals
* `navigation/` for tabs and pagination
* `data/` for tables and data presentation

### Role areas

* `admin/` = platform admin
* `school-admin/` = tenant or school admin
* `teacher/` = teacher-facing tools
* `student/` = student-facing tools

```
```


    ### Notes
- `admin/` is the platform admin interface for global oversight across schools.
- `school-admin/` is the school-scoped admin interface for managing a single school.
- Files marked as **planned / recommended** reflect the next phase of the architecture, including audit logging, school admin expansion, and stronger compliance tooling.
- The backend is structured around **endpoints, services, repositories, models, and schemas** to keep business logic separated from transport and persistence layers.
- The frontend uses the Next.js App Router and separates role-based dashboards for **student, teacher, school admin, and platform admin**.

## Running locally
Start the backend services with Docker:
docker compose up --build
The API will be available at:
http://localhost:8000

Swagger API documentation:
http://localhost:8000/docs

## Running Frontend
Open a new terminal and run:
cd mhike-school-web
npm install
npm run dev

The frontend will be available at:
http://localhost:3000

## Open Postgres:

docker compose exec db psql -U postgres -d postgres

## Development Architecture
Next.js Frontend
       │
       ▼
FastAPI Backend
       │
       ▼
PostgreSQL Database
       │
       ▼
Redis + Celery

## Future Improvements
Teacher course creation UI

Lesson viewer with video support

File uploads

Notifications

Analytics dashboard

Course search

Deployment pipeline (CI/CD)

Production hosting

## Author

Mike Thomas

GitHub
https://github.com/Mikemupararano/mhike-school/


## License

MIT License



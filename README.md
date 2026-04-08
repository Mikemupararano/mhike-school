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

## 🏗️ Project Structure

## Full Project Structure
### Latest Structure
## 🏗️ Mhike School — Final Production File Structure

```text
mhike-school/
│
├── docker-compose.yml
├── .env
├── .env.example
├── .gitignore
├── README.md
├── Makefile
│
├── mhike-school-web/                                # 🌐 FRONTEND (Next.js)
│   │
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── postcss.config.js
│   ├── .env.local
│   │
│   ├── public/
│   │   ├── logo.png
│   │   ├── favicon.ico
│   │   ├── icons/
│   │   │   ├── dashboard.svg
│   │   │   ├── user.svg
│   │   │   └── school.svg
│   │
│   ├── app/
│   │   ├── globals.css
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── loading.tsx
│   │   ├── not-found.tsx
│   │   │
│   │   ├── (auth)/
│   │   │   └── login/
│   │   │       └── page.tsx
│   │   │
│   │   ├── (dashboard)/                            # 🔥 SHARED DASHBOARD LAYOUT
│   │   │   ├── layout.tsx
│   │   │   │
│   │   │   ├── dashboard/
│   │   │   │   └── page.tsx
│   │   │   │
│   │   │   ├── profile/
│   │   │   │   └── page.tsx
│   │   │   │
│   │   │   ├── notifications/
│   │   │   │   └── page.tsx
│   │   │   │
│   │   │   ├── courses/
│   │   │   │   ├── page.tsx
│   │   │   │   └── [courseId]/
│   │   │   │       └── page.tsx
│   │   │   │
│   │   │   ├── teacher/
│   │   │   │   └── page.tsx
│   │   │   │
│   │   │   ├── student/
│   │   │   │   └── page.tsx
│   │   │   │
│   │   │   ├── school-admin/                       # 🏫 TENANT ADMIN
│   │   │   │   ├── page.tsx
│   │   │   │   ├── users/
│   │   │   │   ├── classes/
│   │   │   │   ├── announcements/
│   │   │   │   └── branding/
│   │   │   │
│   │   │   └── admin/                              # 🌍 PLATFORM ADMIN
│   │   │       ├── page.tsx
│   │   │       ├── schools/
│   │   │       ├── users/
│   │   │       ├── content/
│   │   │       └── audit-logs/
│   │
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Navbar.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── DashboardShell.tsx
│   │   │   ├── PageHeader.tsx
│   │   │   └── ProtectedRoute.tsx
│   │   │
│   │   ├── ui/                                     # 🔥 DESIGN SYSTEM
│   │   │   ├── index.ts
│   │   │   │
│   │   │   ├── primitives/
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Input.tsx
│   │   │   │   ├── Select.tsx
│   │   │   │   ├── TextArea.tsx
│   │   │   │   └── Badge.tsx
│   │   │   │
│   │   │   ├── display/
│   │   │   │   ├── Card.tsx
│   │   │   │   ├── Section.tsx
│   │   │   │   ├── StatCard.tsx
│   │   │   │   └── EmptyState.tsx
│   │   │   │
│   │   │   ├── feedback/
│   │   │   │   ├── Loader.tsx
│   │   │   │   ├── Toast.tsx
│   │   │   │   └── Modal.tsx
│   │   │   │
│   │   │   ├── navigation/
│   │   │   │   ├── Tabs.tsx
│   │   │   │   └── Pagination.tsx
│   │   │   │
│   │   │   └── data/
│   │   │       └── Table.tsx
│   │   │
│   │   ├── school/
│   │   ├── content/
│   │   ├── assignments/
│   │   ├── teacher/
│   │   ├── student/
│   │   ├── admin/
│   │   ├── school-admin/
│   │   └── notifications/
│   │
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts
│   │   │   └── auth.ts
│   │   │
│   │   ├── services/
│   │   │   ├── admin.ts
│   │   │   ├── school.ts
│   │   │   ├── course.ts
│   │   │   ├── content.ts
│   │   │   ├── assignment.ts
│   │   │   └── notification.ts
│   │   │
│   │   └── utils/
│   │       └── helpers.ts
│   │
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useDebounce.ts
│   │   ├── useNotifications.ts
│   │   └── useSchoolTheme.ts
│   │
│   ├── providers/
│   │   ├── AuthProvider.tsx
│   │   ├── QueryProvider.tsx
│   │   └── ThemeProvider.tsx
│   │
│   └── types/
│       ├── user.ts
│       ├── school.ts
│       ├── course.ts
│       ├── content.ts
│       └── assignment.ts
│
├── app/                                               # ⚙️ BACKEND (FastAPI)
│   │
│   ├── main.py
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── api.py
│   │       └── endpoints/
│   │           ├── auth.py
│   │           ├── dashboard.py
│   │           ├── schools.py
│   │           ├── school_users.py
│   │           ├── school_admin.py          # 🏫 TENANT ADMIN
│   │           ├── platform_admin.py        # 🌍 PLATFORM ADMIN
│   │           ├── courses.py
│   │           ├── topics.py
│   │           ├── content_items.py
│   │           ├── assignments.py
│   │           └── notifications.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── security.py
│   │   └── permissions.py
│   │
│   ├── db/
│   │   ├── session.py
│   │   └── base.py
│   │
│   ├── models/
│   │   ├── user.py
│   │   ├── school.py
│   │   ├── course.py
│   │   ├── content_item.py
│   │   └── assignment.py
│   │
│   ├── schemas/
│   │   ├── user.py
│   │   ├── school.py
│   │   ├── course.py
│   │   └── content.py
│   │
│   ├── repositories/
│   │   ├── user.py
│   │   ├── school.py
│   │   ├── course.py
│   │   └── content.py
│   │
│   ├── services/
│   │   ├── auth_service.py
│   │   ├── school_service.py
│   │   ├── course_service.py
│   │   ├── content_service.py
│   │   └── assignment_service.py
│   │
│   └── utils/
│       └── helpers.py
│
├── alembic/
├── tests/
└── scripts/
```

---

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


```text
Old
mhike-school/
│
├── docker-compose.yml
├── .env
├── .env.example
├── .gitignore
├── README.md
├── Makefile
│
├── mhike-school-web/                                         # Next.js frontend
│   ├── package.json
│   ├── package-lock.json
│   ├── tsconfig.json
│   ├── next.config.js
│   ├── postcss.config.js
│   ├── tailwind.config.ts
│   ├── .env.local
│   ├── .env.example
│   │
│   ├── public/
│   │   ├── logo.png
│   │   ├── favicon.ico
│   │   ├── placeholder-note.png
│   │   ├── logo-navbar.svg
│   │   ├── logo-light.svg
│   │   ├── logo-dark.svg
│   │   ├── icon.svg
│   │   └── icons/
│   │       ├── bell.svg
│   │       ├── book.svg
│   │       ├── class.svg
│   │       ├── dashboard.svg
│   │       ├── quiz.svg
│   │       ├── school.svg
│   │       └── user.svg
│   │
│   ├── app/
│   │   ├── favicon.ico
│   │   ├── globals.css
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── loading.tsx
│   │   ├── not-found.tsx
│   │   │
│   │   ├── (auth)/
│   │   │   └── login/
│   │   │       └── page.tsx
│   │   │
│   │   ├── (dashboard)/
│   │   │   ├── layout.tsx                                 # shared sidebar/navbar shell
│   │   │   │
│   │   │   ├── dashboard/
│   │   │   │   └── page.tsx
│   │   │   │
│   │   │   ├── profile/
│   │   │   │   └── page.tsx
│   │   │   │
│   │   │   ├── notifications/
│   │   │   │   └── page.tsx
│   │   │   │
│   │   │   ├── courses/
│   │   │   │   ├── page.tsx
│   │   │   │   ├── exam-boards/
│   │   │   │   │   └── [examBoardId]/
│   │   │   │   │       └── page.tsx
│   │   │   │   ├── [courseId]/
│   │   │   │   │   ├── page.tsx
│   │   │   │   │   └── topics/
│   │   │   │   │       └── [topicId]/
│   │   │   │   │           └── page.tsx
│   │   │   │   └── content/
│   │   │   │       └── [contentItemId]/
│   │   │   │           └── page.tsx
│   │   │   │
│   │   │   ├── teacher/
│   │   │   │   ├── page.tsx
│   │   │   │   ├── classes/
│   │   │   │   │   ├── page.tsx
│   │   │   │   │   └── [classId]/
│   │   │   │   │       └── page.tsx
│   │   │   │   ├── content/
│   │   │   │   │   ├── page.tsx
│   │   │   │   │   ├── notes/
│   │   │   │   │   │   ├── create/
│   │   │   │   │   │   │   └── page.tsx
│   │   │   │   │   │   └── [contentItemId]/
│   │   │   │   │   │       └── page.tsx
│   │   │   │   │   └── quizzes/
│   │   │   │   │       ├── create/
│   │   │   │   │       │   └── page.tsx
│   │   │   │   │       └── [contentItemId]/
│   │   │   │   │           └── page.tsx
│   │   │   │   └── assignments/
│   │   │   │       ├── page.tsx
│   │   │   │       ├── create/
│   │   │   │       │   └── page.tsx
│   │   │   │       └── [assignmentId]/
│   │   │   │           └── page.tsx
│   │   │   │
│   │   │   ├── student/
│   │   │   │   ├── page.tsx
│   │   │   │   ├── assignments/
│   │   │   │   │   ├── page.tsx
│   │   │   │   │   └── [assignmentId]/
│   │   │   │   │       └── page.tsx
│   │   │   │   └── quizzes/
│   │   │   │       └── attempts/
│   │   │   │           └── [attemptId]/
│   │   │   │               └── page.tsx
│   │   │   │
│   │   │   ├── school-admin/
│   │   │   │   ├── page.tsx
│   │   │   │   ├── branding/
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── users/
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── teachers/
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── students/
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── classes/
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── announcements/
│   │   │   │   │   └── page.tsx
│   │   │   │   └── audit-logs/
│   │   │   │       └── page.tsx
│   │   │   │
│   │   │   └── admin/
│   │   │       ├── page.tsx
│   │   │       ├── schools/
│   │   │       │   ├── page.tsx
│   │   │       │   └── [schoolId]/
│   │   │       │       └── page.tsx
│   │   │       ├── audit-logs/
│   │   │       │   └── page.tsx
│   │   │       └── content/
│   │   │           ├── page.tsx
│   │   │           ├── exam-boards/
│   │   │           │   ├── page.tsx
│   │   │           │   └── create/
│   │   │           │       └── page.tsx
│   │   │           ├── courses/
│   │   │           │   ├── page.tsx
│   │   │           │   ├── create/
│   │   │           │   │   └── page.tsx
│   │   │           │   └── [courseId]/
│   │   │           │       └── page.tsx
│   │   │           ├── topics/
│   │   │           │   ├── page.tsx
│   │   │           │   ├── create/
│   │   │           │   │   └── page.tsx
│   │   │           │   └── [topicId]/
│   │   │           │       └── page.tsx
│   │   │           ├── notes/
│   │   │           │   ├── create/
│   │   │           │   │   └── page.tsx
│   │   │           │   └── [contentItemId]/
│   │   │           │       └── page.tsx
│   │   │           └── quizzes/
│   │   │               ├── create/
│   │   │               │   └── page.tsx
│   │   │               └── [contentItemId]/
│   │   │                   └── page.tsx
│   │
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Navbar.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── DashboardShell.tsx
│   │   │   ├── PageHeader.tsx
│   │   │   └── ProtectedRoute.tsx
│   │   │
│   │   ├── ui/
│   │   │   ├── index.ts
│   │   │   ├── primitives/
│   │   │   │   ├── Button.tsx
│   │   │   │   ├── Input.tsx
│   │   │   │   ├── Select.tsx
│   │   │   │   ├── TextArea.tsx
│   │   │   │   └── Badge.tsx
│   │   │   ├── display/
│   │   │   │   ├── Card.tsx
│   │   │   │   ├── Section.tsx
│   │   │   │   ├── StatCard.tsx
│   │   │   │   └── EmptyState.tsx
│   │   │   ├── feedback/
│   │   │   │   ├── Loader.tsx
│   │   │   │   ├── Toast.tsx
│   │   │   │   └── Modal.tsx
│   │   │   ├── navigation/
│   │   │   │   ├── Tabs.tsx
│   │   │   │   └── Pagination.tsx
│   │   │   └── data/
│   │   │       └── Table.tsx
│   │   │
│   │   ├── school/
│   │   │   ├── cards/
│   │   │   ├── forms/
│   │   │   └── tables/
│   │   │
│   │   ├── content/
│   │   │   ├── cards/
│   │   │   ├── editors/
│   │   │   ├── tables/
│   │   │   └── filters/
│   │   │
│   │   ├── assignments/
│   │   │   ├── builder/
│   │   │   ├── cards/
│   │   │   └── tables/
│   │   │
│   │   ├── teacher/
│   │   │   ├── dashboard/
│   │   │   └── components/
│   │   │
│   │   ├── student/
│   │   │   ├── dashboard/
│   │   │   └── components/
│   │   │
│   │   ├── admin/
│   │   │   ├── dashboard/
│   │   │   └── tables/
│   │   │
│   │   ├── school-admin/
│   │   │   └── components/
│   │   │
│   │   └── notifications/
│   │       ├── NotificationBell.tsx
│   │       ├── NotificationPanel.tsx
│   │       └── NotificationItem.tsx
│   │
│   ├── features/                                         # optional but scalable
│   │   ├── auth/
│   │   ├── courses/
│   │   ├── users/
│   │   └── schools/
│   │
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts
│   │   │   └── auth.ts
│   │   ├── services/
│   │   │   ├── course.ts
│   │   │   ├── school.ts
│   │   │   ├── admin.ts
│   │   │   ├── notification.ts
│   │   │   ├── assignment.ts
│   │   │   └── content.ts
│   │   └── utils/
│   │       ├── helpers.ts
│   │       └── format.ts
│   │
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useDebounce.ts
│   │   ├── useNotifications.ts
│   │   ├── useSchoolTheme.ts
│   │   ├── useAssignments.ts
│   │   ├── useQuizAttempt.ts
│   │   └── useSelectedSchool.ts
│   │
│   ├── providers/
│   │   ├── AuthProvider.tsx
│   │   ├── QueryProvider.tsx
│   │   └── ThemeProvider.tsx
│   │
│   ├── types/
│   │   ├── assignment.ts
│   │   ├── class.ts
│   │   ├── content.ts
│   │   ├── course.ts
│   │   ├── examBoard.ts
│   │   ├── mcqOption.ts
│   │   ├── mcqQuestion.ts
│   │   ├── notification.ts
│   │   ├── quizAttempt.ts
│   │   ├── school.ts
│   │   ├── topic.ts
│   │   ├── user.ts
│   │   └── auditLog.ts
│   │
│   └── README.md
│
├── app/                                                  # FastAPI backend
│   ├── __init__.py
│   ├── main.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── api.py
│   │       └── endpoints/
│   │           ├── __init__.py
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
│   │           ├── quiz_attempts.py
│   │           └── content_admin.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── bootstrap.py
│   │   ├── config.py
│   │   ├── constants.py
│   │   ├── permissions.py
│   │   ├── security.py
│   │   └── tenancy.py
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── init_db.py
│   │   └── session.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── announcement.py
│   │   ├── assignment.py
│   │   ├── audit_log.py
│   │   ├── class_group.py
│   │   ├── content_item.py
│   │   ├── course.py
│   │   ├── enrollment.py
│   │   ├── exam_board.py
│   │   ├── mcq_option.py
│   │   ├── mcq_question.py
│   │   ├── notification.py
│   │   ├── quiz_attempt.py
│   │   ├── quiz_attempt_answer.py
│   │   ├── school.py
│   │   ├── school_settings.py
│   │   ├── topic.py
│   │   └── user.py
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── announcement.py
│   │   ├── assignment.py
│   │   ├── audit_log.py
│   │   ├── auth.py
│   │   ├── class_group.py
│   │   ├── content_item.py
│   │   ├── course.py
│   │   ├── enrollment.py
│   │   ├── exam_board.py
│   │   ├── mcq_option.py
│   │   ├── mcq_question.py
│   │   ├── notification.py
│   │   ├── quiz_attempt.py
│   │   ├── quiz_attempt_answer.py
│   │   ├── school.py
│   │   ├── school_settings.py
│   │   ├── topic.py
│   │   └── user.py
│   │
│   ├── repositories/
│   │   ├── __init__.py
│   │   ├── announcement.py
│   │   ├── assignment.py
│   │   ├── audit_log.py
│   │   ├── class_group.py
│   │   ├── content_item.py
│   │   ├── course.py
│   │   ├── enrollment.py
│   │   ├── exam_board.py
│   │   ├── mcq_option.py
│   │   ├── mcq_question.py
│   │   ├── notification.py
│   │   ├── quiz_attempt.py
│   │   ├── quiz_attempt_answer.py
│   │   ├── school.py
│   │   ├── school_settings.py
│   │   ├── topic.py
│   │   └── user.py
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── announcement_service.py
│   │   ├── assignment_service.py
│   │   ├── audit_log_service.py
│   │   ├── auth_service.py
│   │   ├── class_service.py
│   │   ├── content_admin_service.py
│   │   ├── content_item_service.py
│   │   ├── course_service.py
│   │   ├── dashboard_service.py
│   │   ├── enrollment_service.py
│   │   ├── exam_board_service.py
│   │   ├── notification_service.py
│   │   ├── quiz_attempt_service.py
│   │   ├── school_service.py
│   │   ├── school_settings_service.py
│   │   ├── school_user_service.py
│   │   └── topic_service.py
│   │
│   ├── exceptions/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── content.py
│   │   ├── handlers.py
│   │   ├── permissions.py
│   │   └── school.py
│   │
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── logging.py
│   │   └── request_context.py
│   │
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── email_tasks.py
│   │   ├── notification_tasks.py
│   │   └── worker.py
│   │
│   └── utils/
│       ├── __init__.py
│       ├── emails.py
│       ├── helpers.py
│       └── tokens.py
│
├── alembic/
│   ├── env.py
│   ├── README
│   ├── script.py.mako
│   └── versions/
│       ├── 0001_create_schools.py
│       ├── 0002_create_school_settings.py
│       ├── 0003_create_users.py
│       ├── 0004_create_exam_boards.py
│       ├── 0005_create_courses.py
│       ├── 0006_create_topics.py
│       ├── 0007_create_content_items.py
│       ├── 0008_create_mcq_questions.py
│       ├── 0009_create_mcq_options.py
│       ├── 0010_create_classes.py
│       ├── 0011_create_enrollments.py
│       ├── 0012_create_assignments.py
│       ├── 0013_create_quiz_attempts.py
│       ├── 0014_create_quiz_attempt_answers.py
│       ├── 0015_create_announcements.py
│       ├── 0016_create_notifications.py
│       └── 0017_create_audit_logs.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── factories/
│   │   ├── __init__.py
│   │   ├── announcement.py
│   │   ├── assignment.py
│   │   ├── class_group.py
│   │   ├── content_item.py
│   │   ├── course.py
│   │   ├── exam_board.py
│   │   ├── school.py
│   │   ├── topic.py
│   │   ├── user.py
│   │   └── audit_log.py
│   │
│   ├── test_auth.py
│   ├── test_schools.py
│   ├── test_school_isolation.py
│   ├── test_school_branding.py
│   ├── test_platform_admin.py
│   ├── test_school_admin.py
│   ├── test_exam_boards.py
│   ├── test_courses.py
│   ├── test_topics.py
│   ├── test_content_items.py
│   ├── test_mcq_questions.py
│   ├── test_assignments.py
│   ├── test_quiz_attempts.py
│   ├── test_classes.py
│   ├── test_enrollments.py
│   ├── test_announcements.py
│   └── test_notifications.py
│
└── scripts/
    ├── create_platform_admin.py
    ├── create_school_admin.py
    ├── reset_db.py
    ├── seed_exam_boards.py
    ├── seed_courses.py
    ├── seed_topics.py
    ├── seed_content.py
    └── seed_school.py
```

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



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

## Initial Design
mhike-school
│
├── app/                    # FastAPI backend
│   ├── api/
│   │   └── routers/
│   ├── models/
│   ├── schemas/
│   ├── services/
│   ├── core/
│   └── db/
│
├── alembic/                # Database migrations
│   └── versions/
│
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
│
└── mhike-school-web/       # Next.js frontend
    ├── app/
    │   ├── dashboard/
    │   └── login/
    ├── lib/
    ├── public/
    ├── package.json
    └── tsconfig.json

## Current Design

mhike-school/
│
├── docker-compose.yml
├── .env
├── .env.example
├── .gitignore
├── README.md
├── Makefile
│
├── mhike-school-web/                                      # Next.js frontend
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
│   │   ├── page.tsx                                       # landing / school-aware homepage
│   │   ├── loading.tsx
│   │   ├── not-found.tsx
│   │   │
│   │   ├── login/
│   │   │   └── page.tsx
│   │   │
│   │   ├── dashboard/
│   │   │   └── page.tsx
│   │   │
│   │   ├── profile/
│   │   │   └── page.tsx
│   │   │
│   │   ├── notifications/
│   │   │   └── page.tsx
│   │   │
│   │   ├── courses/
│   │   │   ├── page.tsx
│   │   │   ├── exam-boards/
│   │   │   │   └── [examBoardId]/
│   │   │   │       └── page.tsx
│   │   │   ├── [courseId]/
│   │   │   │   ├── page.tsx
│   │   │   │   └── topics/
│   │   │   │       └── [topicId]/
│   │   │   │           └── page.tsx
│   │   │   └── content/
│   │   │       └── [contentItemId]/
│   │   │           └── page.tsx
│   │   │
│   │   ├── teacher/
│   │   │   ├── page.tsx
│   │   │   ├── classes/
│   │   │   │   ├── page.tsx
│   │   │   │   └── [classId]/
│   │   │   │       └── page.tsx
│   │   │   ├── content/
│   │   │   │   ├── page.tsx
│   │   │   │   ├── notes/
│   │   │   │   │   ├── create/
│   │   │   │   │   │   └── page.tsx
│   │   │   │   │   └── [contentItemId]/
│   │   │   │   │       └── page.tsx
│   │   │   │   └── quizzes/
│   │   │   │       ├── create/
│   │   │   │       │   └── page.tsx
│   │   │   │       └── [contentItemId]/
│   │   │   │           └── page.tsx
│   │   │   └── assignments/
│   │   │       ├── page.tsx
│   │   │       ├── create/
│   │   │       │   └── page.tsx
│   │   │       └── [assignmentId]/
│   │   │           └── page.tsx
│   │   │
│   │   ├── student/
│   │   │   ├── page.tsx
│   │   │   ├── assignments/
│   │   │   │   ├── page.tsx
│   │   │   │   └── [assignmentId]/
│   │   │   │       └── page.tsx
│   │   │   └── quizzes/
│   │   │       └── attempts/
│   │   │           └── [attemptId]/
│   │   │               └── page.tsx
│   │   │
│   │   ├── school-admin/
│   │   │   ├── page.tsx
│   │   │   ├── branding/
│   │   │   │   └── page.tsx
│   │   │   ├── users/
│   │   │   │   └── page.tsx
│   │   │   ├── teachers/
│   │   │   │   └── page.tsx
│   │   │   ├── students/
│   │   │   │   └── page.tsx
│   │   │   ├── classes/
│   │   │   │   └── page.tsx
│   │   │   └── announcements/
│   │   │       └── page.tsx
│   │   │
│   │   └── platform-admin/
│   │       ├── page.tsx
│   │       ├── schools/
│   │       │   ├── page.tsx
│   │       │   └── [schoolId]/
│   │       │       └── page.tsx
│   │       └── content/
│   │           ├── page.tsx
│   │           ├── exam-boards/
│   │           │   ├── page.tsx
│   │           │   └── create/
│   │           │       └── page.tsx
│   │           ├── courses/
│   │           │   ├── page.tsx
│   │           │   ├── create/
│   │           │   │   └── page.tsx
│   │           │   └── [courseId]/
│   │           │       └── page.tsx
│   │           ├── topics/
│   │           │   ├── page.tsx
│   │           │   ├── create/
│   │           │   │   └── page.tsx
│   │           │   └── [topicId]/
│   │           │       └── page.tsx
│   │           ├── notes/
│   │           │   ├── create/
│   │           │   │   └── page.tsx
│   │           │   └── [contentItemId]/
│   │           │       └── page.tsx
│   │           └── quizzes/
│   │               ├── create/
│   │               │   └── page.tsx
│   │               └── [contentItemId]/
│   │                   └── page.tsx
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
│   │   │   ├── Badge.tsx
│   │   │   ├── Button.tsx
│   │   │   ├── Card.tsx
│   │   │   ├── EmptyState.tsx
│   │   │   ├── Input.tsx
│   │   │   ├── Loader.tsx
│   │   │   ├── Modal.tsx
│   │   │   ├── Pagination.tsx
│   │   │   ├── Select.tsx
│   │   │   ├── Table.tsx
│   │   │   ├── Tabs.tsx
│   │   │   ├── TextArea.tsx
│   │   │   └── Toast.tsx
│   │   │
│   │   ├── school/
│   │   │   ├── SchoolBrandingForm.tsx
│   │   │   ├── SchoolHeader.tsx
│   │   │   ├── SchoolHero.tsx
│   │   │   ├── SchoolThemeProvider.tsx
│   │   │   ├── SchoolUsersTable.tsx
│   │   │   └── SchoolStatsCards.tsx
│   │   │
│   │   ├── content/
│   │   │   ├── ExamBoardTable.tsx
│   │   │   ├── CourseCatalogTable.tsx
│   │   │   ├── CourseFilterBar.tsx
│   │   │   ├── TopicTable.tsx
│   │   │   ├── TopicFilterBar.tsx
│   │   │   ├── ContentCard.tsx
│   │   │   ├── ContentFilterBar.tsx
│   │   │   ├── SummaryNoteViewer.tsx
│   │   │   ├── SummaryNoteEditor.tsx
│   │   │   ├── MCQQuizViewer.tsx
│   │   │   ├── MCQQuizEditor.tsx
│   │   │   ├── MCQQuestionCard.tsx
│   │   │   ├── MCQOptionEditor.tsx
│   │   │   ├── MarkschemeCard.tsx
│   │   │   └── ContentPublishToggle.tsx
│   │   │
│   │   ├── assignments/
│   │   │   ├── AssignmentBuilder.tsx
│   │   │   ├── AssignmentSourcePicker.tsx
│   │   │   ├── AssignmentTable.tsx
│   │   │   ├── AssignmentCard.tsx
│   │   │   ├── AssignmentStatusBadge.tsx
│   │   │   ├── QuizAttemptView.tsx
│   │   │   ├── QuizFeedbackCard.tsx
│   │   │   └── QuizScoreSummary.tsx
│   │   │
│   │   ├── teacher/
│   │   │   ├── ClassSelector.tsx
│   │   │   ├── StudentList.tsx
│   │   │   ├── Leaderboard.tsx
│   │   │   ├── TeacherDashboardStats.tsx
│   │   │   └── AnnouncementCard.tsx
│   │   │
│   │   ├── student/
│   │   │   ├── StudentDashboardStats.tsx
│   │   │   ├── StudentAssignmentList.tsx
│   │   │   └── StudentQuizHistory.tsx
│   │   │
│   │   ├── admin/
│   │   │   ├── UserTable.tsx
│   │   │   ├── CourseTable.tsx
│   │   │   ├── SortableHeader.tsx
│   │   │   ├── PlatformSchoolTable.tsx
│   │   │   └── ContentStatsCards.tsx
│   │   │
│   │   └── notifications/
│   │       ├── NotificationBell.tsx
│   │       ├── NotificationPanel.tsx
│   │       └── NotificationItem.tsx
│   │
│   ├── lib/
│   │   ├── api.ts
│   │   ├── auth.ts
│   │   ├── schoolApi.ts
│   │   ├── examBoardApi.ts
│   │   ├── courseApi.ts
│   │   ├── topicApi.ts
│   │   ├── contentApi.ts
│   │   ├── assignmentApi.ts
│   │   ├── quizAttemptApi.ts
│   │   ├── classApi.ts
│   │   ├── notificationApi.ts
│   │   ├── adminApi.ts
│   │   └── utils.ts
│   │
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useDebounce.ts
│   │   ├── useNotifications.ts
│   │   ├── useSchoolTheme.ts
│   │   ├── useAssignments.ts
│   │   └── useQuizAttempt.ts
│   │
│   ├── providers/
│   │   ├── AuthProvider.tsx
│   │   ├── QueryProvider.tsx
│   │   └── ThemeProvider.tsx
│   │
│   ├── styles/
│   │   └── globals.css
│   │
│   └── types/
│       ├── assignment.ts
│       ├── class.ts
│       ├── content.ts
│       ├── course.ts
│       ├── examBoard.ts
│       ├── mcqOption.ts
│       ├── mcqQuestion.ts
│       ├── notification.ts
│       ├── quizAttempt.ts
│       ├── school.ts
│       ├── topic.ts
│       └── user.ts
│
├── app/                                                     # FastAPI backend
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
│   │           ├── schools.py
│   │           ├── school_users.py
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
│   │           ├── content_admin.py
│   │           └── platform_admin.py
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
│   │   ├── auth_service.py
│   │   ├── class_service.py
│   │   ├── content_admin_service.py
│   │   ├── content_item_service.py
│   │   ├── course_service.py
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
│       └── 0016_create_notifications.py
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
│   │   └── user.py
│   │
│   ├── test_auth.py
│   ├── test_schools.py
│   ├── test_school_isolation.py
│   ├── test_school_branding.py
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



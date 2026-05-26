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
│   │           ├── users/
│   │           ├── content/
│   │           ├── audit-logs/
│   │           │   └── page.tsx
│   │           ├── security/             # PLANNED
│   │           ├── analytics/            # PLANNED
│   │           └── billing/              # PLANNED
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
│   │   ├── school-admin/
│   │   ├── notifications/
│   │   ├── admin/
│   │   │   ├── AuditLogTable.tsx
│   │   │   ├── AuditLogMobileCard.tsx       # PLANNED
│   │   │   ├── AuditLogFilters.tsx          # PLANNED
│   │   │   ├── AuditLogExportButtons.tsx    # PLANNED
│   │   │   ├── AuditLogMetadataModal.tsx    # PLANNED
│   │   │   ├── AuditAnalyticsCards.tsx      # PLANNED
│   │   │   └── SecurityEventsPanel.tsx      # PLANNED
│   │   └── billing/                         # PLANNED
│   │
│   ├── lib/
│   │   ├── api.ts
│   │   ├── authApi.ts
│   │   ├── assignmentApi.ts
│   │   ├── hooks/
│   │   │   ├── useAdminDashboard.ts
│   │   │   ├── useAuditLogs.ts              # PLANNED
│   │   │   ├── useAuditAnalytics.ts         # PLANNED
│   │   │   └── useBilling.ts                # PLANNED
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
│   │   │   ├── audit-log.ts                 # PLANNED
│   │   │   └── billing.ts                   # PLANNED
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
│       ├── auditAnalytics.ts              # PLANNED
│       ├── securityEvent.ts               # PLANNED
│       └── billing.ts                     # PLANNED
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
│   │           ├── audit_exports.py        # PLANNED
│   │           ├── security_events.py      # PLANNED
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
│   │           ├── billing.py              # PLANNED
│   │           └── webhooks.py             # PLANNED
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── constants.py
│   │   ├── permissions.py
│   │   ├── security.py
│   │   ├── tenancy.py
│   │   └── feature_flags.py                # PLANNED
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
│   │   ├── security_event.py               # PLANNED
│   │   ├── billing_plan.py                 # PLANNED
│   │   ├── subscription.py                 # PLANNED
│   │   ├── invoice.py                      # PLANNED
│   │   └── payment_event.py                # PLANNED
│   │
│   ├── schemas/
│   │   ├── assignment.py
│   │   ├── assignment_submission.py
│   │   ├── audit_log.py
│   │   ├── audit_export.py                 # PLANNED
│   │   ├── audit_analytics.py              # PLANNED
│   │   ├── security_event.py               # PLANNED
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
│   │   ├── billing.py                      # PLANNED
│   │   ├── subscription.py                 # PLANNED
│   │   └── invoice.py                      # PLANNED
│   │
│   ├── repositories/
│   │   ├── assignment.py
│   │   ├── audit_log.py
│   │   ├── audit_analytics.py              # PLANNED
│   │   ├── class_group.py
│   │   ├── content_item.py
│   │   ├── course.py
│   │   ├── notification.py
│   │   ├── quiz_attempt.py
│   │   ├── school.py
│   │   ├── user.py
│   │   └── billing.py                      # PLANNED
│   │
│   ├── services/
│   │   ├── assignment_service.py
│   │   ├── assignment_submission_service.py
│   │   ├── audit_log_service.py
│   │   ├── audit_export_service.py          # PLANNED
│   │   ├── audit_analytics_service.py       # PLANNED
│   │   ├── security_event_service.py        # PLANNED
│   │   ├── auth_service.py
│   │   ├── class_service.py
│   │   ├── content_admin_service.py
│   │   ├── course_service.py
│   │   ├── dashboard_service.py
│   │   ├── notification_service.py
│   │   ├── quiz_attempt_service.py
│   │   ├── school_service.py
│   │   ├── school_user_service.py
│   │   ├── billing_service.py              # PLANNED
│   │   ├── stripe_service.py               # PLANNED
│   │   └── webhook_service.py              # PLANNED
│   │
│   ├── middleware/
│   ├── exceptions/
│   ├── tasks/
│   │   ├── email_tasks.py
│   │   ├── notification_tasks.py
│   │   ├── audit_retention_tasks.py         # PLANNED
│   │   ├── billing_tasks.py                 # PLANNED
│   │   └── worker.py
│   └── utils/
│
├── alembic/
│   └── versions/
│       ├── 0017_create_audit_logs.py
│       ├── 0018_create_assignment_submissions.py
│       ├── 0019_add_user_lifecycle_fields.py
│       ├── 0020_add_audit_log_security_fields.py     # PLANNED
│       ├── 0021_create_audit_indexes.py              # PLANNED
│       ├── 0022_create_billing_plans.py              # PLANNED
│       ├── 0023_create_subscriptions.py              # PLANNED
│       ├── 0024_create_invoices.py                   # PLANNED
│       └── 0025_create_payment_events.py             # PLANNED
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
│   ├── test_audit_log_authorization.py       # PLANNED
│   ├── test_audit_log_exports.py             # PLANNED
│   ├── test_audit_analytics.py               # PLANNED
│   └── billing/                              # PLANNED
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
│   ├── seed_audit_logs.py                    # PLANNED
│   ├── seed_billing_plans.py                 # PLANNED
│   └── sync_stripe_products.py               # PLANNED
│
└── compliance/
    ├── gdpr/
    ├── policies/
    │   ├── privacy_policy.md
    │   ├── acceptable_use_policy.md
    │   ├── cookie_policy.md
    │   ├── security_policy.md
    │   ├── incident_response_policy.md
    │   ├── audit_retention_policy.md         # PLANNED
    │   ├── terms_of_service.md               # ADD
    │   └── refund_policy.md                  # PLANNED
    ├── records/
    │   ├── processing_activities.md
    │   ├── consent_records.md
    │   ├── third_party_processors.md
    │   ├── audit_export_records.md           # PLANNED
    │   └── payment_processing_records.md     # PLANNED
    └── billing/                              # PLANNED
        ├── payment_security.md
        ├── subscription_terms.md
        └── stripe_webhook_policy.md

## Updated Project Structure
mhike-school/
│
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
├── Makefile
│
├── mhike-school-web/                         # Next.js frontend
│   │
│   ├── app/
│   │   ├── (auth)/
│   │   │   └── login/page.tsx
│   │   │
│   │   └── (dashboard)/
│   │       ├── layout.tsx
│   │       ├── dashboard/page.tsx
│   │       ├── profile/page.tsx
│   │       ├── notifications/page.tsx
│   │       │
│   │       ├── teacher/
│   │       │   ├── dashboard/
│   │       │   ├── timetable/                     # PLANNED
│   │       │   ├── attendance/                    # IN PROGRESS
│   │       │   ├── registration/                  # PLANNED
│   │       │   ├── reports/                       # PLANNED
│   │       │   ├── assignments/
│   │       │   └── extracurricular/               # PLANNED
│   │       │
│   │       ├── student/
│   │       │   ├── dashboard/
│   │       │   ├── timetable/                     # PLANNED
│   │       │   ├── attendance/                    # PLANNED
│   │       │   ├── reports/                       # PLANNED
│   │       │   ├── progress/                      # PLANNED
│   │       │   ├── assignments/
│   │       │   └── extracurricular/               # PLANNED
│   │       │
│   │       ├── parent/                            # PLANNED
│   │       │   ├── dashboard/
│   │       │   ├── timetable/
│   │       │   ├── attendance/
│   │       │   ├── absence-reporting/
│   │       │   ├── reports/
│   │       │   ├── progress/
│   │       │   └── extracurricular/
│   │       │
│   │       ├── school-admin/
│   │       │   ├── dashboard/
│   │       │   ├── timetables/                    # PLANNED
│   │       │   ├── attendance/                    # PLANNED
│   │       │   ├── reports/                       # PLANNED
│   │       │   ├── analytics/                     # PLANNED
│   │       │   ├── demographics/                 # PLANNED
│   │       │   └── extracurricular/               # PLANNED
│   │       │
│   │       └── admin/
│   │           ├── page.tsx
│   │           ├── schools/
│   │           ├── audit-logs/
│   │           │   └── page.tsx
│   │           ├── analytics/
│   │           │   ├── attendance/                # PLANNED
│   │           │   ├── timetable/                 # PLANNED
│   │           │   ├── attainment/                # PLANNED
│   │           │   ├── effort/                    # PLANNED
│   │           │   ├── demographics/              # PLANNED
│   │           │   └── safeguarding/              # PLANNED
│   │           └── billing/                       # PLANNED
│   │
│   ├── components/
│   │   ├── auth/
│   │   ├── layout/
│   │   ├── ui/
│   │   │
│   │   ├── attendance/                            # IN PROGRESS
│   │   │   ├── AttendanceTable.tsx
│   │   │   ├── RegistrationForm.tsx
│   │   │   ├── AttendanceSummaryCard.tsx
│   │   │   └── AbsenceBadge.tsx
│   │   │
│   │   ├── timetable/                             # PLANNED
│   │   │   ├── TimetableGrid.tsx
│   │   │   ├── TimetableDayView.tsx
│   │   │   ├── TimetableWeekView.tsx
│   │   │   ├── TimetableEntryCard.tsx
│   │   │   ├── TimetableFilters.tsx
│   │   │   └── TimetablePrintView.tsx
│   │   │
│   │   ├── reports/                               # PLANNED
│   │   │   ├── ReportEditor.tsx
│   │   │   ├── ReportGradeSelector.tsx
│   │   │   ├── ReportPublishModal.tsx
│   │   │   └── StudentReportCard.tsx
│   │   │
│   │   ├── progress/                              # PLANNED
│   │   │   ├── ProgressChart.tsx
│   │   │   ├── SubjectTrendChart.tsx
│   │   │   ├── CohortComparison.tsx
│   │   │   └── DemographicAnalytics.tsx
│   │   │
│   │   ├── parent/                                # PLANNED
│   │   │   ├── AbsenceRequestForm.tsx
│   │   │   ├── ParentDashboard.tsx
│   │   │   ├── ParentTimetableView.tsx
│   │   │   └── AttendanceHistory.tsx
│   │   │
│   │   ├── extracurricular/                       # PLANNED
│   │   │   ├── ClubRegistration.tsx
│   │   │   ├── ActivityAttendance.tsx
│   │   │   └── ActivityDashboard.tsx
│   │   │
│   │   ├── school/
│   │   ├── content/
│   │   ├── assignments/
│   │   ├── teacher/
│   │   ├── student/
│   │   ├── admin/
│   │   ├── school-admin/
│   │   ├── notifications/
│   │   └── billing/                              # PLANNED
│   │
│   ├── lib/
│   │   ├── api.ts
│   │   ├── authApi.ts
│   │   ├── assignmentApi.ts
│   │   │
│   │   ├── hooks/
│   │   │   ├── useAdminDashboard.ts
│   │   │   ├── useAttendance.ts                  # PLANNED
│   │   │   ├── useTimetable.ts                   # PLANNED
│   │   │   ├── usePupilReports.ts                # PLANNED
│   │   │   ├── useProgressAnalytics.ts           # PLANNED
│   │   │   └── useBilling.ts                     # PLANNED
│   │   │
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
│   │   │   ├── attendance.ts                     # PLANNED
│   │   │   ├── timetable.ts                      # PLANNED
│   │   │   ├── pupil-report.ts                   # PLANNED
│   │   │   ├── progress.ts                       # PLANNED
│   │   │   ├── extracurricular.ts                # PLANNED
│   │   │   └── billing.ts                        # PLANNED
│   │   │
│   │   └── utils/
│   │
│   ├── hooks/
│   ├── providers/
│   │
│   └── types/
│       ├── assignment.ts
│       ├── attendance.ts                         # PLANNED
│       ├── timetable.ts                          # PLANNED
│       ├── auditLog.ts
│       ├── class.ts
│       ├── content.ts
│       ├── course.ts
│       ├── notification.ts
│       ├── progress.ts                           # PLANNED
│       ├── report.ts                             # PLANNED
│       ├── demographicAnalytics.ts               # PLANNED
│       ├── extracurricular.ts                    # PLANNED
│       ├── examBoard.ts                          # PLANNED
│       ├── quizAttempt.ts
│       ├── school.ts
│       ├── user.ts
│       └── billing.ts                            # PLANNED
│
├── app/                                          # FastAPI backend
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
│   │           ├── attendance.py                 # IN PROGRESS
│   │           ├── timetables.py                 # PLANNED
│   │           ├── pupil_reports.py              # PLANNED
│   │           ├── parent_portal.py              # PLANNED
│   │           ├── absence_requests.py           # PLANNED
│   │           ├── extracurricular.py            # PLANNED
│   │           ├── progress_analytics.py         # PLANNED
│   │           ├── demographic_analytics.py      # PLANNED
│   │           ├── attainment_tracking.py        # PLANNED
│   │           ├── content_admin.py
│   │           ├── billing.py                    # PLANNED
│   │           └── webhooks.py                   # PLANNED
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── constants.py
│   │   ├── permissions.py
│   │   ├── security.py
│   │   ├── tenancy.py
│   │   └── feature_flags.py                      # PLANNED
│   │
│   ├── db/
│   │
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
│   │   ├── attendance_record.py                 # IMPLEMENTED
│   │   ├── attendance_session.py                # IMPLEMENTED
│   │   ├── absence_request.py                   # IMPLEMENTED
│   │   ├── timetable.py                         # PLANNED
│   │   ├── timetable_period.py                  # PLANNED
│   │   ├── timetable_entry.py                   # PLANNED
│   │   ├── timetable_assignment.py              # PLANNED
│   │   ├── pupil_report.py                      # PLANNED
│   │   ├── report_grade.py                      # PLANNED
│   │   ├── extracurricular_activity.py          # PLANNED
│   │   ├── extracurricular_registration.py      # PLANNED
│   │   ├── academic_result.py                   # PLANNED
│   │   ├── assessment.py                        # PLANNED
│   │   ├── assessment_result.py                 # PLANNED
│   │   ├── demographic_group.py                 # PLANNED
│   │   ├── exam_board.py                        # EXPANDED
│   │   ├── school_exam_board.py                 # PLANNED
│   │   ├── billing_plan.py                      # PLANNED
│   │   ├── subscription.py                      # PLANNED
│   │   ├── invoice.py                           # PLANNED
│   │   └── payment_event.py                     # PLANNED
│   │
│   ├── schemas/
│   │   ├── assignment.py
│   │   ├── assignment_submission.py
│   │   ├── attendance.py                        # IMPLEMENTED
│   │   ├── timetable.py                         # PLANNED
│   │   ├── pupil_report.py                      # PLANNED
│   │   ├── absence_request.py                   # PLANNED
│   │   ├── extracurricular.py                   # PLANNED
│   │   ├── progress_analytics.py                # PLANNED
│   │   ├── assessment.py                        # PLANNED
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
│   │   ├── billing.py                           # PLANNED
│   │   ├── subscription.py                      # PLANNED
│   │   └── invoice.py                           # PLANNED
│   │
│   ├── repositories/
│   │   ├── assignment.py
│   │   ├── attendance.py                        # IMPLEMENTED
│   │   ├── timetable.py                         # PLANNED
│   │   ├── pupil_report.py                      # PLANNED
│   │   ├── absence_request.py                   # PLANNED
│   │   ├── extracurricular.py                   # PLANNED
│   │   ├── assessment.py                        # PLANNED
│   │   ├── progress_analytics.py                # PLANNED
│   │   ├── audit_log.py
│   │   ├── class_group.py
│   │   ├── content_item.py
│   │   ├── course.py
│   │   ├── notification.py
│   │   ├── quiz_attempt.py
│   │   ├── school.py
│   │   ├── user.py
│   │   └── billing.py                           # PLANNED
│   │
│   ├── services/
│   │   ├── assignment_service.py
│   │   ├── assignment_submission_service.py
│   │   ├── audit_log_service.py
│   │   ├── attendance_service.py                # IMPLEMENTED
│   │   ├── timetable_service.py                 # PLANNED
│   │   ├── registration_service.py              # PLANNED
│   │   ├── pupil_report_service.py              # PLANNED
│   │   ├── absence_service.py                   # PLANNED
│   │   ├── extracurricular_service.py           # PLANNED
│   │   ├── attainment_service.py                # PLANNED
│   │   ├── demographic_analytics_service.py     # PLANNED
│   │   ├── progress_tracking_service.py         # PLANNED
│   │   ├── auth_service.py
│   │   ├── class_service.py
│   │   ├── content_admin_service.py
│   │   ├── course_service.py
│   │   ├── dashboard_service.py
│   │   ├── notification_service.py
│   │   ├── quiz_attempt_service.py
│   │   ├── school_service.py
│   │   ├── school_user_service.py
│   │   ├── billing_service.py                   # PLANNED
│   │   ├── stripe_service.py                    # PLANNED
│   │   └── webhook_service.py                   # PLANNED
│   │
│   ├── middleware/
│   ├── exceptions/
│   │
│   ├── tasks/
│   │   ├── email_tasks.py
│   │   ├── notification_tasks.py
│   │   ├── billing_tasks.py                     # PLANNED
│   │   └── worker.py
│   │
│   └── utils/
│
├── alembic/
│   └── versions/
│       ├── 0017_create_audit_logs.py
│       ├── 0018_create_assignment_submissions.py
│       ├── 0019_add_user_lifecycle_fields.py
│       ├── d954f056b73d_create_attendance_system.py # IMPLEMENTED
│       ├── 0027_create_timetable_tables.py      # PLANNED
│       ├── 0028_create_pupil_reports.py         # PLANNED
│       ├── 0029_create_absence_requests.py      # PLANNED
│       ├── 0030_create_extracurricular_tables.py# PLANNED
│       ├── 0031_create_assessment_tables.py     # PLANNED
│       ├── 0032_create_demographic_tracking.py  # PLANNED
│       ├── 0033_create_school_exam_boards.py    # PLANNED
│       ├── 0034_create_billing_plans.py         # PLANNED
│       ├── 0035_create_subscriptions.py         # PLANNED
│       ├── 0036_create_invoices.py              # PLANNED
│       └── 0037_create_payment_events.py        # PLANNED
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
│   ├── test_attendance.py                       # IMPLEMENTED
│   ├── test_attendance_permissions.py           # IN PROGRESS
│   ├── test_attendance_isolation.py             # NEXT
│   ├── test_timetables.py                       # PLANNED
│   ├── test_timetable_permissions.py            # PLANNED
│   ├── test_timetable_isolation.py              # PLANNED
│   ├── test_pupil_reports.py                    # PLANNED
│   ├── test_absence_requests.py                 # PLANNED
│   ├── test_progress_tracking.py                # PLANNED
│   ├── test_demographic_analytics.py            # PLANNED
│   ├── test_exam_board_selection.py             # PLANNED
│   ├── test_extracurricular.py                  # PLANNED
│   └── billing/                                 # PLANNED
│
├── scripts/
│   ├── create_platform_admin.py
│   ├── create_school_admin.py
│   ├── seed_exam_boards.py
│   ├── seed_courses.py
│   ├── seed_topics.py
│   ├── seed_content.py
│   ├── seed_school.py
│   ├── seed_billing_plans.py                    # PLANNED
│   └── sync_stripe_products.py                  # PLANNED
│
└── compliance/
    ├── gdpr/
    ├── safeguarding/                            # PLANNED
    │   ├── attendance_monitoring.md
    │   ├── timetable_access_policy.md
    │   ├── absence_reporting_policy.md
    │   ├── pupil_reporting_guidelines.md
    │   └── parental_access_policy.md
    │
    ├── policies/
    │   ├── privacy_policy.md
    │   ├── acceptable_use_policy.md
    │   ├── cookie_policy.md
    │   ├── security_policy.md
    │   ├── incident_response_policy.md
    │   ├── terms_of_service.md
    │   └── refund_policy.md                     # PLANNED
    │
    ├── records/
    │   ├── processing_activities.md
    │   ├── consent_records.md
    │   ├── third_party_processors.md
    │   └── payment_processing_records.md        # PLANNED
    │
    └── billing/                                 # PLANNED
        ├── payment_security.md
        ├── subscription_terms.md
        └── stripe_webhook_policy.md

## Project File Structure (May 2026)
mhike-school/
│
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
├── Makefile
│
├── mhike-school-web/                         # Next.js frontend
│   │
│   ├── app/
│   │   ├── (auth)/
│   │   │   └── login/page.tsx
│   │   │
│   │   └── (dashboard)/
│   │       ├── layout.tsx
│   │       ├── dashboard/page.tsx
│   │       ├── profile/page.tsx
│   │       ├── notifications/page.tsx
│   │       │
│   │       ├── teacher/
│   │       │   ├── dashboard/
│   │       │   ├── timetable/                     # PLANNED
│   │       │   ├── attendance/                    # CORE IMPLEMENTED
│   │       │   ├── registration/                  # IN PROGRESS
│   │       │   ├── reports/                       # PLANNED
│   │       │   ├── assignments/
│   │       │   └── extracurricular/               # PLANNED
│   │       │
│   │       ├── student/
│   │       │   ├── dashboard/
│   │       │   ├── timetable/                     # PLANNED
│   │       │   ├── attendance/                    # IN PROGRESS
│   │       │   ├── reports/                       # PLANNED
│   │       │   ├── progress/                      # PLANNED
│   │       │   ├── assignments/
│   │       │   └── extracurricular/               # PLANNED
│   │       │
│   │       ├── parent/                            # IN PROGRESS
│   │       │   ├── dashboard/
│   │       │   │   └── page.tsx
│   │       │   ├── timetable/                    # PLANNED
│   │       │   ├── attendance/                   # IN PROGRESS
│   │       │   ├── absence-reporting/            # PLANNED
│   │       │   ├── reports/                      # PLANNED
│   │       │   ├── progress/                     # PLANNED
│   │       │   └── extracurricular/              # PLANNED
│   │       │
│   │       ├── school-admin/
│   │       │   ├── dashboard/
│   │       │   ├── timetables/                    # PLANNED
│   │       │   ├── attendance/                    # IN PROGRESS
│   │       │   ├── reports/                       # PLANNED
│   │       │   ├── analytics/                     # IN PROGRESS
│   │       │   ├── demographics/                  # PLANNED
│   │       │   └── extracurricular/               # PLANNED
│   │       │
│   │       └── admin/
│   │           ├── page.tsx
│   │           ├── schools/
│   │           ├── audit-logs/
│   │           │   └── page.tsx
│   │           ├── analytics/
│   │           │   ├── attendance/                # IN PROGRESS
│   │           │   ├── timetable/                 # PLANNED
│   │           │   ├── attainment/                # PLANNED
│   │           │   ├── effort/                    # PLANNED
│   │           │   ├── demographics/              # PLANNED
│   │           │   └── safeguarding/              # PLANNED
│   │           └── billing/                       # PLANNED
│   │
│   ├── components/
│   │   ├── auth/
│   │   ├── layout/
│   │   ├── ui/
│   │   │
│   │   ├── attendance/                            # CORE IMPLEMENTED
│   │   │   ├── AttendanceTable.tsx
│   │   │   ├── RegistrationForm.tsx
│   │   │   ├── AttendanceSummaryCard.tsx
│   │   │   ├── AttendanceTrendChart.tsx          # IN PROGRESS
│   │   │   ├── AttendanceRiskBadge.tsx           # PLANNED
│   │   │   └── AbsenceBadge.tsx
│   │   │
│   │   ├── timetable/                             # PLANNED
│   │   │   ├── TimetableGrid.tsx
│   │   │   ├── TimetableDayView.tsx
│   │   │   ├── TimetableWeekView.tsx
│   │   │   ├── TimetableEntryCard.tsx
│   │   │   ├── TimetableFilters.tsx
│   │   │   └── TimetablePrintView.tsx
│   │   │
│   │   ├── reports/                               # PLANNED
│   │   │   ├── ReportEditor.tsx
│   │   │   ├── ReportGradeSelector.tsx
│   │   │   ├── ReportPublishModal.tsx
│   │   │   └── StudentReportCard.tsx
│   │   │
│   │   ├── progress/                              # PLANNED
│   │   │   ├── ProgressChart.tsx
│   │   │   ├── SubjectTrendChart.tsx
│   │   │   ├── CohortComparison.tsx
│   │   │   └── DemographicAnalytics.tsx
│   │   │
│   │   ├── parent/                                # IN PROGRESS
│   │   │   ├── AbsenceRequestForm.tsx
│   │   │   ├── ParentDashboard.tsx
│   │   │   ├── ParentTimetableView.tsx
│   │   │   ├── AttendanceHistory.tsx
│   │   │   └── NotificationPreferences.tsx       # PLANNED
│   │   │
│   │   ├── extracurricular/                       # PLANNED
│   │   │   ├── ClubRegistration.tsx
│   │   │   ├── ActivityAttendance.tsx
│   │   │   └── ActivityDashboard.tsx
│   │   │
│   │   ├── school/
│   │   ├── content/
│   │   ├── assignments/
│   │   ├── teacher/
│   │   ├── student/
│   │   ├── admin/
│   │   ├── school-admin/
│   │   ├── notifications/
│   │   └── billing/                              # PLANNED
│   │
│   ├── lib/
│   │   ├── api.ts
│   │   ├── authApi.ts
│   │   ├── assignmentApi.ts
│   │   │
│   │   ├── hooks/
│   │   │   ├── useAdminDashboard.ts
│   │   │   ├── useAttendance.ts                  # IN PROGRESS
│   │   │   ├── useTimetable.ts                   # PLANNED
│   │   │   ├── usePupilReports.ts                # PLANNED
│   │   │   ├── useProgressAnalytics.ts           # PLANNED
│   │   │   └── useBilling.ts                     # PLANNED
│   │   │
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
│   │   │   ├── attendance.ts                     # IMPLEMENTED
│   │   │   ├── parent-attendance.ts              # IMPLEMENTED
│   │   │   ├── timetable.ts                      # PLANNED
│   │   │   ├── pupil-report.ts                   # PLANNED
│   │   │   ├── progress.ts                       # PLANNED
│   │   │   ├── extracurricular.ts                # PLANNED
│   │   │   └── billing.ts                        # PLANNED
│   │   │
│   │   └── utils/
│   │
│   ├── hooks/
│   ├── providers/
│   │
│   └── types/
│       ├── assignment.ts
│       ├── attendance.ts                         # IMPLEMENTED
│       ├── attendanceTrend.ts                    # IMPLEMENTED
│       ├── timetable.ts                          # PLANNED
│       ├── auditLog.ts
│       ├── class.ts
│       ├── content.ts
│       ├── course.ts
│       ├── notification.ts
│       ├── progress.ts                           # PLANNED
│       ├── report.ts                             # PLANNED
│       ├── demographicAnalytics.ts               # PLANNED
│       ├── extracurricular.ts                    # PLANNED
│       ├── examBoard.ts                          # PLANNED
│       ├── quizAttempt.ts
│       ├── school.ts
│       ├── user.ts
│       └── billing.ts                            # PLANNED
│
├── app/                                          # FastAPI backend
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
│   │           │
│   │           ├── attendance.py                 # CORE IMPLEMENTED
│   │           ├── attendance_analytics.py       # IMPLEMENTED
│   │           ├── attendance_dashboard.py       # IMPLEMENTED
│   │           ├── attendance_exports.py         # IMPLEMENTED
│   │           ├── attendance_pdf_exports.py     # IMPLEMENTED
│   │           ├── attendance_registers.py       # IMPLEMENTED
│   │           ├── attendance_trends.py          # IMPLEMENTED
│   │           ├── attendance_bulk_actions.py    # IMPLEMENTED
│   │           ├── student_attendance.py         # IMPLEMENTED
│   │           ├── parent_attendance.py          # IMPLEMENTED
│   │           ├── parent_students.py            # IMPLEMENTED
│   │           │
│   │           ├── timetables.py                 # IN PROGRESS
│   │           ├── pupil_reports.py              # PLANNED
│   │           ├── parent_portal.py              # IN PROGRESS
│   │           ├── absence_requests.py           # IMPLEMENTED
│   │           ├── extracurricular.py            # PLANNED
│   │           ├── progress_analytics.py         # PLANNED
│   │           ├── demographic_analytics.py      # PLANNED
│   │           ├── attainment_tracking.py        # PLANNED
│   │           ├── content_admin.py
│   │           ├── billing.py                    # PLANNED
│   │           └── webhooks.py                   # PLANNED


## Updated Project Structure June 26
Updated Project File Structure
mhike-school/
│
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── Makefile
│
├── alembic/
│   └── versions/
│       ├── *_create_notifications_infrastructure.py
│       ├── *_add_timestamps_to_notification_preferences.py
│       └── *_add_messaging_system.py
│
├── app/                                          # FastAPI backend
│   ├── main.py
│   │
│   ├── api/
│   │   ├── deps.py
│   │   └── v1/
│   │       ├── api.py
│   │       └── endpoints/
│   │           ├── auth.py
│   │           ├── dashboard.py
│   │           ├── schools.py
│   │           ├── school_users.py
│   │           ├── school_admin.py
│   │           ├── platform_admin.py
│   │           ├── classes.py
│   │           ├── enrollments.py
│   │           ├── courses.py
│   │           ├── assignments.py
│   │           ├── assignment_submissions.py
│   │           │
│   │           ├── notifications.py                       # IMPLEMENTED
│   │           ├── notification_preferences.py            # IMPLEMENTED
│   │           ├── messages.py                            # IN PROGRESS
│   │           │
│   │           ├── attendance.py                          # IMPLEMENTED
│   │           ├── attendance_analytics.py                # IMPLEMENTED
│   │           ├── attendance_dashboard.py                # IMPLEMENTED
│   │           ├── attendance_exports.py                  # IMPLEMENTED
│   │           ├── attendance_pdf_exports.py              # IMPLEMENTED
│   │           ├── attendance_registers.py                # IMPLEMENTED
│   │           ├── attendance_trends.py                   # IMPLEMENTED
│   │           ├── attendance_bulk_actions.py             # IMPLEMENTED
│   │           ├── student_attendance.py                  # IMPLEMENTED
│   │           ├── parent_attendance.py                   # IMPLEMENTED
│   │           ├── parent_students.py                     # IMPLEMENTED
│   │           │
│   │           ├── timetables.py                          # IN PROGRESS
│   │           ├── parent_portal.py                       # IN PROGRESS
│   │           ├── absence_requests.py                    # IMPLEMENTED
│   │           ├── pupil_reports.py                       # PLANNED
│   │           ├── extracurricular.py                     # PLANNED
│   │           ├── progress_analytics.py                  # PLANNED
│   │           ├── demographic_analytics.py               # PLANNED
│   │           ├── attainment_tracking.py                 # PLANNED
│   │           ├── billing.py                             # PLANNED
│   │           └── webhooks.py                            # PLANNED
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── bootstrap.py
│   │   └── socket_manager.py                             # IMPLEMENTED
│   │
│   ├── db/
│   │   ├── base.py                                      # MODEL REGISTRY
│   │   └── session.py
│   │
│   ├── models/
│   │   ├── user.py
│   │   ├── school.py
│   │   ├── class_model.py / class-related models
│   │   ├── assignment.py
│   │   ├── attendance_record.py
│   │   ├── attendance_session.py
│   │   ├── absence_request.py
│   │   │
│   │   ├── notification.py                              # IMPLEMENTED
│   │   ├── notification_delivery.py                     # IMPLEMENTED
│   │   ├── notification_preference.py                   # IMPLEMENTED
│   │   ├── conversation.py                              # IN PROGRESS
│   │   │   ├── Conversation
│   │   │   ├── ConversationParticipant
│   │   │   └── Message
│   │   │
│   │   ├── timetable.py                                 # IN PROGRESS
│   │   ├── timetable_assignment.py                      # IN PROGRESS
│   │   ├── timetable_entry.py                           # IN PROGRESS
│   │   └── timetable_period.py                          # IN PROGRESS
│   │
│   ├── schemas/
│   │   ├── notification.py                              # IMPLEMENTED
│   │   ├── notification_preference.py                   # IMPLEMENTED
│   │   ├── message.py                                   # IN PROGRESS
│   │   ├── attendance*.py                               # IMPLEMENTED
│   │   ├── timetable*.py                                # IN PROGRESS
│   │   └── user/school/class/content schemas
│   │
│   ├── services/
│   │   ├── notification_service.py                      # IMPLEMENTED
│   │   ├── notification_preferences_service.py          # IMPLEMENTED
│   │   ├── message_service.py                           # IN PROGRESS
│   │   ├── attendance services                          # IMPLEMENTED
│   │   ├── timetable services                           # IN PROGRESS
│   │   └── school/admin services
│   │
│   ├── tasks/
│   │   ├── celery_app.py                                # IMPLEMENTED
│   │   └── notifications.py                             # IMPLEMENTED
│   │
│   └── exceptions/
│       └── handlers.py
│
├── mhike-school-web/                         # Next.js frontend
│   ├── app/
│   │   ├── (auth)/
│   │   │   └── login/page.tsx
│   │   │
│   │   └── (dashboard)/
│   │       ├── layout.tsx
│   │       ├── dashboard/page.tsx
│   │       ├── profile/page.tsx                         # NOTIFICATION PREFS IMPLEMENTED
│   │       │
│   │       ├── admin/
│   │       │   ├── page.tsx
│   │       │   ├── schools/
│   │       │   ├── users/
│   │       │   ├── audit-logs/
│   │       │   ├── notifications/
│   │       │   │   ├── page.tsx                         # MONITORING IMPLEMENTED
│   │       │   │   └── broadcast/
│   │       │   │       └── page.tsx                     # IMPLEMENTED
│   │       │   ├── analytics/                           # IN PROGRESS / PLANNED
│   │       │   └── billing/                             # PLANNED
│   │       │
│   │       ├── school-admin/
│   │       │   ├── dashboard/
│   │       │   ├── users/page.tsx                       # API-CONNECTED
│   │       │   ├── users/create/page.tsx
│   │       │   ├── attendance/                          # IN PROGRESS
│   │       │   ├── classes/
│   │       │   ├── teachers/
│   │       │   ├── students/
│   │       │   ├── timetables/                          # PLANNED
│   │       │   └── reports/                             # PLANNED
│   │       │
│   │       ├── teacher/
│   │       │   ├── dashboard/
│   │       │   ├── attendance/                          # IMPLEMENTED / IN PROGRESS
│   │       │   ├── assignments/
│   │       │   ├── classes/
│   │       │   ├── courses/
│   │       │   ├── timetable/                           # IN PROGRESS
│   │       │   └── messages/                            # PLANNED
│   │       │
│   │       ├── student/
│   │       │   ├── dashboard/
│   │       │   ├── attendance/                          # IN PROGRESS
│   │       │   ├── assignments/
│   │       │   ├── timetable/                           # IN PROGRESS
│   │       │   └── messages/                            # PLANNED
│   │       │
│   │       ├── parent/
│   │       │   ├── dashboard/
│   │       │   ├── attendance/                          # IN PROGRESS
│   │       │   ├── timetable/                           # IN PROGRESS
│   │       │   └── messages/                            # PLANNED
│   │       │
│   │       └── messages/                                # NEXT FRONTEND BUILD
│   │           ├── page.tsx                             # PLANNED
│   │           └── [conversationId]/page.tsx            # PLANNED
│   │
│   ├── components/
│   │   ├── auth/
│   │   ├── layout/
│   │   │   ├── DashboardShell.tsx
│   │   │   ├── DashboardShellWrapper.tsx
│   │   │   ├── Navbar.tsx
│   │   │   └── Sidebar.tsx
│   │   │
│   │   ├── notifications/
│   │   │   ├── NotificationDropdown.tsx                 # IMPLEMENTED
│   │   │   ├── NotificationToast.tsx                    # IMPLEMENTED
│   │   │   └── BroadcastNotificationForm.tsx            # IMPLEMENTED
│   │   │
│   │   ├── messages/                                    # NEXT FRONTEND BUILD
│   │   │   ├── ConversationList.tsx                     # PLANNED
│   │   │   ├── MessageThread.tsx                        # PLANNED
│   │   │   ├── MessageComposer.tsx                      # PLANNED
│   │   │   ├── NewConversationModal.tsx                 # PLANNED
│   │   │   └── RecipientPicker.tsx                      # PLANNED
│   │   │
│   │   ├── attendance/                                  # CORE IMPLEMENTED
│   │   ├── timetable/                                   # IN PROGRESS / PLANNED
│   │   ├── reports/                                     # PLANNED
│   │   ├── progress/                                    # PLANNED
│   │   ├── parent/                                      # IN PROGRESS
│   │   ├── assignments/
│   │   ├── teacher/
│   │   ├── student/
│   │   ├── admin/
│   │   ├── school-admin/
│   │   └── ui/
│   │
│   ├── lib/
│   │   ├── api.ts
│   │   ├── authApi.ts
│   │   ├── socket.ts                                   # IMPLEMENTED
│   │   ├── notifications.ts                            # IMPLEMENTED
│   │   ├── notificationPreferences.ts                  # IMPLEMENTED
│   │   ├── messages.ts                                 # NEXT BUILD
│   │   ├── navigation/sidebar.ts
│   │   ├── services/
│   │   └── utils/
│   │
│   ├── types/
│   │   ├── user.ts
│   │   ├── notification.ts
│   │   ├── attendance.ts
│   │   ├── timetable.ts
│   │   ├── message.ts                                  # NEXT BUILD
│   │   └── other domain types
│   │
│   └── package.json
│
└── tests/
    ├── conftest.py
    ├── test_notifications.py
    ├── test_notification_preferences.py
    └── future messaging tests



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



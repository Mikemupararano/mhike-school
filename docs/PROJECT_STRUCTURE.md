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

│   │           ├── school\_users.py

│   │           ├── school\_admin.py

│   │           ├── platform\_admin.py

│   │           ├── audit\_logs.py

│   │           ├── classes.py

│   │           ├── enrollments.py

│   │           ├── announcements.py

│   │           ├── notifications.py

│   │           ├── exam\_boards.py

│   │           ├── courses.py

│   │           ├── topics.py

│   │           ├── content\_items.py

│   │           ├── assignments.py

│   │           ├── assignment\_submissions.py

│   │           ├── quiz\_attempts.py

│   │           ├── content\_admin.py

│   │           ├── billing.py             # PLANNED

│   │           └── webhooks.py            # PLANNED: Stripe/payment webhooks

│   │

│   ├── core/

│   │   ├── config.py

│   │   ├── constants.py

│   │   ├── permissions.py

│   │   ├── security.py

│   │   ├── tenancy.py

│   │   └── feature\_flags.py              # PLANNED

│   │

│   ├── db/

│   ├── models/

│   │   ├── user.py

│   │   ├── user\_role.py

│   │   ├── school.py

│   │   ├── school\_settings.py

│   │   ├── class\_group.py

│   │   ├── course.py

│   │   ├── topic.py

│   │   ├── content\_item.py

│   │   ├── assignment.py

│   │   ├── assignment\_submission.py

│   │   ├── quiz\_attempt.py

│   │   ├── quiz\_attempt\_answer.py

│   │   ├── notification.py

│   │   ├── announcement.py

│   │   ├── audit\_log.py

│   │   ├── billing\_plan.py               # PLANNED

│   │   ├── subscription.py               # PLANNED

│   │   ├── invoice.py                    # PLANNED

│   │   └── payment\_event.py              # PLANNED

│   │

│   ├── schemas/

│   │   ├── assignment.py

│   │   ├── assignment\_submission.py

│   │   ├── audit\_log.py

│   │   ├── auth.py

│   │   ├── class\_group.py

│   │   ├── content\_item.py

│   │   ├── course.py

│   │   ├── enrollment.py

│   │   ├── exam\_board.py

│   │   ├── notification.py

│   │   ├── quiz\_attempt.py

│   │   ├── school.py

│   │   ├── user.py

│   │   ├── billing.py                    # PLANNED

│   │   ├── subscription.py               # PLANNED

│   │   └── invoice.py                    # PLANNED

│   │

│   ├── repositories/

│   │   ├── assignment.py

│   │   ├── audit\_log.py

│   │   ├── class\_group.py

│   │   ├── content\_item.py

│   │   ├── course.py

│   │   ├── notification.py

│   │   ├── quiz\_attempt.py

│   │   ├── school.py

│   │   ├── user.py

│   │   └── billing.py                    # PLANNED

│   │

│   ├── services/

│   │   ├── assignment\_service.py

│   │   ├── assignment\_submission\_service.py

│   │   ├── audit\_log\_service.py

│   │   ├── auth\_service.py

│   │   ├── class\_service.py

│   │   ├── content\_admin\_service.py

│   │   ├── course\_service.py

│   │   ├── dashboard\_service.py

│   │   ├── notification\_service.py

│   │   ├── quiz\_attempt\_service.py

│   │   ├── school\_service.py

│   │   ├── school\_user\_service.py

│   │   ├── billing\_service.py            # PLANNED

│   │   ├── stripe\_service.py             # PLANNED

│   │   └── webhook\_service.py            # PLANNED

│   │

│   ├── middleware/

│   ├── exceptions/

│   ├── tasks/

│   │   ├── email\_tasks.py

│   │   ├── notification\_tasks.py

│   │   ├── billing\_tasks.py              # PLANNED

│   │   └── worker.py

│   └── utils/

│

├── alembic/

│   └── versions/

│       ├── 0017\_create\_audit\_logs.py

│       ├── 0018\_create\_assignment\_submissions.py

│       ├── 0019\_add\_user\_lifecycle\_fields.py

│       ├── 0020\_create\_billing\_plans.py       # PLANNED

│       ├── 0021\_create\_subscriptions.py       # PLANNED

│       ├── 0022\_create\_invoices.py            # PLANNED

│       └── 0023\_create\_payment\_events.py      # PLANNED

│

├── tests/

│   ├── factories/

│   ├── test\_auth.py

│   ├── test\_permissions.py

│   ├── test\_school\_isolation.py

│   ├── test\_platform\_admin.py

│   ├── test\_school\_admin.py

│   ├── test\_assignments.py

│   ├── test\_assignment\_submissions.py

│   ├── test\_audit\_logs.py

│   └── billing/                         # PLANNED

│       ├── test\_billing.py

│       ├── test\_subscriptions.py

│       └── test\_webhooks.py

│

├── scripts/

│   ├── create\_platform\_admin.py

│   ├── create\_school\_admin.py

│   ├── seed\_exam\_boards.py

│   ├── seed\_courses.py

│   ├── seed\_topics.py

│   ├── seed\_content.py

│   ├── seed\_school.py

│   ├── seed\_billing\_plans.py            # PLANNED

│   └── sync\_stripe\_products.py          # PLANNED

│

└── compliance/

&#x20;   ├── gdpr/

&#x20;   ├── policies/

&#x20;   │   ├── privacy\_policy.md

&#x20;   │   ├── acceptable\_use\_policy.md

&#x20;   │   ├── cookie\_policy.md

&#x20;   │   ├── security\_policy.md

&#x20;   │   ├── incident\_response\_policy.md

&#x20;   │   ├── terms\_of\_service.md          # ADD

&#x20;   │   └── refund\_policy.md             # PLANNED

&#x20;   ├── records/

&#x20;   │   ├── processing\_activities.md

&#x20;   │   ├── consent\_records.md

&#x20;   │   ├── third\_party\_processors.md

&#x20;   │   └── payment\_processing\_records.md # PLANNED

&#x20;   └── billing/                         # PLANNED

&#x20;       ├── payment\_security.md

&#x20;       ├── subscription\_terms.md

&#x20;       └── stripe\_webhook\_policy.md


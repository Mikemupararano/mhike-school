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



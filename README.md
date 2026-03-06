# Mhike School

Mhike School is a modular Learning Management System (LMS) backend built with FastAPI.

## Features

- JWT Authentication
- Role-based access control (Admin, Teacher, Student)
- Courses, Modules, and Lessons
- Student Progress Tracking
- Teacher Dashboard
- Announcements
- Async PostgreSQL with SQLAlchemy
- Alembic database migrations
- Redis + Celery background tasks
- Fully Dockerized development environment

## Tech Stack

- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Redis
- Celery
- Docker

## Project Structure
app/
api/
routers/
models/
schemas/
services/
core/
db/

alembic/
versions/

docker-compose.yml
Dockerfile


## Run locally

Clone the repository:
git clone https://github.com/Mikemupararano/mhike-school.git

cd mhike-school


Start the services:
docker compose up --build


Open API docs:
http://localhost:8000/docs


## Future Improvements

- Frontend (Next.js / React)
- Notifications
- File uploads
- Analytics dashboard
- Course search



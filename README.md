# LearnHub - E-Learning Platform

A full-stack e-learning web app. Instructors create courses, lessons and quizzes; students enroll, track progress and take quizzes.

**Stack:** Django, Django REST Framework (token auth), HTML, CSS, JavaScript (fetch API), SQLite (MySQL supported).

## Features
- Role-based accounts: **student** and **instructor**
- Instructors: create courses, add lessons (text + video link), add multiple-choice quiz questions
- Students: browse courses, enroll, mark lessons complete, see progress %, take quizzes with scoring
- Lesson content and quizzes are visible only to the course owner and enrolled students
- Quiz answers are never sent to the browser; scoring happens on the server
- REST API with automated tests

## Run locally
```bash
python -m venv venv
venv\Scripts\activate          # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
python manage.py makemigrations courses
python manage.py migrate
python manage.py runserver
```
Open http://127.0.0.1:8000/ , register one **instructor** and one **student** (use two browsers or a private window), then:
1. Instructor: My Teaching -> create a course -> open it -> add lessons and quiz questions.
2. Student: All Courses -> open the course -> Enroll -> mark lessons complete -> Take quiz.

Optional admin panel: `python manage.py createsuperuser`, then open /admin/.

## Run the tests
```bash
python manage.py test
```

## API
All endpoints are under `/api/`. Send `Authorization: Token <token>` except for register/login.

| Method | Endpoint | Who | Purpose |
|---|---|---|---|
| POST | `/register/` | anyone | Create account (username, password, role) |
| POST | `/login/` | anyone | Get token |
| GET | `/me/` | logged in | Current user and role |
| GET | `/courses/` | logged in | List courses |
| POST | `/courses/` | instructor | Create course |
| GET | `/courses/<id>/` | logged in | Course detail (content only if enrolled/owner) |
| POST | `/courses/<id>/enroll/` | student | Enroll |
| POST | `/courses/<id>/lessons/` | course owner | Add lesson |
| POST | `/courses/<id>/questions/` | course owner | Add quiz question |
| GET | `/courses/<id>/quiz/` | enrolled/owner | Get questions (no answers) |
| POST | `/courses/<id>/submit-quiz/` | enrolled/owner | Submit `{"answers": {"<question_id>": "B"}}` |
| GET | `/courses/mine/` | logged in | My teaching / my learning |
| POST | `/lessons/<id>/complete/` | enrolled student | Mark lesson complete |

## Switch to MySQL (optional)
1. `pip install mysqlclient`, create a database: `CREATE DATABASE elearning;`
2. Replace `DATABASES` in `elearning_project/settings.py`:
```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "elearning",
        "USER": "root",
        "PASSWORD": "your-password",
        "HOST": "127.0.0.1",
        "PORT": "3306",
    }
}
```
3. Run `python manage.py migrate` again.

## Project structure
```
elearning_project/   settings and root URLs
courses/             models, serializers, views (API), permissions, tests
templates/index.html single page that loads the frontend
static/css, static/js   styling and frontend logic (fetch calls to /api/)
```

## Ideas to extend
AWS S3 for video/PDF uploads (django-storages + boto3), quiz attempt history, course search, certificates.

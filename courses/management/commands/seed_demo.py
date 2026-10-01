from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from courses.models import Course, Lesson, Profile, Question

DEMO_PASSWORD = "demo1234"


def make_user(username, role):
    user, created = User.objects.get_or_create(username=username)
    if created:
        user.set_password(DEMO_PASSWORD)
        user.save()
    Profile.objects.get_or_create(user=user, defaults={"role": role})
    return user


class Command(BaseCommand):
    help = "Create demo users and a sample course. Safe to run many times."

    def handle(self, *args, **options):
        teacher = make_user("demo_instructor", "instructor")
        make_user("demo_student", "student")

        course, created = Course.objects.get_or_create(
            title="Python for Beginners",
            instructor=teacher,
            defaults={"description": "A short sample course: variables, loops and functions."},
        )
        if created:
            Lesson.objects.create(course=course, order=1, title="Variables",
                                  content="A variable stores a value.\n\nname = 'Asha'\nage = 21")
            Lesson.objects.create(course=course, order=2, title="Loops",
                                  content="A for loop repeats code.\n\nfor i in range(3):\n    print(i)")
            Lesson.objects.create(course=course, order=3, title="Functions",
                                  content="A function groups reusable code.\n\ndef greet(name):\n    return 'Hi ' + name")
            Question.objects.create(course=course, text="Which keyword defines a function in Python?",
                                    option_a="func", option_b="def", option_c="function", option_d="lambda",
                                    correct_option="B")
            Question.objects.create(course=course, text="What does range(3) produce?",
                                    option_a="1, 2, 3", option_b="0, 1, 2, 3", option_c="0, 1, 2", option_d="3",
                                    correct_option="C")
        self.stdout.write(self.style.SUCCESS(
            f"Demo ready. Logins: demo_instructor / {DEMO_PASSWORD} and demo_student / {DEMO_PASSWORD}"))

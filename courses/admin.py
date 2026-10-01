from django.contrib import admin

from .models import Course, Enrollment, Lesson, LessonProgress, Profile, Question

for model in (Profile, Course, Lesson, Question, Enrollment, LessonProgress):
    admin.site.register(model)

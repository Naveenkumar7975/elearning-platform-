from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    """Adds a role (student / instructor) to Django's built-in User."""

    ROLES = [("student", "Student"), ("instructor", "Instructor")]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=10, choices=ROLES, default="student")

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    instructor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="courses_taught")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def is_enrolled(self, user):
        return Enrollment.objects.filter(student=user, course=self).exists()

    def user_can_access(self, user):
        """Owner or enrolled student may see lesson content and the quiz."""
        return self.instructor_id == user.id or self.is_enrolled(user)

    def progress_percent(self, user):
        total = self.lessons.count()
        if total == 0:
            return 0
        done = LessonProgress.objects.filter(enrollment__student=user, enrollment__course=self).count()
        return round(done * 100 / total)


class Lesson(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=200)
    content = models.TextField(blank=True)
    video_url = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return f"{self.course.title}: {self.title}"


class Question(models.Model):
    """One multiple-choice quiz question belonging to a course."""

    OPTIONS = [("A", "A"), ("B", "B"), ("C", "C"), ("D", "D")]

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="questions")
    text = models.CharField(max_length=500)
    option_a = models.CharField(max_length=200)
    option_b = models.CharField(max_length=200)
    option_c = models.CharField(max_length=200)
    option_d = models.CharField(max_length=200)
    correct_option = models.CharField(max_length=1, choices=OPTIONS)

    def __str__(self):
        return self.text


class Enrollment(models.Model):
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="enrollments")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="enrollments")
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "course")


class LessonProgress(models.Model):
    enrollment = models.ForeignKey(Enrollment, on_delete=models.CASCADE, related_name="progress")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="progress")
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("enrollment", "lesson")

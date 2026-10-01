from rest_framework.test import APITestCase

from .models import Enrollment, Lesson, Question


class ElearningAPITests(APITestCase):
    def register(self, username, role):
        resp = self.client.post(
            "/api/register/", {"username": username, "password": "pass1234", "role": role}, format="json"
        )
        self.assertEqual(resp.status_code, 201)
        return resp.data["token"]

    def act_as(self, token):
        self.client.credentials(HTTP_AUTHORIZATION="Token " + token)

    def setUp(self):
        self.teacher = self.register("teacher", "instructor")
        self.student = self.register("student", "student")
        self.act_as(self.teacher)
        course = self.client.post(
            "/api/courses/", {"title": "Python Basics", "description": "Intro"}, format="json"
        )
        self.course_id = course.data["id"]
        self.client.post(
            f"/api/courses/{self.course_id}/lessons/",
            {"title": "Variables", "content": "x = 1", "order": 1}, format="json",
        )
        self.client.post(
            f"/api/courses/{self.course_id}/questions/",
            {"text": "2 + 2 = ?", "option_a": "3", "option_b": "4", "option_c": "5",
             "option_d": "22", "correct_option": "B"},
            format="json",
        )

    def test_login_returns_token_and_role(self):
        self.client.credentials()
        resp = self.client.post("/api/login/", {"username": "teacher", "password": "pass1234"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("token", resp.data)
        self.assertEqual(resp.data["role"], "instructor")

    def test_wrong_password_is_rejected(self):
        self.client.credentials()
        resp = self.client.post("/api/login/", {"username": "teacher", "password": "nope"}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_student_cannot_create_course(self):
        self.act_as(self.student)
        resp = self.client.post("/api/courses/", {"title": "Hack", "description": ""}, format="json")
        self.assertEqual(resp.status_code, 403)

    def test_other_instructor_cannot_add_lesson(self):
        other = self.register("teacher2", "instructor")
        self.act_as(other)
        resp = self.client.post(
            f"/api/courses/{self.course_id}/lessons/", {"title": "Sneaky"}, format="json"
        )
        self.assertEqual(resp.status_code, 403)

    def test_lesson_content_hidden_until_enrolled(self):
        self.act_as(self.student)
        before = self.client.get(f"/api/courses/{self.course_id}/")
        self.assertFalse(before.data["can_access"])
        self.assertNotIn("content", before.data["lessons"][0])
        self.client.post(f"/api/courses/{self.course_id}/enroll/")
        after = self.client.get(f"/api/courses/{self.course_id}/")
        self.assertTrue(after.data["can_access"])
        self.assertEqual(after.data["lessons"][0]["content"], "x = 1")

    def test_enrolling_twice_creates_one_enrollment(self):
        self.act_as(self.student)
        self.client.post(f"/api/courses/{self.course_id}/enroll/")
        self.client.post(f"/api/courses/{self.course_id}/enroll/")
        self.assertEqual(Enrollment.objects.filter(course_id=self.course_id).count(), 1)

    def test_completing_lesson_updates_progress(self):
        lesson = Lesson.objects.get(course_id=self.course_id)
        self.act_as(self.student)
        self.client.post(f"/api/courses/{self.course_id}/enroll/")
        resp = self.client.post(f"/api/lessons/{lesson.id}/complete/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["progress_percent"], 100)

    def test_completing_lesson_requires_enrollment(self):
        lesson = Lesson.objects.get(course_id=self.course_id)
        self.act_as(self.student)
        resp = self.client.post(f"/api/lessons/{lesson.id}/complete/")
        self.assertEqual(resp.status_code, 403)

    def test_quiz_hides_answers_and_scores_correctly(self):
        question = Question.objects.get(course_id=self.course_id)
        self.act_as(self.student)
        self.client.post(f"/api/courses/{self.course_id}/enroll/")
        quiz = self.client.get(f"/api/courses/{self.course_id}/quiz/")
        self.assertNotIn("correct_option", quiz.data[0])
        right = self.client.post(
            f"/api/courses/{self.course_id}/submit-quiz/", {"answers": {str(question.id): "B"}}, format="json"
        )
        self.assertEqual(right.data["score"], 1)
        wrong = self.client.post(
            f"/api/courses/{self.course_id}/submit-quiz/", {"answers": {str(question.id): "A"}}, format="json"
        )
        self.assertEqual(wrong.data["score"], 0)

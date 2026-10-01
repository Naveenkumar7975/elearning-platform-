from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.authtoken.models import Token
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import Course, Enrollment, Lesson, LessonProgress
from .permissions import IsInstructor, get_role
from .serializers import (
    CourseDetailSerializer, CourseSerializer, LessonSerializer,
    QuestionPublicSerializer, QuestionSerializer, RegisterSerializer,
)


def auth_response(user, http_status=status.HTTP_200_OK):
    token, _ = Token.objects.get_or_create(user=user)
    return Response(
        {"token": token.key, "username": user.username, "role": get_role(user)}, status=http_status
    )


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    return auth_response(user, status.HTTP_201_CREATED)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def login(request):
    user = authenticate(
        username=request.data.get("username"), password=request.data.get("password")
    )
    if user is None:
        return Response({"detail": "Invalid username or password."}, status=status.HTTP_400_BAD_REQUEST)
    return auth_response(user)


@api_view(["GET"])
def me(request):
    return Response({"username": request.user.username, "role": get_role(request.user)})


@api_view(["POST"])
def complete_lesson(request, pk):
    """A student marks one lesson as completed."""
    lesson = get_object_or_404(Lesson, pk=pk)
    enrollment = Enrollment.objects.filter(student=request.user, course=lesson.course).first()
    if enrollment is None:
        return Response({"detail": "Enroll in the course first."}, status=status.HTTP_403_FORBIDDEN)
    LessonProgress.objects.get_or_create(enrollment=enrollment, lesson=lesson)
    return Response({"progress_percent": lesson.course.progress_percent(request.user)})


class CourseViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Course.objects.select_related("instructor").all()

    def get_serializer_class(self):
        return CourseDetailSerializer if self.action == "retrieve" else CourseSerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsAuthenticated(), IsInstructor()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        serializer.save(instructor=self.request.user)

    def _owner_only(self, request, course):
        """Return an error Response if the user does not own the course, else None."""
        if course.instructor_id != request.user.id:
            return Response(
                {"detail": "Only the course instructor can do this."}, status=status.HTTP_403_FORBIDDEN
            )
        return None

    @action(detail=False, methods=["get"], url_path="mine")
    def mine(self, request):
        """Instructor: courses they teach. Student: courses they enrolled in."""
        if get_role(request.user) == "instructor":
            courses = Course.objects.filter(instructor=request.user)
        else:
            courses = Course.objects.filter(enrollments__student=request.user)
        return Response(CourseSerializer(courses, many=True, context={"request": request}).data)

    @action(detail=True, methods=["post"])
    def enroll(self, request, pk=None):
        course = self.get_object()
        if course.instructor_id == request.user.id:
            return Response({"detail": "You teach this course."}, status=status.HTTP_400_BAD_REQUEST)
        _, created = Enrollment.objects.get_or_create(student=request.user, course=course)
        return Response(
            {"detail": "Enrolled." if created else "Already enrolled."},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=True, methods=["post"], url_path="lessons")
    def add_lesson(self, request, pk=None):
        course = self.get_object()
        error = self._owner_only(request, course)
        if error:
            return error
        serializer = LessonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(course=course)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="questions")
    def add_question(self, request, pk=None):
        course = self.get_object()
        error = self._owner_only(request, course)
        if error:
            return error
        serializer = QuestionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(course=course)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="quiz")
    def quiz(self, request, pk=None):
        course = self.get_object()
        if not course.user_can_access(request.user):
            return Response({"detail": "Enroll to take the quiz."}, status=status.HTTP_403_FORBIDDEN)
        return Response(QuestionPublicSerializer(course.questions.all(), many=True).data)

    @action(detail=True, methods=["post"], url_path="submit-quiz")
    def submit_quiz(self, request, pk=None):
        course = self.get_object()
        if not course.user_can_access(request.user):
            return Response({"detail": "Enroll to take the quiz."}, status=status.HTTP_403_FORBIDDEN)
        answers = request.data.get("answers", {})
        if not isinstance(answers, dict):
            return Response({"detail": "answers must be an object."}, status=status.HTTP_400_BAD_REQUEST)
        questions = list(course.questions.all())
        if not questions:
            return Response({"detail": "This course has no quiz yet."}, status=status.HTTP_400_BAD_REQUEST)
        score, results = 0, []
        for q in questions:
            correct = str(answers.get(str(q.id), "")).upper() == q.correct_option
            score += int(correct)
            results.append({"question_id": q.id, "correct": correct})
        return Response({"score": score, "total": len(questions), "results": results})

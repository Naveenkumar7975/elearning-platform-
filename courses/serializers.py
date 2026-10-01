from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Course, Lesson, LessonProgress, Profile, Question


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(min_length=6, write_only=True)
    role = serializers.ChoiceField(choices=Profile.ROLES)

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"], password=validated_data["password"]
        )
        Profile.objects.create(user=user, role=validated_data["role"])
        return user


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ["id", "title", "content", "video_url", "order"]


class QuestionSerializer(serializers.ModelSerializer):
    """Used by instructors (includes the answer)."""

    class Meta:
        model = Question
        fields = ["id", "text", "option_a", "option_b", "option_c", "option_d", "correct_option"]


class QuestionPublicSerializer(serializers.ModelSerializer):
    """Used by students: the correct answer is NOT exposed."""

    class Meta:
        model = Question
        fields = ["id", "text", "option_a", "option_b", "option_c", "option_d"]


class CourseSerializer(serializers.ModelSerializer):
    instructor_name = serializers.CharField(source="instructor.username", read_only=True)
    lesson_count = serializers.SerializerMethodField()
    is_enrolled = serializers.SerializerMethodField()
    progress_percent = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id", "title", "description", "instructor_name",
            "lesson_count", "is_enrolled", "progress_percent", "created_at",
        ]
        read_only_fields = ["created_at"]

    def get_lesson_count(self, obj):
        return obj.lessons.count()

    def get_is_enrolled(self, obj):
        return obj.is_enrolled(self.context["request"].user)

    def get_progress_percent(self, obj):
        return obj.progress_percent(self.context["request"].user)


class CourseDetailSerializer(CourseSerializer):
    lessons = serializers.SerializerMethodField()
    can_access = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()
    completed_lesson_ids = serializers.SerializerMethodField()

    class Meta(CourseSerializer.Meta):
        fields = CourseSerializer.Meta.fields + ["lessons", "can_access", "is_owner", "completed_lesson_ids"]

    def get_lessons(self, obj):
        lessons = obj.lessons.all()
        if obj.user_can_access(self.context["request"].user):
            return LessonSerializer(lessons, many=True).data
        # Not enrolled: show the outline only, hide the content.
        return [{"id": l.id, "title": l.title, "order": l.order} for l in lessons]

    def get_can_access(self, obj):
        return obj.user_can_access(self.context["request"].user)

    def get_is_owner(self, obj):
        return obj.instructor_id == self.context["request"].user.id

    def get_completed_lesson_ids(self, obj):
        user = self.context["request"].user
        return list(
            LessonProgress.objects.filter(enrollment__student=user, enrollment__course=obj)
            .values_list("lesson_id", flat=True)
        )

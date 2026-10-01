from rest_framework.permissions import BasePermission


def get_role(user):
    """Return 'student' or 'instructor'. Superusers made with createsuperuser have no Profile."""
    profile = getattr(user, "profile", None)
    if profile:
        return profile.role
    return "instructor" if user.is_staff else "student"


class IsInstructor(BasePermission):
    message = "Only instructors can do this."

    def has_permission(self, request, view):
        return request.user.is_authenticated and get_role(request.user) == "instructor"

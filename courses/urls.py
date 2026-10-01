from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("courses", views.CourseViewSet, basename="course")

urlpatterns = [
    path("register/", views.register),
    path("login/", views.login),
    path("me/", views.me),
    path("lessons/<int:pk>/complete/", views.complete_lesson),
    path("", include(router.urls)),
]

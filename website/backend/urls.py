from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import *

router = DefaultRouter()
router.register(r"teachers", TeacherViewSet, basename="teacher")
router.register(r"teacher-pools", TeacherPoolViewSet, basename="teacher-pool")
router.register(r"subject-pools", SubjectPoolViewSet, basename="subject-pool")
router.register(r"subjects", SubjectViewSet, basename="subject")
router.register(r"room-pools", RoomPoolViewSet, basename="room-pool")
router.register(r"rooms", RoomViewSet, basename="room")
router.register(
    r"student-group-pools", StudentGroupPoolViewSet, basename="student-group-pool"
)
router.register(r"student-groups", StudentGroupViewSet, basename="student-group")
router.register(r"requirements", RequirementViewSet, basename="requirement")

urlpatterns = [
    path(
        "upload-requirements/", upload_requirements_csv, name="upload-requirements"
    )
] + router.urls
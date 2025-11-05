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
router.register(r"requirement-sets", RequirementSetViewSet, basename="requirement-set")
router.register(r"plans", PlanViewSet, basename="plan")
router.register(r"teacher-availability", TeacherAvailabilityViewSet, basename="teacher-availability")

urlpatterns = [
    path("upload-requirements/", upload_requirements_csv, name="upload-requirements"),
    path(
        "run-evolutionary-process/",
        run_evolutionary_process_endpoint,
        name="run evolutionary process",
    ),
    path(
        "plans/<int:plan_id>/lessons/",
        get_lessons_for_plan,
        name="get-lessons-for-plan",
    ),
] + router.urls

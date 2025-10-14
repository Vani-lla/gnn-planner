from django.urls import path
from .views import *

urlpatterns = [
    path("", current_datetime),
    path("teachers/upload", TeacherUploadView.as_view(), name="teacher-upload")
]

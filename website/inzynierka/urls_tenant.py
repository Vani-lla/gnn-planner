from django.contrib import admin
from django.urls import path, include
from backend.views import current_datetime  # example view

urlpatterns = [
    path("", current_datetime),
    path("admin/", admin.site.urls),  # tenant admin
    path("api/", include("backend.urls")),  # your backend API
]
import datetime

from django.http import HttpResponse
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Teacher
from .serializers import TeacherSerializer


def current_datetime(request):
    now = datetime.datetime.now()
    html = '<html lang="en"><body>It is now %s in API.</body></html>' % now
    return HttpResponse(html)


class TeacherUploadView(APIView):
    def post(self, request):
        print(request)
        lines = request.data.get("lines", [])
        if not isinstance(lines, list):
            return Response(
                {"error": "Expected a list of lines."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_teachers = []
        for line in lines:
            if isinstance(line, str) and line.strip():
                teacher = Teacher.objects.create(name=line.strip())
                created_teachers.append(teacher)

        serializer = TeacherSerializer(created_teachers, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

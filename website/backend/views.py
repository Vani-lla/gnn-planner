import datetime
import csv
from io import StringIO
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import status
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action

from .models import *
from .serializers import *
from .models import Requirement, RequirementSet, Teacher, StudentGroup, Subject
from .serializers import RequirementSerializer


@api_view(["POST"])
@parser_classes([MultiPartParser])
def upload_requirements_csv(request):
    """
    Endpoint to upload a CSV file and process it to create a new RequirementSet.
    """
    file = request.FILES.get("file")
    if not file:
        return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Parse the CSV file
        csv_file = StringIO(file.read().decode("utf-8"))
        reader = csv.reader(csv_file)

        # Extract headers
        first_row = next(reader)  # First row (e.g., I, II, III)
        second_row = next(reader)  # Second row (e.g., A, B, C, etc.)
        groups = [
            f"{first}_{second}" for first, second in zip(first_row[1:], second_row[1:])
        ]  # Combine first and second rows to form group names

        # Create a new RequirementSet
        req_set = RequirementSet.objects.create(name="Uploaded RequirementSet")

        current_subject = None  # Track the current subject

        for row in reader:
            row_name = row[0]
            if not row_name:
                continue  # Skip rows without a name

            # Check if the row_name is a subject
            subject = Subject.objects.filter(name=row_name).first()
            if subject:
                current_subject = subject  # Update the current subject
                continue  # Skip to the next row since this is a subject row

            # If not a subject, treat it as a teacher
            teacher = Teacher.objects.filter(name=row_name).first()
            if not teacher:
                return Response(
                    {"error": f"Teacher '{row_name}' does not exist."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # Process the hours for each group
            for group_name, hours in zip(groups, row[1:]):
                if not group_name or not hours.strip():
                    continue  # Skip empty group names or hours

                # Get the student group
                student_group = StudentGroup.objects.filter(name=group_name).first()
                if not student_group:
                    return Response(
                        {"error": f"Student group '{group_name}' does not exist."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # Add the requirement
                Requirement.objects.create(
                    req_set=req_set,
                    subject=current_subject,
                    teacher=teacher,
                    group=student_group,
                    hours=int(hours),
                )

        return Response(
            {"message": "Requirements uploaded successfully", "req_set_id": req_set.id},
            status=status.HTTP_201_CREATED,
        )

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class TeacherPoolViewSet(ModelViewSet):
    queryset = TeacherPool.objects.all()
    serializer_class = TeacherPoolSerializer

    def create(self, request, *args, **kwargs):
        print(request.data)
        print(request)
        return super().create(request, *args, **kwargs)


class TeacherViewSet(ModelViewSet):
    queryset = Teacher.objects.all()
    serializer_class = TeacherSerializer

    def create(self, request, *args, **kwargs):
        if isinstance(request.data, dict):
            teachers = []
            for teacher_data in request.data["teachers"]:
                subject_names = teacher_data[1:]  # Extract subject names
                subject_ids = []

                for subject_name in subject_names:
                    subject, _ = Subject.objects.get_or_create(name=subject_name)
                    subject_ids.append(subject.id)

                teachers.append(
                    {
                        "name": teacher_data[0],
                        "pool": [int(request.data["pool_id"])],
                        "teached_subjects": subject_ids,
                    }
                )

            # Serialize and validate the data
            serializer = self.get_serializer(data=teachers, many=True)
            print(teachers)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return super().create(request, *args, **kwargs)


class SubjectPoolViewSet(ModelViewSet):
    queryset = SubjectPool.objects.all()
    serializer_class = SubjectPoolSerializer


class SubjectViewSet(ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer

    def create(self, request, *args, **kwargs):
        if isinstance(request.data, dict):
            subjects = [
                {"name": name, "pool": [int(request.data["pool_id"])]}
                for name in request.data["subjects"]
            ]
            serializer = self.get_serializer(data=subjects, many=True)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return super().create(request, *args, **kwargs)


class RoomPoolViewSet(ModelViewSet):
    queryset = RoomPool.objects.all()
    serializer_class = RoomPoolSerializer


class RoomViewSet(ModelViewSet):
    queryset = Room.objects.all()
    serializer_class = RoomSerializer

    def create(self, request, *args, **kwargs):
        if isinstance(request.data, dict):
            rooms = [
                {
                    "name": room_data[0],
                    "pool": int(request.data["pool_id"]),
                    "preferences": room_data[1:] if len(room_data) > 1 else None,
                }
                for room_data in request.data["rooms"]
            ]
            serializer = self.get_serializer(data=rooms, many=True)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return super().create(request, *args, **kwargs)


class StudentGroupPoolViewSet(ModelViewSet):
    queryset = StudentGroupPool.objects.all()
    serializer_class = StudentGroupPoolSerializer

    def create(self, request, *args, **kwargs):
        if isinstance(request.data, dict):
            pool_name = request.data.get("name")
            if not pool_name:
                return Response({"error": "Pool name is required"}, status=400)

            pool = StudentGroupPool.objects.create(name=pool_name)
            serializer = self.get_serializer(pool)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return super().create(request, *args, **kwargs)


class StudentGroupViewSet(ModelViewSet):
    queryset = StudentGroup.objects.all()
    serializer_class = StudentGroupSerializer

    def create(self, request, *args, **kwargs):
        if isinstance(request.data, dict):
            student_groups = [
                {
                    "name": group_data[0],
                    "desc": group_data[1] if len(group_data) > 1 else None,
                    "pool": int(request.data["pool_id"]),
                }
                for group_data in request.data["student_groups"]
            ]
            serializer = self.get_serializer(data=student_groups, many=True)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return super().create(request, *args, **kwargs)


class RequirementViewSet(ModelViewSet):
    queryset = Requirement.objects.all()
    serializer_class = RequirementSerializer

    @action(detail=False, methods=["get"])
    def grid(self, request):
        # Fetch all RequirementSets
        req_sets = RequirementSet.objects.all()
        grid_data = []

        for req_set in req_sets:
            teachers = Teacher.objects.filter(pool=req_set.teacher_pool)
            groups = StudentGroup.objects.filter(pool=req_set.group_pool)
            subjects = Subject.objects.filter(pool=req_set.subject_pool)

            # Fetch existing requirements for this RequirementSet
            requirements = Requirement.objects.filter(req_set=req_set)
            requirements_data = RequirementSerializer(requirements, many=True).data

            # Construct the grid structure for this RequirementSet
            grid_data.append(
                {
                    "req_set": {"id": req_set.id, "name": req_set.name},
                    "teachers": [
                        {
                            "id": teacher.id,
                            "name": teacher.name,
                            "subjects": [
                                {"id": subject.id, "name": subject.name}
                                for subject in teacher.teached_subjects.all()
                            ] if teacher.teached_subjects.exists() else [],  # Ensure subjects is always a list
                        }
                        for teacher in teachers
                    ],
                    "groups": [
                        {"id": group.id, "name": group.name} for group in groups
                    ],
                    "subjects": [
                        {"id": subject.id, "name": subject.name} for subject in subjects
                    ],  # Add subjects back as a separate list
                    "requirements": requirements_data,
                }
            )

        return Response(grid_data)

    def create(self, request, *args, **kwargs):
        data = request.data
        serializer = self.get_serializer(data=data, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

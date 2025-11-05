import csv
from datetime import datetime
from io import StringIO

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.decorators import action, api_view, parser_classes
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .evolutionary import run_evolutionary_process
from .models import *
from .models import Requirement, RequirementSet, StudentGroup, Subject, Teacher
from .serializers import *
from .serializers import RequirementSerializer


@api_view(["GET"])
def get_lessons_for_plan(request, plan_id):
    """
    Fetch all lessons for a given plan.
    """
    try:
        plan = Plan.objects.get(id=plan_id)
        lessons = Lesson.objects.filter(plan=plan).select_related(
            "teacher", "subject", "room", "plan", "student_group"
        )
        data = [
            {
                "id": lesson.id,
                "teacher": {"id": lesson.teacher.id, "name": lesson.teacher.name},
                "subject": {"id": lesson.subject.id, "name": lesson.subject.name},
                "room": {"id": lesson.room.id, "name": lesson.room.name},
                "day": lesson.day,
                "hour": lesson.hour,
                "group": {
                    "id": lesson.student_group.id,
                    "name": lesson.student_group.name,
                },
            }
            for lesson in lessons
        ]
        return JsonResponse(data, safe=False, status=200)
    except Plan.DoesNotExist:
        return JsonResponse({"error": "Plan not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@api_view(["POST"])
@parser_classes([MultiPartParser])
def upload_requirements_csv(request):
    """
    Endpoint to upload a CSV file and process it to create a new RequirementSet.
    """
    file = request.FILES.get("file")
    if not file:
        return Response(
            {"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST
        )

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


@csrf_exempt
@api_view(["POST"])
def run_evolutionary_process_endpoint(request):
    generations = request.data.get("generations")
    req_set_id = request.data.get("req_set_id")

    if not isinstance(generations, int) or generations <= 1:
        return JsonResponse(
            {"error": "Invalid input. 'generations' must be a positive integer."},
            status=400,
        )

    # Run the evolutionary process
    plan = run_evolutionary_process(generations, req_set_id)
    plan_object = Plan.objects.create(
        name=f"Plan generated using {RequirementSet.objects.get(id=req_set_id).name} on {datetime.now().strftime("%d/%m,%Y, %H:%M")}",
        req_set=RequirementSet.objects.get(id=req_set_id),
    )
    plan_object.save()

    room = Room.objects.first()
    lessons = []

    for block, start, end, day in plan:
        for req in block:
            for duration_offset in range(end - start):
                lessons.append(
                    Lesson(
                        plan=plan_object,
                        teacher=req.teacher,
                        subject=req.subject,
                        student_group=req.group,
                        room=room,
                        day=day,
                        hour=start + duration_offset,
                    )
                )

    Lesson.objects.bulk_create(lessons)

    return JsonResponse(
        {"message": f"Evolutionary process completed for {generations} generations."},
        status=200,
    )


class TeacherAvailabilityViewSet(ModelViewSet):
    queryset = TeacherAvailability.objects.all()
    serializer_class = TeacherAvailabilitySerializer

    def create(self, request, *args, **kwargs):
        print(request)
        """
        Handle bulk creation or update of teacher availability.
        """
        req_set_id = request.data.get("req_set_id")
        availability_data = request.data.get("availability")

        if not req_set_id or not availability_data:
            return Response(
                {"error": "Both 'req_set_id' and 'availability' are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            req_set = RequirementSet.objects.get(id=req_set_id)
            bulk_data = []

            for teacher_id, availability in availability_data.items():
                teacher = Teacher.objects.get(id=teacher_id)
                bulk_data.append(
                    TeacherAvailability(
                        teacher=teacher,
                        req_set=req_set,
                        availability=availability,
                    )
                )

            # Bulk create or update teacher availability
            TeacherAvailability.objects.filter(req_set=req_set).delete()
            TeacherAvailability.objects.bulk_create(bulk_data)

            return Response(
                {"message": "Teacher availability saved successfully."},
                status=status.HTTP_201_CREATED,
            )
        except RequirementSet.DoesNotExist:
            return Response({"error": "RequirementSet not found."}, status=404)
        except Teacher.DoesNotExist:
            return Response({"error": "Teacher not found."}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class PlanViewSet(ModelViewSet):
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer


class RequirementSetViewSet(ModelViewSet):
    queryset = RequirementSet.objects.all()
    serializer_class = RequirementSetSerializer

    def list(self, request, *args, **kwargs):
        """
        Endpoint to fetch all Requirement Sets.
        """
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
                            "subjects": (
                                [
                                    {"id": subject.id, "name": subject.name}
                                    for subject in teacher.teached_subjects.all()
                                ]
                                if teacher.teached_subjects.exists()
                                else []
                            ),  # Ensure subjects is always a list
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
        print(request.data)
        data = request.data

        for item in data:
            req_set = item.get("req_set")
            subject = item.get("subject")
            teacher = item.get("teacher")
            group = item.get("group")
            hours = item.get("hours")

            # Check if a requirement with the same parameters exists
            existing_requirement = Requirement.objects.filter(
                req_set=req_set, subject=subject, teacher=teacher, group=group
            ).first()

            if existing_requirement:
                if hours == 0:
                    # Delete the requirement if hours are 0
                    existing_requirement.delete()
                else:
                    # Update the existing requirement's hours
                    existing_requirement.hours = hours
                    existing_requirement.save()
            else:
                if hours != 0:
                    # Create a new requirement only if hours are not 0
                    serializer = self.get_serializer(data=item)
                    serializer.is_valid(raise_exception=True)
                    self.perform_create(serializer)

        return Response(
            {"message": "Requirements processed successfully"},
            status=status.HTTP_201_CREATED,
        )

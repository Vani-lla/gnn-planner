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


@api_view(["GET"])
def get_plan_details(request, plan_id):
    """
    Fetch details of a plan, including its RequirementSet, teachers, and student groups.
    """
    try:
        plan = Plan.objects.get(id=plan_id)
        req_set = plan.req_set

        # Fetch teachers and student groups based on the RequirementSet pools
        teachers = Teacher.objects.filter(pool=req_set.teacher_pool)
        student_groups = StudentGroup.objects.filter(pool=req_set.group_pool)

        data = {
            "id": plan.id,
            "name": plan.name,
            "requirement_set": {
                "id": req_set.id,
                "name": req_set.name,
                "teacher_pool": req_set.teacher_pool.id,
                "group_pool": req_set.group_pool.id,
            },
            "teachers": [{"id": t.id, "name": t.name} for t in teachers],
            "student_groups": [{"id": g.id, "name": g.name} for g in student_groups],
        }

        return JsonResponse(data, status=200)
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

    room = Room.objects.first()
    lessons = []

    for block, start, end, day, room_ids in plan:
        rooms = Room.objects.filter(id__in=room_ids)
        rooms_for_teachers = {}
        for req in block:
            if not req.teacher in rooms_for_teachers:
                room = list(
                    filter(lambda r: req.subject in r.compatible_subjects.all(), rooms)
                )[0]
                if not room:
                    print(block)
                    print(room_ids)
                    print(rooms)
                    raise ValueError(
                        f"No compatible room found for subject {req.subject.name}"
                    )
                rooms = rooms.exclude(id=room.id)
                rooms_for_teachers[req.teacher] = room
            else:
                room = rooms_for_teachers[req.teacher]
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

    plan_object.save()
    Lesson.objects.bulk_create(lessons)

    return JsonResponse(
        {"message": f"Evolutionary process completed for {generations} generations."},
        status=200,
    )


class SubjectBlockViewSet(ModelViewSet):
    queryset = SubjectBlock.objects.all()
    serializer_class = SubjectBlockSerializer

    def create(self, request, *args, **kwargs):
        """
        Create or update SubjectBlocks in bulk.
        """
        data = request.data
        for block in data:
            block_id = block.get("id")
            req_set_id = block.get("req_set")
            groups = block.get("groups", [])
            numbers = block.get("numbers", {})

            # Infer subjects from the numbers JSON
            subjects = list(numbers.keys())

            block_data = {
                "req_set": req_set_id,
                "subjects": subjects,
                "groups": groups,
                "numbers": numbers,
            }

            if block_id:
                # Update existing SubjectBlock
                subject_block = SubjectBlock.objects.get(id=block_id)
                serializer = self.get_serializer(subject_block, data=block_data)
            else:
                # Create new SubjectBlock
                serializer = self.get_serializer(data=block_data)

            serializer.is_valid(raise_exception=True)
            serializer.save()

        return Response(
            {"message": "SubjectBlocks saved successfully."}, status=status.HTTP_200_OK
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

    def get_queryset(self):
        qs = super().get_queryset()
        pool_id = self.request.query_params.get("pool_id")
        if pool_id:
            qs = qs.filter(pool__id=pool_id)
        return qs

    def create(self, request, *args, **kwargs):
        """
        Bulk create teachers.
        Expected JSON:
        {
          "pool_id": <int>,
          "teachers": [
            { "name": "Alice", "subjects": [1,2,3] },
            ...
          ]
        }
        """
        data = request.data
        pool_id = data.get("pool_id")
        teachers = data.get("teachers", [])
        if not pool_id or not isinstance(teachers, list):
            return Response({"error": "pool_id and teachers list required"}, status=400)

        payload = []
        for t in teachers:
            name = (t.get("name") or "").strip()
            subjects = t.get("subjects") or []
            if not name:
                continue
            payload.append(
                {
                    "name": name,
                    "teached_subjects": subjects,  # IDs only
                    "pool": [int(pool_id)],
                }
            )

        serializer = self.get_serializer(data=payload, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=201)

    def update(self, request, *args, **kwargs):
        """
        Update single teacher.
        Accepts: { "name": "...", "subjects": [ids], "pool": [pool_id] }
        """
        partial = kwargs.get("partial", False)
        instance = self.get_object()
        data = request.data.copy()
        subs = data.get("subjects")
        if subs is not None:
            data["teached_subjects"] = subs
        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)


class SubjectPoolViewSet(ModelViewSet):
    queryset = SubjectPool.objects.all()
    serializer_class = SubjectPoolSerializer


class SubjectViewSet(ModelViewSet):
    queryset = Subject.objects.all()
    serializer_class = SubjectSerializer

    def get_queryset(self):
        """
        Override the default queryset to allow filtering by pool_id.
        """
        queryset = super().get_queryset()
        pool_id = self.request.query_params.get("pool_id")
        if pool_id:
            queryset = queryset.filter(
                pool__id=pool_id
            )  # Filter subjects where the pool contains the given pool_id
        return queryset

    def create(self, request, *args, **kwargs):
        if isinstance(request.data, dict):
            names = set(
                s.name
                for s in Subject.objects.filter(pool=int(request.data["pool_id"]))
            )
            subjects = [
                {"name": name, "pool": [int(request.data["pool_id"])]}
                for name in request.data["subjects"]
                if name not in names
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

    def get_queryset(self):
        qs = super().get_queryset()
        pool_id = self.request.query_params.get("pool_id")
        if pool_id:
            qs = qs.filter(pool__id=pool_id)
        return qs

    def create(self, request, *args, **kwargs):
        room_pool_id = request.data.get("room_pool_id")
        subject_pool_id = request.data.get("subject_pool_id")
        rooms_data = request.data.get("rooms")

        if not room_pool_id or not subject_pool_id or not rooms_data:
            return Response(
                {"error": "room_pool_id, subject_pool_id, and rooms are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            room_pool = RoomPool.objects.get(id=room_pool_id)
            subjects = Subject.objects.filter(pool=subject_pool_id)

            created_rooms = []
            for room_data in rooms_data:
                room_name = room_data[0]
                subject_names = room_data[1:]

                # Match subjects by name
                matched_subjects = subjects.filter(name__in=subject_names)

                # Create or update the room
                room, _ = Room.objects.update_or_create(
                    name=room_name,
                    pool=room_pool,
                    defaults={"pool": room_pool},
                )

                # Add subjects to the room
                room.compatible_subjects.set(matched_subjects)
                created_rooms.append(room)

            return Response(
                RoomSerializer(created_rooms, many=True).data,
                status=status.HTTP_201_CREATED,
            )
        except RoomPool.DoesNotExist:
            return Response({"error": "RoomPool not found."}, status=404)
        except SubjectPool.DoesNotExist:
            return Response({"error": "SubjectPool not found."}, status=404)
        except Exception as e:
            return Response({"error": str(e)}, status=500)


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

    def get_queryset(self):
        qs = super().get_queryset()
        pool_id = self.request.query_params.get("pool_id")
        if pool_id:
            qs = qs.filter(pool__id=pool_id)
        return qs

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

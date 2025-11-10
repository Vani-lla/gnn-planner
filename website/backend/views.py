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
def import_requirements_csv(request):
    file = request.FILES.get("file")
    teacher_pool_id = request.data.get("teacher_pool_id")
    subject_pool_id = request.data.get("subject_pool_id")
    group_pool_id = request.data.get("group_pool_id")
    req_set_id = request.data.get("req_set_id")
    new_req_set_name = (request.data.get("new_req_set_name") or "").strip()

    if not file or not teacher_pool_id or not subject_pool_id or not group_pool_id:
        return Response(
            {"error": "file, teacher_pool_id, subject_pool_id, group_pool_id required"},
            status=400,
        )

    try:
        teacher_pool = TeacherPool.objects.get(id=teacher_pool_id)
        subject_pool = SubjectPool.objects.get(id=subject_pool_id)
        group_pool = StudentGroupPool.objects.get(id=group_pool_id)
    except (
        TeacherPool.DoesNotExist,
        SubjectPool.DoesNotExist,
        StudentGroupPool.DoesNotExist,
    ):
        return Response({"error": "Invalid pool id(s)"}, status=404)

    # RequirementSet resolve/create
    if req_set_id:
        try:
            req_set = RequirementSet.objects.get(id=req_set_id)
        except RequirementSet.DoesNotExist:
            return Response({"error": "RequirementSet not found"}, status=404)
    else:
        if not new_req_set_name:
            return Response(
                {"error": "Provide new_req_set_name when req_set_id not given"},
                status=400,
            )
        req_set = RequirementSet.objects.create(
            name=new_req_set_name,
            teacher_pool=teacher_pool,
            subject_pool=subject_pool,
            group_pool=group_pool,
            room_pool=None,
        )

    csv_text = file.read().decode("utf-8")
    reader = csv.reader(StringIO(csv_text))

    try:
        first_row = next(reader)
        second_row = next(reader)
    except StopIteration:
        return Response(
            {"error": "CSV must contain at least two header rows"}, status=400
        )

    # Build combined group names (skip first empty header cell)
    raw_first = first_row[1:]
    raw_second = second_row[1:]
    combined_names = [f"{a}_{b}" for a, b in zip(raw_first, raw_second)]

    # Existing groups in pool (dict by name)
    existing_groups = {g.name: g for g in StudentGroup.objects.filter(pool=group_pool)}
    # Keep only group objects that exist
    ordered_groups = [
        existing_groups[name] for name in combined_names if name in existing_groups
    ]

    subjects_cache = {s.name: s for s in Subject.objects.filter(pool=subject_pool)}
    teachers_cache = {t.name: t for t in Teacher.objects.filter(pool=teacher_pool)}

    def is_numeric(s: str) -> bool:
        return s.strip().isdigit()

    current_subject = None
    processed_rows = 0
    upserted = 0

    for row in reader:
        if not row:
            continue
        label = (row[0] or "").strip()
        if not label or is_numeric(label):
            continue  # skip numeric/empty first cell

        # Subject row
        if label in subjects_cache:
            current_subject = subjects_cache[label]
            processed_rows += 1
            continue

        # Teacher row (must match existing teacher and have current_subject)
        if label in teachers_cache and current_subject:
            teacher = teachers_cache[label]
            # Iterate hours aligned with filtered existing groups
            # Need original hours cells corresponding to combined_names indexes
            hours_cells = row[1:]
            # Map group objects to their column index
            for idx, g in enumerate(ordered_groups):
                if idx >= len(hours_cells):
                    break
                val = (hours_cells[idx] or "").strip()
                if not val:
                    continue
                try:
                    hours_int = int(val)
                except ValueError:
                    continue
                if hours_int <= 0:
                    continue
                req_obj = Requirement.objects.filter(
                    req_set=req_set,
                    subject=current_subject,
                    teacher=teacher,
                    group=g,
                ).first()
                if req_obj:
                    req_obj.hours = hours_int
                    req_obj.save()
                else:
                    Requirement.objects.create(
                        req_set=req_set,
                        subject=current_subject,
                        teacher=teacher,
                        group=g,
                        hours=hours_int,
                    )
                upserted += 1
            processed_rows += 1
        # Anything else ignored (no creation)

    return Response(
        {
            "message": "CSV processed",
            "requirement_set_id": req_set.id,
            "rows_processed": processed_rows,
            "requirements_upserted": upserted,
            "ignored_groups": [
                name for name in combined_names if name not in existing_groups
            ],
        },
        status=201,
    )


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

    def get_queryset(self):
        qs = super().get_queryset()
        req_set = self.request.query_params.get("req_set")
        if req_set:
            qs = qs.filter(req_set_id=req_set)
        return qs

    def create(self, request, *args, **kwargs):
        data = request.data
        if not isinstance(data, list):
            return Response({"error": "Expect a list of blocks"}, status=400)
        for block in data:
            block_id = block.get("id")
            req_set_id = block.get("req_set")
            groups = block.get("groups", [])
            numbers = block.get("numbers", {})
            power_block = block.get("power_block", False)
            max_number = block.get("max_number", 0)

            subjects = list(numbers.keys())  # derive subjects from numbers map

            block_data = {
                "req_set": req_set_id,
                "subjects": subjects,
                "groups": groups,
                "numbers": numbers,
                "power_block": power_block,
                "max_number": max_number,
            }

            if block_id:
                instance = SubjectBlock.objects.get(id=block_id)
                serializer = self.get_serializer(instance, data=block_data)
            else:
                serializer = self.get_serializer(data=block_data)

            serializer.is_valid(raise_exception=True)
            serializer.save()
        return Response({"message": "SubjectBlocks saved"}, status=200)


class TeacherAvailabilityViewSet(ModelViewSet):
    queryset = TeacherAvailability.objects.all()
    serializer_class = TeacherAvailabilitySerializer

    def get_queryset(self):
        qs = super().get_queryset()
        req_set = self.request.query_params.get("req_set")
        if req_set:
            qs = qs.filter(req_set_id=req_set)
        return qs

    def create(self, request, *args, **kwargs):
        """
        Bulk replace availability for a req_set.
        Body: { req_set_id: int, availability: { "<teacherId>": { "0": true, ... "4": false }, ... } }
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
            # Replace all for this req_set
            TeacherAvailability.objects.filter(req_set=req_set).delete()
            bulk = []
            for teacher_id, avail in availability_data.items():
                teacher = Teacher.objects.get(id=teacher_id)
                bulk.append(
                    TeacherAvailability(
                        teacher=teacher, req_set=req_set, availability=avail
                    )
                )
            TeacherAvailability.objects.bulk_create(bulk)
            return Response(
                {"message": "Teacher availability saved successfully."},
                status=status.HTTP_201_CREATED,
            )
        except RequirementSet.DoesNotExist:
            return Response({"error": "RequirementSet not found."}, status=404)
        except Teacher.DoesNotExist:
            return Response({"error": "Teacher not found."}, status=404)


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
        req_set_id = request.query_params.get("req_set_id")
        if req_set_id:
            try:
                req_set = RequirementSet.objects.get(id=req_set_id)
            except RequirementSet.DoesNotExist:
                return Response({"error": "RequirementSet not found."}, status=404)

            teachers = Teacher.objects.filter(pool=req_set.teacher_pool)
            groups = StudentGroup.objects.filter(pool=req_set.group_pool)
            subjects = Subject.objects.filter(pool=req_set.subject_pool)

            requirements = Requirement.objects.filter(req_set=req_set)
            requirements_data = RequirementSerializer(requirements, many=True).data

            data = {
                "req_set": {"id": req_set.id, "name": req_set.name},
                "teachers": [
                    {
                        "id": t.id,
                        "name": t.name,
                        "subjects": (
                            [
                                {"id": s.id, "name": s.name}
                                for s in t.teached_subjects.all()
                            ]
                            if t.teached_subjects.exists()
                            else []
                        ),
                    }
                    for t in teachers
                ],
                "groups": [{"id": g.id, "name": g.name} for g in groups],
                "subjects": [{"id": s.id, "name": s.name} for s in subjects],
                "requirements": requirements_data,
            }
            return Response(data, status=200)

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

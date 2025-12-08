from rest_framework import serializers

from .models import (
    Plan,
    Requirement,
    RequirementSet,
    Room,
    RoomPool,
    StudentGroup,
    StudentGroupPool,
    Subject,
    SubjectBlock,
    SubjectPool,
    Teacher,
    TeacherAvailability,
    TeacherPool,
)


class SubjectBlockSerializer(serializers.ModelSerializer):
    subjects = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.all(), many=True
    )
    groups = serializers.PrimaryKeyRelatedField(
        queryset=StudentGroup.objects.all(), many=True
    )

    class Meta:
        model = SubjectBlock
        fields = ["id", "req_set", "subjects", "groups", "numbers", "power_block", "max_number"]


class TeacherAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = TeacherAvailability
        fields = ["id", "teacher", "req_set", "availability"]


class PlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = Plan
        fields = ["id", "name"]


class RequirementSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequirementSet
        fields = ["id", "name", "teacher_pool", "group_pool", "subject_pool", "room_pool"]


class StudentGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentGroup
        fields = ["id", "name", "desc", "pool"]


class StudentGroupPoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentGroupPool
        fields = ["id", "name"]


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ["id", "name", "pool", "compatible_subjects"]


class RoomPoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomPool
        fields = ["id", "name"]


class TeacherSerializer(serializers.ModelSerializer):
    pool = serializers.PrimaryKeyRelatedField(
        queryset=TeacherPool.objects.all(), many=True
    )
    teached_subjects = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.all(), many=True
    )

    class Meta:
        model = Teacher
        fields = ["id", "name", "pool", "teached_subjects"]


class TeacherPoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeacherPool
        fields = ["id", "name"]


class SubjectSerializer(serializers.ModelSerializer):
    pool = serializers.PrimaryKeyRelatedField(
        many=True, queryset=SubjectPool.objects.all()
    )

    class Meta:
        model = Subject
        fields = ["id", "name", "pool"]


class SubjectPoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubjectPool
        fields = ["id", "name"]


class RequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Requirement
        fields = ["id", "req_set", "teacher", "group", "subject", "hours"]

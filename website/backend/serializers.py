from rest_framework import serializers

from .models import (
    Room,
    RoomPool,
    StudentGroup,
    StudentGroupPool,
    Subject,
    SubjectPool,
    Teacher,
    TeacherPool,
    Requirement,
)


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
        fields = ["id", "name", "pool", "preferences"]


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

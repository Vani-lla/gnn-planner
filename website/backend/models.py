from django.db import models


class StudentGroupPool(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class StudentGroup(models.Model):
    pool = models.ForeignKey(StudentGroupPool, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    desc = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class RoomPool(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Room(models.Model):
    pool = models.ForeignKey(RoomPool, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    preferences = models.JSONField(blank=True, null=True)

    def __str__(self):
        return self.name


class SubjectPool(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Subject(models.Model):
    pool = models.ManyToManyField(SubjectPool)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class TeacherPool(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Teacher(models.Model):
    pool = models.ManyToManyField(TeacherPool)
    name = models.CharField(max_length=255)
    teached_subjects = models.ManyToManyField(Subject)

    def __str__(self):
        return f"{self.name}"


class RequirementSet(models.Model):
    teacher_pool = models.ForeignKey(TeacherPool, on_delete=models.SET_NULL, null=True)
    room_pool = models.ForeignKey(RoomPool, on_delete=models.SET_NULL, null=True)
    group_pool = models.ForeignKey(
        StudentGroupPool, on_delete=models.SET_NULL, null=True
    )
    subject_pool = models.ForeignKey(SubjectPool, on_delete=models.SET_NULL, null=True)

    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class TeacherAvailability(models.Model):
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    req_set = models.ForeignKey(RequirementSet, on_delete=models.SET_NULL, null=True)
    availability = models.JSONField()

    def __str__(self):
        return f"Availability of {self.teacher} for {self.req_set}"


class Requirement(models.Model):
    req_set = models.ForeignKey(
        RequirementSet, on_delete=models.CASCADE, related_name="requirements"
    )
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    group = models.ForeignKey(StudentGroup, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    hours = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.subject} {self.hours}h - {self.teacher} / {self.group}"


class Plan(models.Model):
    req_set = models.ForeignKey(RequirementSet, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Lesson(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="lessons")
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    day = models.PositiveSmallIntegerField()
    hour = models.PositiveSmallIntegerField()

    def __str__(self):
        return f"{self.subject} by {self.teacher} in {self.room} (Day {self.day}, Hour {self.hour})"

from django.db import models


class Student(models.Model):
    name = models.CharField(max_length=100)
    roll_number = models.CharField(max_length=20, unique=True)
    photo = models.ImageField(upload_to='photos/')
    face_encoding = models.BinaryField()

    def __str__(self):
        return self.name


class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    time = models.TimeField(auto_now_add=True)
    status = models.CharField(
        max_length=10,
        choices=[('Present', 'Present'), ('Absent', 'Absent')],
        default='Absent'  # Set default status to 'Absent'
    )

    def __str__(self):
        return f"{self.student.name} - {self.date} - {self.time} - {self.status}"

from django.shortcuts import render, redirect
from django.http import JsonResponse, StreamingHttpResponse
from .models import Student, Attendance
import face_recognition
import cv2
import pickle
import numpy as np
import time
from django.views.decorators.csrf import csrf_exempt  # Add this
import json  # Import Json
import base64  # Import base64
import datetime


def register_student(request):
    if request.method == 'POST':
        image = face_recognition.load_image_file(request.FILES['photo'])
        encodings = face_recognition.face_encodings(image)
        if not encodings:
            return JsonResponse({'error': 'No face found'})

        encoding = encodings[0]
        pickled_encoding = pickle.dumps(encoding)

        Student.objects.create(
            name=request.POST['name'],
            roll_number=request.POST['roll_number'],
            photo=request.FILES['photo'],
            face_encoding=pickled_encoding
        )
        return redirect('register_student')

    return render(request, 'register.html')


def get_student_attendance():
    """
    Helper function to get student attendance data.
    Returns:
        list: A list of dictionaries, where each dictionary contains student
              information and their latest attendance status.
    """
    students = Student.objects.all()
    student_attendance_list = []
    for student in students:
        # Get the latest attendance record for each student
        latest_attendance = Attendance.objects.filter(
            student=student).order_by('-date', '-time').first()
        student_attendance = {
            'student': student,
            'latest_attendance': latest_attendance.status if latest_attendance else 'Absent',
            'date': latest_attendance.date if latest_attendance else None,
            'time': latest_attendance.time if latest_attendance else None,
        }
        student_attendance_list.append(student_attendance)
    return student_attendance_list


def show_attendance(request):
    """
    View to display the attendance table.
    """
    student_attendance_list = get_student_attendance()
    return render(request, 'attendance_table.html', {'student_attendance_list': student_attendance_list})


@csrf_exempt  # Add this decorator to mark_attendance view
def mark_attendance(request):
    """
    View to mark attendance.  Now receives frame data from the frontend.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body.decode('utf-8'))
            frame_data_url = data['frame']  # Get the frame data URL
            # print(frame_data_url) #check
            # Convert the data URL to a NumPy array (and then to a cv2 frame)
            _, encoded_data = frame_data_url.split(',', 1)
            decoded_data = base64.b64decode(encoded_data)
            np_data = np.frombuffer(decoded_data, np.uint8)
            frame = cv2.imdecode(np_data, cv2.IMREAD_COLOR)

            students = Student.objects.all()
            known_encodings = [pickle.loads(s.face_encoding)
                               for s in students]

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_frame)
            encodings = face_recognition.face_encodings(
                rgb_frame, face_locations)

            face_names = []
            detected_faces = []  # To store face locations
            attendance_data = []  # send this

            for (top, right, bottom, left), face_encoding in zip(
                face_locations, encodings
            ):
                matches = face_recognition.compare_faces(
                    known_encodings, face_encoding)
                name = 'Unknown'
                if True in matches:
                    index = matches.index(True)
                    student = students[index]
                    today_attendance = Attendance.objects.filter(
                        student=student, date=datetime.date.today()  # Changed this line
                    ).first()
                    print('Student:', student)  # Added debugging print
                    # Added debugging print
                    print('Today attendance:', today_attendance)
                    if not today_attendance:
                        Attendance.objects.create(
                            student=student, status='Present')
                        print(
                            "Attendance marked for:", student.name)  # Added print
                        today_attendance = Attendance.objects.filter(
                            student=student, date=datetime.date.today()  # Changed this line
                        ).first()
                    name = student.name
                    face_names.append(name)
                    detected_faces.append({
                        'name': name,
                        'top': top,
                        'right': right,
                        'bottom': bottom,
                        'left': left,
                    })
                    attendance_data.append({
                        'student': {'id': student.id, 'name': student.name, 'roll_number': student.roll_number},
                        'latest_attendance': today_attendance.status if today_attendance else 'Absent',
                        'date': today_attendance.date if today_attendance else None,
                        'time': today_attendance.time if today_attendance else None,
                    })
                    cv2.rectangle(frame, (left, top),
                                  (right, bottom), (0, 255, 0), 2)
                    cv2.putText(
                        frame,
                        name,
                        (left + 6, bottom - 6),
                        cv2.FONT_HERSHEY_DUPLEX,
                        0.7,
                        (255, 255, 255),
                        1,
                    )
                else:
                    face_names.append(name)
                    detected_faces.append({  # Add face location for unknown faces
                        'name': 'Unknown',
                        'top': top,
                        'right': right,
                        'bottom': bottom,
                        'left': left,
                    })
                    attendance_data.append({  # send for each student
                        'student': {'id': student.id, 'name': student.name, 'roll_number': student.roll_number},
                        'latest_attendance': 'Absent',  # Or keep it 'Unknown'
                        'date': None,
                        'time': None,
                    })
                    cv2.rectangle(frame, (left, top),
                                  (right, bottom), (0, 0, 255), 2)
                    cv2.putText(
                        frame,
                        name,
                        (left + 6, bottom - 6),
                        cv2.FONT_HERSHEY_DUPLEX,
                        0.7,
                        (255, 255, 255),
                        1,
                    )

            if face_names:
                # Return the names
                # Return detected faces
                return JsonResponse({'status': 'success', 'message': f"Faces detected: {', '.join(face_names)}", 'face_names': face_names, 'detected_faces': detected_faces, 'attendance_data': attendance_data})
            else:
                return JsonResponse({'status': 'success', 'message': "No face detected", 'face_names': [], 'detected_faces': [], 'attendance_data': []})
        except Exception as e:
            print(f"Error: {e}")  # Print the error
            return JsonResponse({'status': 'error', 'message': f"Error processing frame: {str(e)}"})
    else:
        student_attendance_list = get_student_attendance()
        return render(request, 'mark_attendance.html', {'student_attendance_list': student_attendance_list})


def video_feed(request):
    """
    View to stream the video feed.
    """
    video = cv2.VideoCapture(1)

    def generate():
        while True:
            ret, frame = video.read()
            if not ret:
                break
            _, jpeg = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')
    return StreamingHttpResponse(generate(), content_type='multipart/x-mixed-replace;boundary=frame')

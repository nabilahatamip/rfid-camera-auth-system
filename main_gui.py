import sys
import cv2
import serial
from PyQt5.QtCore import QThread, pyqtSignal
import os
import face_recognition
import numpy as np
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QVBoxLayout, QHBoxLayout
)
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import Qt, QTimer


class SmartDoorSystemGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart Door System")
        self.setGeometry(200, 100, 800, 600)
        self.cap = None
        self.serial_port = None
        self.timer = QTimer()
        self.known_face_encodings = []
        self.known_face_names = []
        self.current_name = "Unknown"
        self.init_ui()
        self.load_faces()
        self.start_all_systems()

    def init_ui(self):
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        central_widget.setStyleSheet("background-color: #FFF5E1;")
        central_widget.setLayout(main_layout)

        logo_layout = QHBoxLayout()
        logo_left = QLabel()
        logo_left.setPixmap(QPixmap("assets/image.png").scaledToHeight(60, Qt.SmoothTransformation))
        logo_right = QLabel()
        logo_right.setPixmap(QPixmap("assets/telkom.png").scaledToHeight(60, Qt.SmoothTransformation))
        logo_layout.addWidget(logo_left, alignment=Qt.AlignLeft)
        logo_layout.addStretch()
        logo_layout.addWidget(logo_right, alignment=Qt.AlignRight)
        main_layout.addLayout(logo_layout)

        title = QLabel("SMART DOOR SYSTEM")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #333;")
        main_layout.addWidget(title)

        self.image_label = QLabel()
        self.image_label.setFixedSize(400, 300)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: #ddd; border: 4px solid red; margin: 10px;")
        face_layout = QHBoxLayout()
        face_layout.addStretch()
        face_layout.addWidget(self.image_label)
        face_layout.addStretch()
        main_layout.addLayout(face_layout)

        self.name_label = QLabel("Name   : Unknown")
        self.status_label = QLabel("Status : Denied")
        for label in [self.name_label, self.status_label]:
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("""
                background-color: #333;
                color: white;
                font-size: 16px;
                padding: 10px;
                border-radius: 6px;
                margin: 5px 50px;
            """)
            main_layout.addWidget(label)

        main_layout.addStretch()
        self.setCentralWidget(central_widget)

    def load_faces(self):
        training_dir = "training"
        if not os.path.exists(training_dir):
            print(f"[WARNING] Folder '{training_dir}' tidak ditemukan.")
            return

        for person_name in os.listdir(training_dir):
            person_dir = os.path.join(training_dir, person_name)
            if not os.path.isdir(person_dir):
                continue

            for image_name in os.listdir(person_dir):
                image_path = os.path.join(person_dir, image_name)

                try:
                    image_bgr = cv2.imread(image_path)
                    if image_bgr is None:
                        print(f"[ERROR] Gambar tidak bisa dibuka: {image_path}")
                        continue

                    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
                    encodings = face_recognition.face_encodings(image_rgb)

                    if encodings:
                        self.known_face_encodings.append(encodings[0])
                        self.known_face_names.append(person_name)
                        print(f"[OK] Wajah dari {person_name} dimuat dari {image_name}")
                    else:
                        print(f"[WARNING] Tidak ditemukan wajah di: {image_name}")

                except Exception as e:
                    print(f"[ERROR] Gagal proses gambar {image_path}: {e}")

    def start_all_systems(self):
        # Deteksi kamera otomatis
        for index in range(5):
            test_cap = cv2.VideoCapture(index, cv2.CAP_ANY)
            if test_cap.isOpened():
                print(f"[INFO] Kamera ditemukan di index {index}")
                self.cap = test_cap
                break
            else:
                test_cap.release()

        if self.cap is None or not self.cap.isOpened():
            print("[ERROR] Tidak ada kamera yang dapat digunakan.")
            self.status_label.setText("Status : Kamera Tidak Ditemukan")
            return
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)

        self.rfid_thread = RFIDThread()
        self.rfid_thread.rfid_detected.connect(self.handle_rfid)
        self.rfid_thread.start()

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret or frame is None:
            print("[ERROR] Kamera gagal diinisialisasi atau frame kosong. Periksa index kamera atau koneksi webcam.")
            self.status_label.setText("Status : Kamera Error")
            return

        if len(frame.shape) != 3 or frame.shape[2] != 3:
            print("[ERROR] Format frame kamera tidak valid (harus RGB).")
            return

        try:
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = face_recognition.face_locations(rgb_image)
            face_encodings = face_recognition.face_encodings(rgb_image, face_locations)

            name = "Unknown"
            for face_encoding in face_encodings:
                matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding)
                if True in matches:
                    match_index = matches.index(True)
                    name = self.known_face_names[match_index]
                    break

            self.current_name = name

            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image).scaled(
                self.image_label.width(),
                self.image_label.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(pixmap)

            self.name_label.setText(f"Name   : {name}")
            self.status_label.setText("Status : Denied")

        except Exception as e:
            print(f"[ERROR] Gagal memproses frame kamera: {e}")

    

    def lookup_rfid(self, rfid_input):
        try:
            with open("historyy.txt", "r") as file:
                for line in file:
                    if " - " in line:
                        uid, name = line.strip().split(" - ", 1)
                        if uid.strip() == rfid_input:
                            return name
        except Exception as e:
            print(f"❌ Gagal membaca historyy.txt: {e}")
        return "Unknown"

    def handle_rfid(self, rfid_data):
        print(f"RFID Detected: {rfid_data}")
        name = self.lookup_rfid(rfid_data)
        if name != "Unknown":
            self.name_label.setText(f"Name   : {name}")
            self.status_label.setText("Status : Granted")
        else:
            self.name_label.setText("Name   : Unknown")
            self.status_label.setText("Status : Denied")


    def closeEvent(self, event):
        print("Menutup aplikasi...")
        self.timer.stop()
        if self.cap:
            self.cap.release()
        if self.rfid_thread:
            self.rfid_thread.stop()
        event.accept()


class RFIDThread(QThread):
    rfid_detected = pyqtSignal(str)

    def __init__(self, port="COM3", baudrate=9600):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.serial_port = None

    def run(self):
        try:
            self.serial_port = serial.Serial(self.port, self.baudrate, timeout=1)
            while True:
                if self.serial_port.in_waiting:
                    data = self.serial_port.readline().decode('utf-8').strip()
                    if data:
                        self.rfid_detected.emit(data)
        except serial.SerialException:
            print(f"⚠️ Tidak dapat membuka port {self.port} untuk RFID.")

    def stop(self):
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SmartDoorSystemGUI()
    window.show()
    sys.exit(app.exec_())
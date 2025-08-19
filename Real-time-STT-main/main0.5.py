from flask import Flask, jsonify, request
from flask_cors import CORS
import threading
import queue
import io
import logging
import datetime
import pyaudio
import speech_recognition as sr
import time
from faster_whisper import WhisperModel
import pyodbc
import os  # 파일 탐색용 추가

app = Flask(__name__)
CORS(app)

# 텍스트 파일 저장 경로 (필요에 따라 변경 가능)
LOG_DIR = os.getcwd()

# DB 연결 함수
def get_db_connection():
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=DESKTOP-1KG9K4O\SQLEXPRESS;'
        'DATABASE=wb41;'
        'UID=aaa;'
        'PWD=1234'
    )
    return conn


class STT:
    def __init__(self, model_size="large", device="cuda", compute_type="float16", logging_level="INFO"):
        self.recorder = sr.Recognizer()
        self.data_queue = queue.Queue()
        self.transcription = []
        self.last_transcription = ""
        self.is_listening = True
        self.is_paused = False

        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        now = datetime.datetime.now()
        self.log_filename = now.strftime("%Y-%m-%d_%H-%M-%S_transcript.txt")

        self.lock = threading.Lock()
        STT.configure_logging(level=logging_level)

        self.thread = threading.Thread(target=self.transcribe)
        self.thread.daemon = True
        self.thread.start()

        print("준비되었습니다!\n")

    def transcribe(self):
        while self.is_listening:
            audio_data = self.data_queue.get()
            if audio_data == 'STOP':
                break

            if self.is_paused:
                self.data_queue.task_done()
                time.sleep(0.1)
                continue

            segments, info = self.model.transcribe(audio_data, beam_size=5, vad_filter=True)
            for segment in segments:
                text = segment.text.strip()
                log_msg = "[%.2fs -> %.2fs] %s" % (segment.start, segment.end, text)
                logging.info(log_msg)

                with self.lock:
                    self.transcription.append(text)
                    self.last_transcription = text

                # DB로 교체
                with open(self.log_filename, "a", encoding="utf-8") as f:
                    f.write(text + "\n")

            self.data_queue.task_done()
            time.sleep(0.25)

    def recorder_callback(self, _, audio_data):
        audio = io.BytesIO(audio_data.get_wav_data())
        self.data_queue.put(audio)

    def listen(self):
        def background():
            mic = sr.Microphone(device_index=self.setup_mic())
            with mic as source:
                self.recorder.adjust_for_ambient_noise(source)
            self.recorder.listen_in_background(mic, callback=self.recorder_callback)
            while self.is_listening:
                time.sleep(0.5)

        threading.Thread(target=background, daemon=True).start()

    def stop(self):
        self.is_listening = False
        self.data_queue.put("STOP")
        logging.info(f"전체 인식 결과:\n {self.transcription}")

    def get_last_transcription(self):
        with self.lock:
            text = self.last_transcription
        return text

    def pause(self):
        self.is_paused = True
        logging.info("음성 인식 일시정지됨.")

    def resume(self):
        self.is_paused = False
        logging.info("음성 인식 다시 시작됨.")

    @staticmethod
    def setup_mic():
        p = pyaudio.PyAudio()
        try:
            return p.get_default_input_device_info()["index"]
        except (IOError, OSError):
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    return i
        raise Exception("입력 장치를 찾을 수 없습니다.")

    @staticmethod
    def configure_logging(level="INFO"):
        levels = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        logging.basicConfig(level=levels.get(level.upper(), logging.INFO))


stt = STT()
stt.listen()


# --- 회원가입 API ---
@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    email = data.get("email")
    name = data.get("name")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM S_User WHERE User_id = ?", username)
    if cursor.fetchone()[0] > 0:
        return jsonify({"success": False, "message": "이미 존재하는 아이디입니다."})

    cursor.execute(
        "INSERT INTO S_User (User_id, User_pw, User_Email, User_Name) VALUES (?, ?, ?, ?)",
        (username, password, email, name)
    )
    conn.commit()
    conn.close()

    return jsonify({"success": True})


# --- 로그인 API ---
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM S_User WHERE User_id = ? AND User_pw = ?", username, password)
    user = cursor.fetchone()
    conn.close()

    if user:
        return jsonify({"success": True, "token": "dummy-token"})
    else:
        return jsonify({"success": False, "message": "아이디 또는 비밀번호가 틀렸습니다."})


# --- 내 정보 API ---
@app.route("/api/profile", methods=["GET"])
def get_profile():
    username = request.args.get("username")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT User_id, User_Email, User_Name FROM S_User WHERE User_id = ?", (username,))
    user = cursor.fetchone()
    conn.close()

    if user:
        user_info = {
            "username": user.User_id,
            "email": user.User_Email,
            "name": user.User_Name
        }
        return jsonify({"success": True, "user": user_info})
    else:
        return jsonify({"success": False, "message": "사용자를 찾을 수 없습니다."})


@app.route("/api/last_transcription")
def last_transcription():
    text = stt.get_last_transcription()
    return jsonify({"text": text})


@app.route("/api/stop", methods=["POST"])
def stop_stt():
    stt.stop()
    return jsonify({"status": "stopped"})


@app.route("/api/pause", methods=["POST"])
def pause_stt():
    stt.pause()
    return jsonify({"status": "paused"})


@app.route("/api/resume", methods=["POST"])
def resume_stt():
    stt.resume()
    return jsonify({"status": "resumed"})


# --- 텍스트 파일 목록 조회 API ---
@app.route("/api/text_files", methods=["GET"])
def list_text_files():
    try:
        files = []
        for filename in os.listdir(LOG_DIR):
            if filename.endswith(".txt"):
                files.append(filename)
        return jsonify({"success": True, "files": files})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

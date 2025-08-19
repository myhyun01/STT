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
import os  # 파일 탐색용

app = Flask(__name__)
CORS(app)

# DB 연결 함수
def get_db_connection():
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=DESKTOP-PGE18AQ\SQLEXPRESS;'
        'DATABASE=weekproject;'
        'UID=bbb;'
        'PWD=1234'
    )
    return conn


class STT:
    def __init__(self, model_size="large", device="cuda", compute_type="float16", logging_level="INFO"):
        self.recorder = sr.Recognizer()
        self.data_queue = queue.Queue()
        self.transcription = []
        self.last_transcription = ""
        self.is_listening = False  # 초기값 False로 변경
        self.is_paused = False

        self.user_id = None
        self.original_id = None

        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        STT.configure_logging(level=logging_level)

        self.lock = threading.Lock()
        self.thread = None  # 스레드는 listen() 시작 시 생성

        print("STT 준비 완료!\n")

    def set_user(self, user_id):
        self.user_id = user_id
        self.create_original_record()

    def create_original_record(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO S_Original (User_id, original_title) OUTPUT INSERTED.original_id VALUES (?, ?)",
            (self.user_id, now)
        )
        self.original_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        logging.info(f"S_Original에 기록됨: original_id={self.original_id}")

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

                # DB에 저장
                if self.original_id is not None:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO S_Sentence (original_id, sentence_content) VALUES (?, ?)",
                        (self.original_id, text)
                    )
                    conn.commit()
                    conn.close()
                else:
                    logging.warning("original_id가 설정되지 않았습니다. DB에 저장되지 않음.")

            self.data_queue.task_done()
            time.sleep(0.25)

    def recorder_callback(self, _, audio_data):
        audio = io.BytesIO(audio_data.get_wav_data())
        self.data_queue.put(audio)

    def listen(self):
        if self.is_listening:
            # 이미 듣고 있으면 다시 시작하지 않음
            logging.info("이미 음성 인식 중입니다.")
            return

        self.is_listening = True

        def background():
            mic = sr.Microphone(device_index=self.setup_mic())
            with mic as source:
                self.recorder.adjust_for_ambient_noise(source)
            self.recorder.listen_in_background(mic, callback=self.recorder_callback)
            while self.is_listening:
                time.sleep(0.5)

        self.thread = threading.Thread(target=self.transcribe)
        self.thread.daemon = True
        self.thread.start()

        threading.Thread(target=background, daemon=True).start()

    def stop(self):
        if not self.is_listening:
            logging.info("이미 음성 인식이 중지된 상태입니다.")
            return

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
# stt.listen()  # 서버 시작 시 음성 인식 자동 시작 안함


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
        # 로그인 성공 → stt에 사용자 설정
        stt.set_user(username)
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

@app.route("/api/delete_user", methods=["POST"])
def delete_user():
    data = request.json
    username = data.get("username")

    if not username:
        return jsonify({"success": False, "message": "username이 필요합니다."}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 사용자 존재 여부 확인
        cursor.execute("SELECT COUNT(*) FROM S_User WHERE User_id = ?", (username,))
        if cursor.fetchone()[0] == 0:
            conn.close()
            return jsonify({"success": False, "message": "존재하지 않는 사용자입니다."}), 404

        # 자식 테이블부터 삭제
        cursor.execute("""
            DELETE S_S
            FROM S_Sentence S_S
            INNER JOIN S_Original S_O ON S_S.original_id = S_O.original_id
            WHERE S_O.User_id = ?
        """, (username,))
        deleted_sentence = cursor.rowcount

        cursor.execute("DELETE FROM S_Original WHERE User_id = ?", (username,))
        deleted_original = cursor.rowcount

        cursor.execute("DELETE FROM S_User WHERE User_id = ?", (username,))
        deleted_user = cursor.rowcount

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "message": f"삭제 완료: 문장 {deleted_sentence}개, 원본 {deleted_original}개, 사용자 {deleted_user}개."
        })

    except Exception as e:
        print("삭제 중 예외 발생:", e)
        return jsonify({"success": False, "message": str(e)}), 500






# --- 마지막 인식 결과 반환 ---
@app.route("/api/last_transcription")
def last_transcription():
    text = stt.get_last_transcription()
    return jsonify({"text": text})


# --- STT 컨트롤 API ---
@app.route("/api/start", methods=["POST"])
def start_stt():
    if stt.is_listening:
        return jsonify({"status": "already listening"})
    else:
        stt.listen()
        return jsonify({"status": "started"})


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


# --- 텍스트 파일 목록 API ---
@app.route("/api/text_files", methods=["GET"])
def list_text_files():
    user_id = request.args.get("user_id")  # 클라이언트에서 user_id를 쿼리 파라미터로 받아야 합니다.

    if not user_id:
        return jsonify({"success": False, "message": "user_id가 필요합니다."}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT original_title FROM S_Original WHERE User_id = ?", user_id)
        rows = cursor.fetchall()
        conn.close()

        titles = [row.original_title for row in rows]

        return jsonify({"success": True, "titles": titles})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    
    #--- 수정 기능 ---
@app.route("/api/update-profile", methods=["PUT"])
def update_profile():
    data = request.get_json()
    username = data.get("username")
    new_email = data.get("email")
    new_name = data.get("name")
    new_password = data.get("password")

    if not username:
        return jsonify({"success": False, "message": "username이 필요합니다."}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM S_User WHERE User_id = ?", (username,))
        if not cursor.fetchone():
            return jsonify({"success": False, "message": "사용자를 찾을 수 없습니다."}), 404

        cursor.execute("""
            UPDATE S_User 
            SET User_Email = ?, User_Name = ?, User_pw = ?
            WHERE User_id = ?
        """, (new_email, new_name, new_password, username))

        conn.commit()
        return jsonify({"success": True, "message": "회원 정보 수정 완료"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

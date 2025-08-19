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
import os
from openai import OpenAI
import traceback

app = Flask(__name__)
CORS(app)

client = OpenAI(api_key="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")

@app.errorhandler(Exception)
def handle_exception(e):
    logging.error("=== 예외 발생 ===")
    logging.error(traceback.format_exc())
    return jsonify({"success": False, "message": str(e)}), 500

def ask_gpt(prompt):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "당신은 정확하고 창의적인 비서입니다. 질문에 대한 해답을 알려주세요 가끔은 센스 발휘도 부탁해요."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.85
    )
    return response.choices[0].message.content.strip()

def get_db_connection():
    conn = pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=DESKTOP-PGE18AQ\\SQLEXPRESS;'
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
        self.is_listening = False
        self.is_paused = False

        self.user_id = None
        self.original_id = None

        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        STT.configure_logging(level=logging_level)

        self.lock = threading.Lock()
        self.thread = None

        print("STT 준비 완료!\n")

    def set_user(self, user_id):
        self.user_id = user_id

    def create_original_record_first(self, user_id):
        self.set_user(user_id)
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


#--- GPT 응답 기능 ---
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    text = data.get("prompt", "") or data.get("text", "")
    if not text:
        return jsonify({"success": False, "message": "prompt가 필요합니다!"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        answer = ask_gpt(text)

        # S_Sentence에서 문장 내용으로 sentence_number 찾기
        cursor.execute("SELECT sentence_number FROM S_Sentence WHERE sentence_content = ?", (text,))
        row = cursor.fetchone()

        if row:
            sentence_number = row[0]

            # Sentence_Mean에 이미 있으면 update, 없으면 insert
            cursor.execute("SELECT COUNT(*) FROM Sentence_Mean WHERE sentence_number = ?", (sentence_number,))
            exists = cursor.fetchone()[0]

            if exists:
                cursor.execute(
                    "UPDATE Sentence_Mean SET sentence_mean = ? WHERE sentence_number = ?",
                    (answer, sentence_number)
                )
            else:
                cursor.execute(
                    "INSERT INTO Sentence_Mean (sentence_number, sentence_mean) VALUES (?, ?)",
                    (sentence_number, answer)
                )
            conn.commit()
        else:
            # 문장 못찾으면 그냥 패스하거나 로그 남기기
            print(f"'{text}' 문장을 DB에서 찾을 수 없습니다.")

        return jsonify({"success": True, "memo": answer})

    except Exception as e:
        conn.rollback()
        logging.error(traceback.format_exc())
        return jsonify({"success": False, "message": str(e)}), 500
    finally:
        conn.close()

#--- 회원가입 기능 ---
@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    email = data.get("email")
    name = data.get("name")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM S_User WHERE User_id = ?", (username,))
    if cursor.fetchone()[0] > 0:
        conn.close()
        return jsonify({"success": False, "message": "이미 존재하는 아이디입니다."})

    cursor.execute(
        "INSERT INTO S_User (User_id, User_pw, User_Email, User_Name) VALUES (?, ?, ?, ?)",
        (username, password, email, name)
    )
    conn.commit()
    conn.close()

    return jsonify({"success": True})

#--- 로그인 기능 ---
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM S_User WHERE User_id = ? AND User_pw = ?", (username, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        stt.set_user(username)
        return jsonify({"success": True, "token": "dummy-token"})
    else:
        return jsonify({"success": False, "message": "아이디 또는 비밀번호가 틀렸습니다."})

#--- 내정보 기능 ---
@app.route("/api/profile", methods=["GET"])
def get_profile():
    username = request.args.get("username")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT User_id, User_Email, User_Name FROM S_User WHERE User_id = ?", (username,))
    row = cursor.fetchone()
    conn.close()

    if row:
        # pyodbc는 튜플로 반환되니까, 딕셔너리로 수동 매핑!
        user_info = {
            "username": row[0],
            "email": row[1],
            "name": row[2]
        }
        return jsonify({"success": True, "user": user_info})
    else:
        return jsonify({"success": False, "message": "사용자를 찾을 수 없습니다."})

#--- 실시간 음성 인식 텍스트 기능 ---
@app.route("/api/last_transcription")
def last_transcription():
    return jsonify({"text": stt.get_last_transcription()})

#--- 음성 녹음 시작 기능 ---
@app.route("/api/start", methods=["POST"])
def start_stt():
    if not request.is_json:
        return jsonify({"success": False, "message": "Content-Type이 application/json이어야 합니다."}), 415
    
    data = request.get_json()  
    user_id = data.get("user_id")
    
    if not user_id:
        return jsonify({"success": False, "message": "user_id가 필요합니다."}), 400

    if stt.is_listening:
        stt.create_original_record_first(user_id)  # user_id 전달
        return jsonify({"status": "already listening"})
    else:
        stt.set_user(user_id)  # user_id 세팅
        stt.create_original_record_first(user_id)  # 원본 기록 생성
        stt.listen()
        return jsonify({"status": "started"})


#--- 음성 녹음 중지 기능 ---
@app.route("/api/stop", methods=["POST"])
def stop_stt():
    stt.stop()
    return jsonify({"status": "stopped"})

#--- 음성 녹음 일시정지 기능 ---
@app.route("/api/pause", methods=["POST"])
def pause_stt():
    stt.pause()
    return jsonify({"status": "paused"})

#--- 음성 녹음 다시시작 기능 ===
@app.route("/api/resume", methods=["POST"])
def resume_stt():
    stt.resume()
    return jsonify({"status": "resumed"})

#--- 원문 파일 타이틀 가져오기 기능 ---
@app.route("/api/text_files", methods=["GET"])
def list_text_files():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "user_id가 필요합니다."}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT original_title FROM S_Original WHERE User_id = ?", (user_id,))
        rows = cursor.fetchall()

        # 컬럼 이름 추출
        columns = [column[0] for column in cursor.description]
        
        # 튜플 rows -> dict 리스트 변환
        results = [dict(zip(columns, row)) for row in rows]

        titles = [row["original_title"] for row in results]

        conn.close()

        return jsonify({"success": True, "titles": titles})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


#--- 원문 내용만 보내는 기능 ---
@app.route("/api/text_file_sentences", methods=["GET"])
def get_text_file_sentences():
    user_id = request.args.get("user_id")
    original_title = request.args.get("original_title")

    if not user_id or not original_title:
        return jsonify({"success": False, "message": "user_id, original_title 모두 필요합니다."}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT original_id FROM S_Original WHERE User_id = ? AND original_title = ?",
            (user_id, original_title)
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({"success": False, "message": "해당 제목에 대한 데이터가 없습니다."}), 404

        original_id = row[0]

        cursor.execute(
            "SELECT sentence_number, sentence_content FROM S_Sentence WHERE original_id = ? ORDER BY sentence_number",
            (original_id,)
        )
        sentences = cursor.fetchall()

        sentence_list = []
        for s in sentences:
            sentence_list.append({
                "sentence_number": s[0],
                "sentence_content": s[1]
            })

        conn.close()

        return jsonify({
            "success": True,
            "sentences": sentence_list
        })

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


#--- 원문 내용 + GPT 해석 기능 ---
@app.route("/api/text_file_sentences_with_gpt", methods=["GET"])
def get_text_file_sentences_with_gpt():
    user_id = request.args.get("user_id")
    original_title = request.args.get("original_title")

    if not user_id or not original_title:
        return jsonify({"success": False, "message": "user_id, original_title 모두 필요합니다."}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT original_id FROM S_Original WHERE User_id = ? AND original_title = ?",
            (user_id, original_title)
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({"success": False, "message": "해당 제목에 대한 데이터가 없습니다."}), 404

        original_id = row[0]

        cursor.execute(
            "SELECT s.sentence_number, s.sentence_content, m.sentence_mean "
            "FROM S_Sentence s LEFT JOIN Sentence_Mean m ON s.sentence_number = m.sentence_number "
            "WHERE s.original_id = ? ORDER BY s.sentence_number",
            (original_id,)
        )
        sentences = cursor.fetchall()

        sentence_list = []
        for s in sentences:
            sentence_list.append({
                "sentence_number": s[0],
                "sentence_content": s[1],
                "sentence_mean": s[2]
            })

        conn.close()

        return jsonify({
            "success": True,
            "sentences": sentence_list
        })

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

#--- 수정 기능 ---
@app.route("/api/update_profile", methods=["PUT"])
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

#--- 회원 삭제 기능 ---
@app.route("/api/delete_user", methods=["POST"])
def delete_user():
    data = request.json
    username = data.get("username")

    if not username:
        return jsonify({"success": False, "message": "username이 필요합니다."}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM S_User WHERE User_id = ?", (username,))
        if cursor.fetchone()[0] == 0:
            conn.close()
            return jsonify({"success": False, "message": "존재하지 않는 사용자입니다."}), 404

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
    
#--- 원문 삭제 기능 ---
@app.route("/api/delete_original", methods=["POST"])
def delete_original():
    data = request.json
    username = data.get("username")
    title = data.get("title")

    if not username:
        return jsonify({"success": False, "message": "username이 필요합니다."}), 400
    
    if not title:
        return jsonify({"success": False, "message": "title 필요합니다."}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM S_User WHERE User_id = ?", (username,))
        if cursor.fetchone()[0] == 0:
            conn.close()
            return jsonify({"success": False, "message": "존재하지 않는 사용자입니다."}), 404
        
        cursor.execute("SELECT COUNT(*) FROM S_Original WHERE User_id = ? AND original_title = ?", (username, title,))
        if cursor.fetchone()[0] == 0:
            conn.close()
            return jsonify({"success": False, "message": "존재하지 않는 원문입니다."}), 404

        cursor.execute("""
            DELETE S_S
            FROM S_Sentence S_S
            JOIN S_Original S_O ON S_S.original_id = S_O.original_id
            WHERE S_O.user_id = ? AND S_O.original_title = ?
        """, (username, title,))

        cursor.execute("""
            DELETE FROM S_Original WHERE user_id = ? AND original_title = ?
        """, (username, title,))

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
        })

    except Exception as e:
        print("삭제 중 예외 발생:", e)
        return jsonify({"success": False, "message": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5000, debug=True)
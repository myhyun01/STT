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

class STT:
    def __init__(self, model_size="large", device="cuda", compute_type="float16", logging_level="INFO"):
        self.recorder = sr.Recognizer()
        self.data_queue = queue.Queue()
        self.transcription = []
        self.last_transcription = ""
        self.is_listening = True

        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        now = datetime.datetime.now()
        self.log_filename = now.strftime("%Y-%m-%d_%H-%M-%S_transcript.txt")

        self.lock = threading.Lock()
        STT.configure_logging(level=logging_level)  # 클래스명으로 호출

        self.thread = threading.Thread(target=self.transcribe)
        self.thread.daemon = True
        self.thread.start()

        print("준비되었습니다!\n")

    def transcribe(self):
        while self.is_listening:
            audio_data = self.data_queue.get()
            if audio_data == 'STOP':
                break
            segments, info = self.model.transcribe(audio_data, beam_size=5, vad_filter=True)
            for segment in segments:
                text = segment.text.strip()
                log_msg = "[%.2fs -> %.2fs] %s" % (segment.start, segment.end, text)
                logging.info(log_msg)

                with self.lock:
                    self.transcription.append(text)
                    self.last_transcription = text

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
            # self.last_transcription = ""  # 제거했습니다!
        return text

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


app = Flask(__name__)
CORS(app)  # CORS 허용

stt = STT()
stt.listen()

@app.route("/api/last_transcription")
def last_transcription():
    text = stt.get_last_transcription()
    return jsonify({"text": text})

@app.route("/api/stop", methods=["POST"])
def stop_stt():
    stt.stop()
    return jsonify({"status": "stopped"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

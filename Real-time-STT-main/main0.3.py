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
    """Faster WhisperModel과 speech_recognition을 사용하는 실시간 음성 인식 클래스입니다."""

    def __init__(self, model_size: str = "large", device: str = "cuda", compute_type: str = "float16",
                 logging_level: str = "INFO"):
        """STT 객체를 초기화합니다."""
        self.recorder = sr.Recognizer()
        self.data_queue = queue.Queue()
        self.transcription = ['']
        self.last_transcription = ""
        self.is_listening = True

        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self.default_mic = self.setup_mic()

        # Whisper 모델 로드 (language 인자 제거)
        self.model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)

        # 로그 파일 이름 생성 (날짜_시간)
        now = datetime.datetime.now()
        self.log_filename = now.strftime("%Y-%m-%d_%H-%M-%S_transcript.txt")

        self.lock = threading.Lock()

        # 로그 설정
        self.configure_logging(level=logging_level)

        self.thread = threading.Thread(target=self.transcribe)
        self.thread.daemon = True
        self.thread.start()

        logging.info("준비되었습니다!\n")
        print("준비되었습니다!\n")

    def transcribe(self):
        """큐에서 오디오 데이터를 꺼내어 텍스트로 변환합니다."""
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

                # 인식된 내용을 파일에도 기록
                with open(self.log_filename, "a", encoding="utf-8") as f:
                    f.write(text + "\n")

            self.data_queue.task_done()
            time.sleep(0.25)

    def recorder_callback(self, _, audio_data):
        """녹음 콜백 함수입니다."""
        audio = io.BytesIO(audio_data.get_wav_data())
        self.data_queue.put(audio)

    def listen(self):
        """마이크로부터 입력을 받아 들으며 콜백을 등록합니다."""
        with sr.Microphone(device_index=self.default_mic) as source:
            self.recorder.adjust_for_ambient_noise(source)
        self.recorder.listen_in_background(source=source, callback=self.recorder_callback)

    def stop(self):
        """음성 인식을 중지합니다."""
        logging.info("중지 중...")
        logging.info(f"전체 인식 결과:\n {self.transcription}")
        self.is_listening = False
        self.data_queue.put("STOP")

    def get_last_transcription(self):
        """가장 최근 인식된 결과를 반환하고 비웁니다."""
        with self.lock:
            text = self.last_transcription
            self.last_transcription = ""
        return text

    @staticmethod
    def setup_mic():
        """마이크를 설정합니다."""
        p = pyaudio.PyAudio()
        default_device_index = None
        try:
            default_input = p.get_default_input_device_info()
            default_device_index = default_input["index"]
        except (IOError, OSError):
            logging.error("기본 입력 장치를 찾을 수 없습니다. 모든 입력 장치를 출력합니다:")
            for i in range(p.get_device_count()):
                info = p.get_device_info_by_index(i)
                if info['maxInputChannels'] > 0:
                    logging.info(f"장치 인덱스: {i}, 장치 이름: {info['name']}")
                    if default_device_index is None:
                        default_device_index = i

        if default_device_index is None:
            raise Exception("입력 장치를 찾을 수 없습니다.")

        return default_device_index

    @staticmethod
    def configure_logging(level: str = "INFO"):
        """
        로그 레벨을 설정합니다.
        :param level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        """
        levels = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        logging.basicConfig(level=levels.get(level.upper(), logging.INFO))


# 사용 예시
try:
    stt = STT()
    stt.listen()

    while stt.is_listening:
        last_transcription = stt.get_last_transcription()
        if len(last_transcription) > 0:
            print("말씀하신 내용:", last_transcription)

        time.sleep(1)

except KeyboardInterrupt:
    # Ctrl+C로 프로그램 종료 시
    stt.stop()
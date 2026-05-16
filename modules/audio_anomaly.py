import webrtcvad
import pyaudio
import threading
import time

class AudioMonitor:
    def __init__(self, config):
        cfg = config.get("audio_anomaly", {})
        self.sample_rate = cfg.get("sample_rate", 16000)
        self.chunk_duration_ms = cfg.get("chunk_duration_ms", 30)
        self.vad_aggressiveness = cfg.get("vad_aggressiveness", 2)
        self.speech_threshold = cfg.get("speech_threshold_seconds", 2.0)
        
        self.chunk_size = int(self.sample_rate * self.chunk_duration_ms / 1000)
        
        self.vad = webrtcvad.Vad(self.vad_aggressiveness)
        
        self.running = False
        self.audio = pyaudio.PyAudio()
        self.stream = None
        
        self.is_speech = False
        self.speech_start_time = None
        self.anomaly = False
        
        self.lock = threading.Lock()
        self.thread = threading.Thread(target=self._audio_loop, daemon=True)
        
    def start(self):
        try:
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )
            self.running = True
            self.thread.start()
        except Exception as e:
            print(f"[Warning] Could not initialize audio stream: {e}")
            self.running = False

    def get_results(self):
        with self.lock:
            return {
                "is_speech": self.is_speech,
                "anomaly": self.anomaly
            }
            
    def _audio_loop(self):
        while self.running:
            try:
                # Read audio chunk
                chunk = self.stream.read(self.chunk_size, exception_on_overflow=False)
                # Check VAD
                is_active = self.vad.is_speech(chunk, self.sample_rate)
                
                with self.lock:
                    self.is_speech = is_active
                    if is_active:
                        if self.speech_start_time is None:
                            self.speech_start_time = time.time()
                        elif time.time() - self.speech_start_time > self.speech_threshold:
                            self.anomaly = True
                    else:
                        self.speech_start_time = None
                        self.anomaly = False
                        
            except Exception as e:
                print(f"[Audio Error] {e}")
                time.sleep(0.1)

    def stop(self):
        self.running = False
        if self.thread.is_alive():
            self.thread.join()
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.audio.terminate()

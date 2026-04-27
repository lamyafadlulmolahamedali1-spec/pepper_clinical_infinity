# ── Always-on speech ──────────────────────────────────────────────────
class Speech(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True, name="Speech")
        self._running = True
        self._manual  = False
        self._maudio  = None
        self._mlk     = threading.Lock()
        self.whisper  = None
        self.r = sr.Recognizer()
        self.r.energy_threshold = 100
        self.r.dynamic_energy_threshold = True
        self.r.dynamic_energy_adjustment_damping = 0.10
        self.r.pause_threshold = 0.5
        self.r.phrase_threshold = 0.03
        self.r.non_speaking_duration = 0.3
        try:
            with sr.Microphone() as src:
                self.r.adjust_for_ambient_noise(src, duration=0.6)
            print(f"✅ Mic always-on (energy={self.r.energy_threshold:.0f})")
        except Exception as e:
            print(f"⚠️  Mic: {e}")
        if WHISPER_OK:
            try:
                dev = "cuda" if os.path.exists("/dev/nvidia0") else "cpu"
                self.whisper = WhisperModel(
                    "tiny", device=dev,
                    compute_type="float16" if dev=="cuda" else "int8")
                print(f"✅ Whisper ({dev})")
            except Exception as e:
                print(f"⚠️  Whisper: {e}")

    def _transcribe(self, audio) -> str:
        if self.whisper:
            try:
                raw = audio.get_raw_data(convert_rate=16000, convert_width=2)
                with tempfile.NamedTemporaryFile(
                        suffix=".wav", delete=False) as tmp:
                    tp = tmp.name
                with wave.open(tp, "wb") as wf:
                    wf.setnchannels(1); wf.setsampwidth(2)
                    wf.setframerate(16000); wf.writeframes(raw)
                segs, _ = self.whisper.transcribe(
                    tp, language="en", beam_size=1, vad_filter=False)
                text = " ".join(s.text.strip() for s in segs).strip()
                try: os.unlink(tp)
                except Exception: pass
                if text:
                    LOG(f"Whisper: {text}")
                    return text.lower()
            except Exception as e:
                LOG(f"Whisper: {e}", "warn")
        try:
            text = self.r.recognize_google(audio)
            LOG(f"Google SR: {text}")
            return text.lower()
        except sr.UnknownValueError:
            return ""
        except Exception as e:
            LOG(f"SR: {e}", "warn")
            return ""

    def _heard(self, text: str):
        if not text: return
        text = text.strip().lower()
        ST["last_speech"] = text
        ST["last_sound"]  = time.time()
        ST["heard_flag"]  = True
        ST["speech_q"].put(text)
        ST["session_chat"].append({"role":"child","text":text,
            "time":datetime.now().strftime("%H:%M:%S")})
        if len(ST["session_chat"]) > 100:
            ST["session_chat"] = ST["session_chat"][-100:]
        BR.sig_rec_off.emit(text)

    def run(self):
        while self._running:
            try:
                with sr.Microphone() as src:
                    self.r.adjust_for_ambient_noise(src, duration=0.06)
                    ST["listening"] = True
                    try:
                        audio = self.r.listen(src, timeout=4,
                                              phrase_time_limit=8)
                        ST["recording"] = True
                        BR.sig_rec_on.emit()
                        text = self._transcribe(audio)
                        ST["recording"] = False
                        if text: self._heard(text)
                    except sr.WaitTimeoutError:
                        pass
                    except Exception:
                        pass
                    finally:
                        ST["recording"] = False
                        ST["listening"] = True
            except Exception:
                time.sleep(0.5)
            time.sleep(0.04)

    def start_manual(self):
        with self._mlk: self._manual = True
        ST["recording"] = True; BR.sig_rec_on.emit()
        threading.Thread(target=self._do_manual, daemon=True).start()

    def _do_manual(self):
        try:
            with sr.Microphone() as src:
                self.r.adjust_for_ambient_noise(src, duration=0.04)
                audio = self.r.listen(src, timeout=12, phrase_time_limit=8)
                with self._mlk: self._maudio = audio
        except Exception:
            pass
        finally:
            ST["recording"] = False
            with self._mlk: self._manual = False

    def stop_manual(self) -> str:
        for _ in range(30):
            with self._mlk:
                if not self._manual: break
            time.sleep(0.1)
        with self._mlk:
            audio = self._maudio
            self._maudio = None
        if not audio: return ""
        text = self._transcribe(audio)
        if text: self._heard(text)
        return text

    def stop(self): self._running = False

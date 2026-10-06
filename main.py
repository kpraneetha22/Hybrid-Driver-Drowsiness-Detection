# app.py
import pywhatkit
import os
import smtplib
import ssl
import threading
import time
import platform
import traceback
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, Response, jsonify
from scipy.spatial import distance as dist
import numpy as np
import imutils
import cv2
from dotenv import load_dotenv

def send_whatsapp_alert():
    phone = "+919704627165"  # your number
    msg = f"🚨 Driver {DRIVER_NAME} is drowsy! Vehicle {VEHICLE_ID}"
    pywhatkit.sendwhatmsg_instantly(phone, msg, wait_time=10, tab_close=True)
# ===== MediaPipe (dlib replacement) =====
import mediapipe as mp
mp_face_mesh = mp.solutions.face_mesh

load_dotenv()

app = Flask(__name__)

# === CONFIG ===
# === CONFIG ===
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_ADDRESS = "praneethakramadhati@gmail.com"
EMAIL_PASSWORD = "qktbzpusndicvlww"
ALERT_RECIPIENT = "praneethakramadhatii@gmail.com"
VEHICLE_ID = os.getenv("VEHICLE_ID", "234765")
DRIVER_NAME = os.getenv("DRIVER_NAME", "Rohini")


EYE_AR_THRESH = 0.25
YAWN_THRESH = 12
DROWSINESS_ALERT_THRESHOLD = 70
YAWN_ALERT_THRESHOLD = 30

# === DECAY CONFIG ===
DECAY_HALF_LIFE = 60.0  # seconds for count to halve when awake
MIN_COUNT = 0

class AppState:
    def __init__(self):
        self.drowsy_count = 0
        self.yawn_count = 0
        self.drowsy_alerted = False
        self.yawn_alerted = False
        self.last_drowsy_time = 0.0
        self.last_yawn_time = 0.0
        self.lock = threading.Lock()

state = AppState()

# === MODEL LOADING ===
def load_models():
    print("\n🔍 Loading MediaPipe Face Mesh...")
    try:
        face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=False,
            min_detection_confidence=0.6,
            min_tracking_confidence=0.6
        )
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        if face_cascade.empty():
            raise RuntimeError("Haar cascade not loaded.")
        print("✅ All models loaded successfully.\n")
        return face_cascade, face_mesh
    except Exception as e:
        raise RuntimeError(f"Model loading failed: {e}\n{traceback.format_exc()}")

try:
    face_cascade, face_mesh = load_models()
except Exception as e:
    print(str(e))
    exit(1)

# === SOUND FUNCTIONS (5-SECOND ALERT BEEP) ===
def play_5sec_alert_beep():
    """Plays a continuous/alert beep for 5 seconds across platforms."""
    start_time = time.time()
    try:
        system = platform.system()
        if system == "Windows":
            import winsound
            while time.time() - start_time < 5.0:
                winsound.Beep(500, 500)  # 200ms beep, looped
                time.sleep(0.05)
        elif system == "Linux":
            # Use 'speaker-test' for clean tone (fallback to bell)
            cmd = "timeout 5 speaker-test -t sine -f 200 -l 0 2>/dev/null"
            os.system(cmd)
            # If speaker-test fails, fallback:
            if os.system("which speaker-test > /dev/null 2>&1") != 0:
                for _ in range(25):
                    print("\a", end="", flush=True)
                    time.sleep(0.2)
        elif system == "Darwin":  # macOS
            # Loop Glass sound 5 times (~1s each)
            for _ in range(5):
                os.system('afplay /System/Library/Sounds/Glass.aiff 2>/dev/null')
                time.sleep(0.1)
        else:
            for _ in range(25):
                print("\a", end="", flush=True)
                time.sleep(0.2)
    except Exception as e:
        print(f"[SOUND ERROR] {e}")

def play_sound_yawn():
    try:
        system = platform.system()
        if system == "Windows":
            import winsound
            winsound.Beep(440, 300)
            time.sleep(0.1)
            winsound.Beep(440, 300)
        elif system == "Linux":
            os.system('play -q -n synth 0.3 sine 440 vol 0.6 2>/dev/null; sleep 0.1; play -q -n synth 0.3 sine 440 vol 0.6 2>/dev/null || echo -e "\\a\\a"')
        elif system == "Darwin":
            os.system('afplay /System/Library/Sounds/Glass.aiff 2>/dev/null')
    except: pass

def play_buzzer_sound():
    try:
        system = platform.system()
        if system == "Windows":
            import winsound
            for _ in range(3):
                winsound.Beep(800, 300)
                time.sleep(0.15)
        elif system == "Linux":
            for _ in range(3):
                os.system('speaker-test -t sine -f 800 -l 1 2>/dev/null & pid=$!; sleep 0.3; kill -9 $pid 2>/dev/null')
                time.sleep(0.15)
        elif system == "Darwin":
            for _ in range(3):
                os.system('afplay /System/Library/Sounds/Glass.aiff 2>/dev/null')
                time.sleep(0.15)
        else:
            for _ in range(3):
                print("\a", end="", flush=True)
                time.sleep(0.3)
    except Exception as e:
        print(f"[BUZZER ERROR] {e}")

# === EMAIL FUNCTION ===
def send_email_alert():
    sender = EMAIL_ADDRESS
    password = EMAIL_PASSWORD
    recipient = ALERT_RECIPIENT

    if not all([sender, password, recipient]):
        print("📧 [SKIP] Email config missing in .env")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg['Subject'] = f"🚨 URGENT: Driver Fatigue Alert — Vehicle {VEHICLE_ID}"
        msg['From'] = sender
        msg['To'] = recipient
        msg['X-Priority'] = '1'

        html = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 650px; margin: 20px auto; border: 1px solid #e0e0e0; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
          <div style="background: linear-gradient(135deg, #d32f2f, #b71c1c); color: white; padding: 25px; text-align: center;">
            <h1 style="margin: 0; font-size: 28px;">🚨 DRIVER SAFETY ALERT</h1>
            <p style="margin: 10px 0 0; opacity: 0.9;">Real-Time Fatigue Detection</p>
          </div>
          <div style="padding: 25px; background: #fafafa;">
            <p><b>🕒 Alert Time:</b> {time.strftime('%A, %d %B %Y at %I:%M:%S %p %Z')}</p>
            <p><b>🚗 Vehicle ID:</b> <span style="font-family: monospace; background: #eee; padding: 2px 6px; border-radius: 3px;">{VEHICLE_ID}</span></p>
            <p><b>👤 Driver:</b> {DRIVER_NAME}</p>

            <div style="background: #fff8e1; border-left: 4px solid #ffb300; padding: 15px; margin: 20px 0; border-radius: 0 4px 4px 0;">
              <h3 style="margin-top: 0; color: #5d4037;">⚠️ Critical Observation</h3>
              <p style="font-size: 1.1em; line-height: 1.5; margin: 0;">
                <strong>The driver is currently exhibiting severe signs of drowsiness and frequent yawning.</strong><br>
                Drowsiness count: <b>{state.drowsy_count:.0f}</b> (threshold: {DROWSINESS_ALERT_THRESHOLD})<br>
                Yawn count: <b>{state.yawn_count:.0f}</b> (threshold: {YAWN_ALERT_THRESHOLD})
              </p>
            </div>

            <div style="background: #e8f5e9; border: 1px solid #4caf50; border-radius: 8px; padding: 18px; margin: 20px 0;">
              <h3 style="margin-top: 0; color: #2e7d32;">✅ Recommended Action</h3>
              <ol style="text-align: left; line-height: 1.6;">
                <li><strong>Contact the driver immediately</strong> via phone/radio.</li>
                <li>Advise them to <strong>pull over safely</strong> at the nearest rest area.</li>
                <li>Recommend a <strong>minimum 20-minute power nap</strong> or shift change.</li>
                <li>Do <strong>not</strong> allow continuation of driving until fully alert.</li>
              </ol>
            </div>

            <p style="color: #555; font-size: 0.9em; border-top: 1px dashed #ccc; padding-top: 15px; margin-top: 20px;">
              <i>This alert was generated automatically by the AI-powered Driver Monitoring System.<br>
              System Status: Active | Confidence: High</i>
            </p>
          </div>
        </div>
        """
        msg.attach(MIMEText(html, 'html'))

        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(sender, password)
            server.sendmail(sender, recipient, msg.as_string())
        
        print(f"✅ [EMAIL] Alert sent to {recipient}")
        threading.Thread(target=play_buzzer_sound, daemon=True).start()
        return True

    except Exception as e:
        print(f"❌ [EMAIL FAILED] {e}")
        return False

# === CV HELPERS ===
def eye_aspect_ratio(eye_pts):
    A = dist.euclidean(eye_pts[1], eye_pts[5])
    B = dist.euclidean(eye_pts[2], eye_pts[4])
    C = dist.euclidean(eye_pts[0], eye_pts[3])
    return (A + B) / (2.0 * C)

def final_ear(shape):
    left_eye = shape[[33, 160, 158, 133, 153, 144]]
    right_eye = shape[[362, 385, 387, 263, 373, 380]]
    leftEAR = eye_aspect_ratio(left_eye)
    rightEAR = eye_aspect_ratio(right_eye)
    return (leftEAR + rightEAR) / 2.0

def lip_distance(shape):
    upper = shape[13]
    lower = shape[14]
    return abs(upper[1] - lower[1])

# === FRAME PROCESSING WITH DECAY & 5-SEC BEEP ===
def process_frame(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    rects = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))

    drowsy_this_frame = False
    yawn_this_frame = False
    current_time = time.time()

    if len(rects) > 0:
        idx = np.argmax([w * h for (x, y, w, h) in rects])
        x, y, w, h = rects[idx]
        face_roi = frame[y:y+h, x:x+w]
        rgb_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb_roi)

        if results.multi_face_landmarks:
            h_roi, w_roi = face_roi.shape[:2]
            shape = []
            for lm in results.multi_face_landmarks[0].landmark:
                px = int(lm.x * w_roi) + x
                py = int(lm.y * h_roi) + y
                shape.append([px, py])
            shape = np.array(shape)

            ear = final_ear(shape)
            yawn_dist = lip_distance(shape)

            left_eye_pts = shape[[33, 160, 158, 133, 153, 144]]
            right_eye_pts = shape[[362, 385, 387, 263, 373, 380]]
            mouth_pts = shape[[78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308]]
            for part in [left_eye_pts, right_eye_pts, mouth_pts]:
                hull = cv2.convexHull(part.astype(np.int32))
                cv2.drawContours(frame, [hull], -1, (0, 255, 0), 1)

            if ear < EYE_AR_THRESH:
                drowsy_this_frame = True
            if yawn_dist > YAWN_THRESH:
                yawn_this_frame = True

            cv2.putText(frame, f"EAR: {ear:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 1)
            cv2.putText(frame, f"Yawn: {yawn_dist:.1f}", (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 1)

    # ===== DECAY & ALERT LOGIC =====
    with state.lock:
        # Drowsiness handling
        if drowsy_this_frame:
            state.drowsy_count += 1
            state.last_drowsy_time = current_time
        else:
            elapsed = current_time - state.last_drowsy_time
            if elapsed > 0 and state.drowsy_count > MIN_COUNT:
                decay_factor = 0.5 ** (elapsed / DECAY_HALF_LIFE)
                state.drowsy_count = max(MIN_COUNT, state.drowsy_count * decay_factor)
                state.last_drowsy_time = current_time

        # Yawn handling
        if yawn_this_frame:
            state.yawn_count += 1
            state.last_yawn_time = current_time
        else:
            elapsed = current_time - state.last_yawn_time
            if elapsed > 0 and state.yawn_count > MIN_COUNT:
                decay_factor = 0.5 ** (elapsed / DECAY_HALF_LIFE)
                state.yawn_count = max(MIN_COUNT, state.yawn_count * decay_factor)
                state.last_yawn_time = current_time

        # Trigger alerts — with 5-sec beep
        if state.drowsy_count >= DROWSINESS_ALERT_THRESHOLD and not state.drowsy_alerted:
            state.drowsy_alerted = True
            # 🔊 Play 5-second alert beep in background thread
            threading.Thread(target=play_5sec_alert_beep, daemon=True).start()
            threading.Thread(target=send_email_alert, daemon=True).start()

            threading.Thread(target=send_whatsapp_alert, daemon=True).start()

            print("🚨 HUGE ALERT: 5-sec beep + email + buzzer triggered!")

        if state.yawn_count >= YAWN_ALERT_THRESHOLD and not state.yawn_alerted:
            state.yawn_alerted = True
            threading.Thread(target=play_sound_yawn, daemon=True).start()

    # Overlay UI
    cv2.putText(frame, f"Drowsy: {int(state.drowsy_count)}", (10, frame.shape[0]-60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
    cv2.putText(frame, f"Yawn: {int(state.yawn_count)}", (10, frame.shape[0]-35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)

    if state.drowsy_alerted:
        cv2.putText(frame, "🚨 HUGE DROWSINESS ALERT!", (30, frame.shape[0]//2 - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
    if state.yawn_alerted:
        cv2.putText(frame, "⚠️ YAWN ALERT!", (30, frame.shape[0]//2 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)

    return frame

# === FLASK ROUTES ===
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/detect')
def detect_page():
    return render_template('detect.html')

@app.route('/video_feed')
def video_feed():
    def generate():
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise RuntimeError("❌ Cannot access webcam.")
        time.sleep(2.0)
        try:
            while True:
                success, frame = cap.read()
                if not success:
                    break
                frame = imutils.resize(frame, width=640)
                frame = process_frame(frame)
                ret, buffer = cv2.imencode('.jpg', frame)
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        finally:
            cap.release()
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/status')
def status():
    with state.lock:
        return jsonify({
            'drowsy_count': round(state.drowsy_count, 1),
            'yawn_count': round(state.yawn_count, 1),
            'drowsy_alerted': state.drowsy_alerted,
            'yawn_alerted': state.yawn_alerted
        })

@app.route('/reset')
def reset():
    with state.lock:
        state.drowsy_count = 0
        state.yawn_count = 0
        state.drowsy_alerted = False
        state.yawn_alerted = False
    return jsonify({'status': 'reset'})

if __name__ == '__main__':
    print("="*60)
    print("✅ DRIVER SAFETY MONITOR — MediaPipe + Decay + 5-sec Alert")
    print("="*60)
    print("   Home Page:      http://localhost:5000")
    print("   Detection Page: http://localhost:5000/detect")
    print("   Reset via:      GET /reset")
    print("   Status via:     GET /status")
    print("="*60)
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
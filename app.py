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
from imutils import face_utils
import numpy as np
import imutils
import dlib
import cv2
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)



# === CONFIG ===
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
ALERT_RECIPIENT = os.getenv("ALERT_RECIPIENT", "admin@example.com")
VEHICLE_ID = os.getenv("VEHICLE_ID", "UNKNOWN")
DRIVER_NAME = os.getenv("DRIVER_NAME", "Driver")

def send_whatsapp_alert():
    try:
        phone = "+919550927515" \
        ""  # your number
        msg = f"🚨 Driver {DRIVER_NAME} is drowsy! Vehicle {VEHICLE_ID}"

        pywhatkit.sendwhatmsg_instantly(phone, msg, wait_time=10, tab_close=True)

        print("✅ WhatsApp sent")
    except Exception as e:
        print("❌ WhatsApp error:", e)

EYE_AR_THRESH = 0.28
YAWN_THRESH = 20
DROWSINESS_ALERT_THRESHOLD = 70
YAWN_ALERT_THRESHOLD = 30

class AppState:
    def __init__(self):
        self.drowsy_count = 0
        self.yawn_count = 0
        self.drowsy_alerted = False
        self.yawn_alerted = False
        self.lock = threading.Lock()

state = AppState()

# === MODEL LOADING WITH VALIDATION ===
def load_models():
    print("\n🔍 Loading AI Models...")
    
    # Check predictor file
    predictor_path = 'xce.h5'
    if not os.path.exists(predictor_path):
        raise FileNotFoundError(
            f"\n❌ FATAL: '{predictor_path}' not found.\n"
            "👉 Download from: https://github.com/davisking/dlib-models/raw/master/shape_predictor_68_face_landmarks.dat.bz2\n"
            "👉 Extract with 7-Zip (right-click → 'Extract Here')\n"
            "⚠️ File must be ~95.4 MB (not .bz2!)"
        )
    
    file_size = os.path.getsize(predictor_path)
    if file_size < 90_000_000:
        raise ValueError(
            f"\n❌ Model file too small ({file_size / 1e6:.1f} MB). Expected ~95.4 MB.\n"
            "→ Redownload and extract properly."
        )
    
    try:
        print("   → Loading face detector...")
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        
        print("   → Loading landmark predictor...")
        predictor = dlib.shape_predictor(predictor_path)
        
        print("✅ All models loaded successfully.\n")
        return face_cascade, predictor
    except Exception as e:
        raise RuntimeError(f"Model loading failed: {e}\n{traceback.format_exc()}")

# Load models ONCE at startup (fail fast)
try:
    face_cascade, predictor = load_models()
except Exception as e:
    print(str(e))
    exit(1)

# === SOUND FUNCTIONS ===
def play_sound_huge():
    try:
        system = platform.system()
        if system == "Windows":
            import winsound
            winsound.Beep(200, 800)
        elif system == "Linux":
            os.system('timeout 0.8 play -q -n synth 0.8 sine 200 vol 0.8 2>/dev/null || echo -e "\\a\\a\\a"')
        elif system == "Darwin":
            os.system('afplay /System/Library/Sounds/Sosumi.aiff 2>/dev/null')
    except: pass

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
                Drowsiness count: <b>{state.drowsy_count}</b> (threshold: {DROWSINESS_ALERT_THRESHOLD})<br>
                Yawn count: <b>{state.yawn_count}</b> (threshold: {YAWN_ALERT_THRESHOLD})
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
        threading.Thread(target=send_email_alert, daemon=True).start()
        threading.Thread(target=send_whatsapp_alert, daemon=True).start()
        return True

    except Exception as e:
        print(f"❌ [EMAIL FAILED] {e}")
        return False

# === CV HELPERS ===
def eye_aspect_ratio(eye):
    A = dist.euclidean(eye[1], eye[5])
    B = dist.euclidean(eye[2], eye[4])
    C = dist.euclidean(eye[0], eye[3])
    return (A + B) / (2.0 * C)

def final_ear(shape):
    (lStart, lEnd) = face_utils.FACIAL_LANDMARKS_IDXS["left_eye"]
    (rStart, rEnd) = face_utils.FACIAL_LANDMARKS_IDXS["right_eye"]
    leftEAR = eye_aspect_ratio(shape[lStart:lEnd])
    rightEAR = eye_aspect_ratio(shape[rStart:rEnd])
    return (leftEAR + rightEAR) / 2.0

def lip_distance(shape):
    top = np.concatenate((shape[50:53], shape[61:64]))
    bottom = np.concatenate((shape[56:59], shape[65:68]))
    return abs(np.mean(top, axis=0)[1] - np.mean(bottom, axis=0)[1])

# === FRAME PROCESSING ===
def process_frame(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    rects = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))

    drowsy_this_frame = False
    yawn_this_frame = False

    if len(rects) > 0:
        idx = np.argmax([w * h for (x, y, w, h) in rects])
        x, y, w, h = rects[idx]
        rect = dlib.rectangle(int(x), int(y), int(x + w), int(y + h))
        shape = predictor(gray, rect)  # ← Now SAFE: predictor is validated
        shape = face_utils.shape_to_np(shape)

        ear = final_ear(shape)
        yawn_dist = lip_distance(shape)

        for part in [shape[36:42], shape[42:48], shape[48:60]]:
            cv2.drawContours(frame, [cv2.convexHull(part)], -1, (0, 255, 0), 1)

        if ear < EYE_AR_THRESH:
            drowsy_this_frame = True
        if yawn_dist > YAWN_THRESH:
            yawn_this_frame = True

        cv2.putText(frame, f"EAR: {ear:.2f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 1)
        cv2.putText(frame, f"Yawn: {yawn_dist:.1f}", (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 1)

    with state.lock:
        if drowsy_this_frame:
            state.drowsy_count += 1
        if yawn_this_frame:
            state.yawn_count += 1

        if state.drowsy_count >= DROWSINESS_ALERT_THRESHOLD and not state.drowsy_alerted:
            state.drowsy_alerted = True
            threading.Thread(target=play_sound_huge, daemon=True).start()
            threading.Thread(target=send_email_alert, daemon=True).start()
            print("🚨 HUGE ALERT: Email + Buzzer triggered!")

        if state.yawn_count >= YAWN_ALERT_THRESHOLD and not state.yawn_alerted:
            state.yawn_alerted = True
            threading.Thread(target=play_sound_yawn, daemon=True).start()

    cv2.putText(frame, f"Drowsy: {state.drowsy_count}", (10, frame.shape[0]-60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
    cv2.putText(frame, f"Yawn: {state.yawn_count}", (10, frame.shape[0]-35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)

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
            raise RuntimeError("❌ Cannot access webcam. Check permissions.")
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
            'drowsy_count': state.drowsy_count,
            'yawn_count': state.yawn_count,
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
    print("✅ DRIVER SAFETY MONITORING SYSTEM")
    print("="*60)
    print("   Home Page:      http://localhost:5000")
    print("   Detection Page: http://localhost:5000/detect")
    print("   Quit:           Ctrl+C")
    print("="*60)
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
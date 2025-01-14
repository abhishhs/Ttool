import cv2
import wave
import pyaudio
import threading
from flask import Flask, Response, render_template

# Flask App Initialization
app = Flask(__name__)

# Camera Setup
camera = cv2.VideoCapture(0)  # Default Camera

# Audio Setup
audio_format = pyaudio.paInt16
channels = 1
rate = 44100
chunk = 1024
audio = pyaudio.PyAudio()

audio_stream = audio.open(format=audio_format,
                          channels=channels,
                          rate=rate,
                          input=True,
                          frames_per_buffer=chunk)

# File Names for Storage
video_filename = "output_video.avi"
audio_filename = "output_audio.wav"

# Video Writer Setup
fourcc = cv2.VideoWriter_fourcc(*'XVID')
fps = 20.0
frame_size = (int(camera.get(3)), int(camera.get(4)))
video_writer = cv2.VideoWriter(video_filename, fourcc, fps, frame_size)

# Audio Writer Setup
wavefile = wave.open(audio_filename, 'wb')
wavefile.setnchannels(channels)
wavefile.setsampwidth(audio.get_sample_size(audio_format))
wavefile.setframerate(rate)

# Flags for Recording
recording = True


# Background Thread to Save Camera Frames
def save_camera_frames():
    global recording
    while recording:
        ret, frame = camera.read()
        if ret:
            video_writer.write(frame)


# Background Thread to Save Audio Data
def save_audio_frames():
    global recording
    while recording:
        data = audio_stream.read(chunk)
        wavefile.writeframes(data)


# Flask Routes
@app.route('/')
def index():
    """Renders the Home Page"""
    return """
    <h1>Camera and Microphone Access</h1>
    <ul>
        <li><a href="/video_feed">Live Video Feed</a></li>
        <li><a href="/audio_feed">Live Audio Feed</a></li>
        <li>Check saved files: output_video.avi and output_audio.wav</li>
    </ul>
    """


@app.route('/video_feed')
def video_feed():
    """Stream Video Feed"""
    def generate():
        while True:
            success, frame = camera.read()
            if not success:
                break
            else:
                _, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/audio_feed')
def audio_feed():
    """Stream Audio Feed"""
    def generate_audio():
        while True:
            data = audio_stream.read(chunk)
            yield data
    return Response(generate_audio(), mimetype='audio/wav')


if __name__ == '__main__':
    try:
        # Start Recording Threads
        video_thread = threading.Thread(target=save_camera_frames)
        audio_thread = threading.Thread(target=save_audio_frames)

        video_thread.start()
        audio_thread.start()

        # Start Flask App
        app.run(host='0.0.0.0', port=5000, debug=True)

    finally:
        # Stop Recording and Release Resources
        recording = False
        video_thread.join()
        audio_thread.join()

        camera.release()
        video_writer.release()
        wavefile.close()
        audio_stream.stop_stream()
        audio_stream.close()
        audio.terminate()

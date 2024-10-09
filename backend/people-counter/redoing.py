import signal
import sys
import threading
import base64
from mylib.centroidtracker import CentroidTracker
from mylib.trackableobject import TrackableObject
from imutils.video import VideoStream
from imutils.video import FPS
from mylib.mailer import Mailer
from mylib import config, thread
import time, schedule, csv
import numpy as np
import argparse, imutils
import time, dlib, cv2, datetime
from itertools import zip_longest
from flask import Flask, Response, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import logging

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

logging.basicConfig(level=logging.DEBUG)

output_frames = {}
camera_threads = {}
stop_events = {}
counters = {}

# Global structure to store counts for each camera
counts = {
    "entered": {},
    "exited": {},
    "inside": {}
}

def run_camera(camera_id, url):
    global output_frames, counts

    ap = argparse.ArgumentParser()
    ap.add_argument("-p", "--prototxt", required=False, default="./mobilenet_ssd/MobileNetSSD_deploy.prototxt",
                    help="path to Caffe 'deploy' prototxt file")
    ap.add_argument("-m", "--model", required=False, default="./mobilenet_ssd/MobileNetSSD_deploy.caffemodel",
                    help="path to Caffe pre-trained model")
    ap.add_argument("-c", "--confidence", type=float, default=0.4,
                    help="minimum probability to filter weak detections")
    ap.add_argument("-s", "--skip-frames", type=int, default=30,
                    help="# of skip frames between detections")
    args = vars(ap.parse_args())

    CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat", "bottle", "bus", "car", "cat", "chair", "cow",
               "diningtable", "dog", "horse", "motorbike", "person", "pottedplant", "sheep", "sofa", "train", "tvmonitor"]

    net = cv2.dnn.readNetFromCaffe(args["prototxt"], args["model"])

    vs = VideoStream(url).start()
    time.sleep(2.0)

    writer = None
    W = None
    H = None

    ct = CentroidTracker(maxDisappeared=40, maxDistance=50)
    trackers = []
    trackableObjects = {}

    totalFrames = 0
    totalDown = 0
    totalUp = 0

    fps = FPS().start()

    if config.Thread:
        vs = thread.ThreadingClass(url)

    while not stop_events[camera_id].is_set():
        frame = vs.read()
        frame = frame[1] if isinstance(vs, cv2.VideoCapture) else frame

        if frame is None:
            break

        frame = imutils.resize(frame, width=500)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        if W is None or H is None:
            (H, W) = frame.shape[:2]

        status = "Waiting"
        rects = []

        if totalFrames % args["skip_frames"] == 0:
            status = "Detecting"
            trackers = []

            blob = cv2.dnn.blobFromImage(frame, 0.007843, (W, H), 127.5)
            net.setInput(blob)
            detections = net.forward()

            for i in np.arange(0, detections.shape[2]):
                confidence = detections[0, 0, i, 2]

                if confidence > args["confidence"]:
                    idx = int(detections[0, 0, i, 1])

                    if CLASSES[idx] != "person":
                        continue

                    box = detections[0, 0, i, 3:7] * np.array([W, H, W, H])
                    (startX, startY, endX, endY) = box.astype("int")

                    tracker = dlib.correlation_tracker()
                    rect = dlib.rectangle(startX, startY, endX, endY)
                    tracker.start_track(rgb, rect)

                    trackers.append(tracker)

        else:
            for tracker in trackers:
                status = "Tracking"
                tracker.update(rgb)
                pos = tracker.get_position()

                startX = int(pos.left())
                startY = int(pos.top())
                endX = int(pos.right())
                endY = int(pos.bottom())

                rects.append((startX, startY, endX, endY))

        cv2.line(frame, (0, H // 2), (W, H // 2), (0, 0, 0), 3)
        cv2.putText(frame, "-Prediction border - Entrance-", (10, H - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

        objects = ct.update(rects)

        for (objectID, centroid) in objects.items():
            to = trackableObjects.get(objectID, None)

            if to is None:
                to = TrackableObject(objectID, centroid)
            else:
                y = [c[1] for c in to.centroids]
                direction = centroid[1] - np.mean(y)
                to.centroids.append(centroid)

                if not to.counted:
                    if direction < 0 and centroid[1] < H // 2:
                        totalUp += 1
                        to.counted = True

                    elif direction > 0 and centroid[1] > H // 2:
                        totalDown += 1
                        to.counted = True

            trackableObjects[objectID] = to

            text = "ID {}".format(objectID)
            cv2.putText(frame, text, (centroid[0] - 10, centroid[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            cv2.circle(frame, (centroid[0], centroid[1]), 4, (0, 0, 255), -1)

        counts["entered"][camera_id] = totalDown
        counts["exited"][camera_id] = totalUp
        counts["inside"][camera_id] = totalDown - totalUp

        if writer is not None:
            writer.write(frame)

        _, buffer = cv2.imencode('.jpg', frame)
        b_frame = base64.b64encode(buffer).decode('utf-8')
        socketio.emit('video_feed', {'camera_id': camera_id, 'frame': b_frame}, namespace='/video')
        socketio.emit('count', {'camera_id': camera_id, 'count': counts}, namespace='/video')

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

        totalFrames += 1
        fps.update()

    fps.stop()
    print("[INFO] elapsed time: {:.2f}".format(fps.elapsed()))
    print("[INFO] approx. FPS: {:.2f}".format(fps.fps()))

    if writer is not None:
        writer.release()

    if isinstance(vs, VideoStream):
        vs.stop()
    elif isinstance(vs, thread.ThreadingClass):
        vs.stop()
    cv2.destroyAllWindows()

@socketio.on('connect', namespace='/video')
def test_connect():
    print('Client connected')

@socketio.on('disconnect', namespace='/video')
def test_disconnect():
    print('Client disconnected')

def is_valid_camera_link(camera_link):
    cap = cv2.VideoCapture(camera_link)
    if not cap.isOpened():
        return False
    cap.release()
    return True

@app.route('/add_camera', methods=['POST'])
def add_camera():
    try:
        data = request.get_json()
        camera_id = data.get('camera_id')
        camera_link = data.get('camera_link')

        if not camera_id or not camera_link:
            return jsonify({'error': 'Missing camera_id or camera_link'}), 400

        if not is_valid_camera_link(camera_link):
            return jsonify({'error': 'Invalid camera_link'}), 400

        if camera_id in camera_threads:
            return jsonify({'error': 'Camera ID already exists'}), 400

        stop_events[camera_id] = threading.Event()
        camera_threads[camera_id] = threading.Thread(target=run_camera, args=(camera_id, camera_link))
        camera_threads[camera_id].start()

        return jsonify({'message': f'Camera {camera_id} added'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/remove_camera', methods=['POST'])
def remove_camera():
    data = request.get_json()
    camera_id = data.get('camera_id')

    if not camera_id:
        return jsonify({'error': 'Missing camera_id'}), 400

    if camera_id not in camera_threads:
        return jsonify({'error': 'Camera ID not found'}), 404

    stop_events[camera_id].set()
    camera_threads[camera_id].join()

    del camera_threads[camera_id]
    del stop_events[camera_id]
    del counts["entered"][camera_id]
    del counts["exited"][camera_id]
    del counts["inside"][camera_id]

    return jsonify({'message': f'Camera {camera_id} removed'}), 200

@app.route('/count', methods=['GET'])
def get_count():
    return jsonify(counts)

def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    for camera_id in camera_threads.copy():
        remove_camera(camera_id)
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False, allow_unsafe_werkzeug=True)
import signal
import sys
import threading
import cv2
import dlib
import numpy as np
import argparse
import imutils
from imutils.video import VideoStream, FPS
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk
from mylib.centroidtracker import CentroidTracker
from mylib.trackableobject import TrackableObject

# Global variables
output_frame = None
stop_event = threading.Event()
lock = threading.Lock()

# Tracker variables
totalUp = 0
totalDown = 0
W = None
H = None
totalFrames = 0

def run_video_processing():

    CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat",
           "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
           "dog", "horse", "motorbike", "person", "pottedplant",
           "sheep", "sofa", "train", "tvmonitor"]


    global output_frame, totalUp, totalDown, W, H, totalFrames

    ap = argparse.ArgumentParser()
    ap.add_argument("-p", "--prototxt", required=False, default="./mobilenet_ssd/MobileNetSSD_deploy.prototxt",
                    help="path to Caffe 'deploy' prototxt file")
    ap.add_argument("-m", "--model", required=False, default="./mobilenet_ssd/MobileNetSSD_deploy.caffemodel",
                    help="path to Caffe pre-trained model")
    ap.add_argument("-i", "--input", type=str,
                    help="path to optional input video file")
    ap.add_argument("-o", "--output", type=str,
                    help="path to optional output video file")
    ap.add_argument("-c", "--confidence", type=float, default=0.4,
                    help="minimum probability to filter weak detections")
    ap.add_argument("-s", "--skip-frames", type=int, default=30,
                    help="# of skip frames between detections")
    args = vars(ap.parse_args())

    # Load the serialized model from disk
    net = cv2.dnn.readNetFromCaffe(args["prototxt"], args["model"])

    # Start the video stream
    if not args.get("input", False):
        vs = VideoStream(src=0).start()
        time.sleep(2.0)
    else:
        vs = cv2.VideoCapture(args["input"])

    # Initialize the centroid tracker and frame dimensions
    ct = CentroidTracker(maxDisappeared=40, maxDistance=50)
    trackers = []
    trackableObjects = {}

    fps = FPS().start()

    while not stop_event.is_set():
        frame = vs.read()
        frame = frame[1] if args.get("input", False) else frame

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
        cv2.putText(frame, "-Prediction border - Entrance-", (10, H - 50),
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

        info = [
            ("Exited", totalUp),
            ("Entered", totalDown),
            ("Status", status),
        ]

        info2 = [
            ("Total people inside", totalDown - totalUp),
        ]

        for (i, (k, v)) in enumerate(info):
            text = "{}: {}".format(k, v)
            cv2.putText(frame, text, (10, H - ((i * 20) + 20)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        for (i, (k, v)) in enumerate(info2):
            text = "{}: {}".format(k, v)
            cv2.putText(frame, text, (265, H - ((i * 20) + 60)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

        with lock:
            output_frame = frame.copy()

        totalFrames += 1
        fps.update()

    fps.stop()

    vs.stop() if not args.get("input", False) else vs.release()

def update_gui(canvas, img_label, count_label):
    global output_frame, totalUp, totalDown

    with lock:
        if output_frame is not None:
            frame = cv2.cvtColor(output_frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            img_tk = ImageTk.PhotoImage(image=img)
            img_label.img_tk = img_tk  # Keep a reference
            img_label.configure(image=img_tk)

    count_label.config(text=f"Entered: {totalDown}, Exited: {totalUp}")
    canvas.after(10, update_gui, canvas, img_label, count_label)

def start_gui():
    root = tk.Tk()
    root.title("People Counter")

    canvas = tk.Canvas(root, width=600, height=400)
    canvas.pack()

    img_label = ttk.Label(canvas)
    img_label.pack()

    count_label = ttk.Label(root, text="Entered: 0, Exited: 0")
    count_label.pack()

    # Start video processing in a separate thread
    video_thread = threading.Thread(target=run_video_processing, daemon=True)
    video_thread.start()

    # Start GUI update loop
    update_gui(canvas, img_label, count_label)

    root.mainloop()

def signal_handler(sig, frame):
    global stop_event
    stop_event.set()
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    start_gui()

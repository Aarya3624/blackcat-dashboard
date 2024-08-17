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
from tkinter import ttk, simpledialog, messagebox
from mylib.centroidtracker import CentroidTracker
from mylib.trackableobject import TrackableObject

# Global variables
output_frames = {}
camera_trackers = {}
stop_event = threading.Event()
lock = threading.Lock()

def run_video_processing(camera_id, video_source, update_counts):
    CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat",
               "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
               "dog", "horse", "motorbike", "person", "pottedplant",
               "sheep", "sofa", "train", "tvmonitor"]

    global output_frames, camera_trackers

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

    # Load the serialized model from disk
    net = cv2.dnn.readNetFromCaffe(args["prototxt"], args["model"])

    # Start the video stream
    if isinstance(video_source, int):
        vs = VideoStream(src=video_source).start()
        time.sleep(2.0)
    else:
        vs = cv2.VideoCapture(video_source)

    # Initialize the centroid tracker and frame dimensions
    ct = CentroidTracker(maxDisappeared=40, maxDistance=50)
    trackers = []
    trackableObjects = {}
    totalUp = 0
    totalDown = 0
    W = None
    H = None
    totalFrames = 0

    fps = FPS().start()

    while not stop_event.is_set():
        frame = vs.read()
        frame = frame[1] if not isinstance(video_source, int) else frame

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
            output_frames[camera_id] = frame.copy()

        totalFrames += 1
        fps.update()

    fps.stop()

    vs.stop() if isinstance(video_source, int) else vs.release()

    update_counts(camera_id, totalUp, totalDown)

def update_gui(camera_id, img_label, count_label):
    global output_frames, camera_trackers

    with lock:
        if camera_id in output_frames:
            frame = cv2.cvtColor(output_frames[camera_id], cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            img_tk = ImageTk.PhotoImage(image=img)
            img_label.img_tk = img_tk  # Keep a reference
            img_label.configure(image=img_tk)

            if camera_id in camera_trackers:
                count_label.config(text=f"Entered: {camera_trackers[camera_id]['down']}, Exited: {camera_trackers[camera_id]['up']}")

    img_label.after(10, update_gui, camera_id, img_label, count_label)

def start_gui():
    root = tk.Tk()
    root.title("People Counter Dashboard")
    root.geometry("1024x768")

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("TButton", padding=6, relief="flat", background="#0078d7", foreground="#ffffff")
    style.configure("TLabel", background="#f0f0f0", font=("Arial", 12))
    style.configure("TFrame", background="#ffffff")

    notebook = ttk.Notebook(root)
    notebook.pack(expand=1, fill='both')

    people_counter_tab = ttk.Frame(notebook)
    notebook.add(people_counter_tab, text="People Counter")

    add_camera_button = ttk.Button(people_counter_tab, text="Add Camera", command=lambda: add_camera(notebook, people_counter_tab))
    add_camera_button.pack(pady=10)

    root.mainloop()

def add_camera(notebook, people_counter_tab):
    camera_id = simpledialog.askstring("Camera ID", "Enter Camera ID:")
    hall_number = simpledialog.askstring("Hall Number", "Enter Hall Number:")
    camera_url = simpledialog.askstring("Camera URL", "Enter Camera URL:")

    if camera_id and hall_number and camera_url:
        camera_frame = ttk.Frame(notebook)
        camera_frame.pack(fill="both", expand=True)

        img_label = ttk.Label(camera_frame)
        img_label.pack()

        count_label = ttk.Label(camera_frame, text="Entered: 0, Exited: 0")
        count_label.pack(pady=10)

        # Add the camera_frame to the notebook
        notebook.add(camera_frame, text=f"Camera {camera_id} - Hall {hall_number}")

        camera_trackers[camera_id] = {"up": 0, "down": 0}

        def update_counts(camera_id, total_up, total_down):
            with lock:
                camera_trackers[camera_id]["up"] = total_up
                camera_trackers[camera_id]["down"] = total_down

        # Start video processing in a separate thread
        def start_processing():
            threading.Thread(target=run_video_processing, args=(camera_id, camera_url, update_counts), daemon=True).start()
            update_gui(camera_id, img_label, count_label)

        start_processing()
    else:
        messagebox.showerror("Input Error", "All fields must be filled out.")

if __name__ == "__main__":
    start_gui()


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
from tkinter import ttk, messagebox
from mylib.centroidtracker import CentroidTracker
from mylib.trackableobject import TrackableObject

# Global variables
output_frames = {}
camera_trackers = {}
stop_event = threading.Event()
lock = threading.Lock()
PLACEHOLDER_IMAGE = "path_to_placeholder_image.png"  # Path to your placeholder image

def run_video_processing(camera_id, video_source, update_counts):
    CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat",
               "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
               "dog", "horse", "motorbike", "person", "pottedplant",
               "sheep", "sofa", "train", "tvmonitor"]

    global output_frames, camera_trackers

    prototxt = "./mobilenet_ssd/MobileNetSSD_deploy.prototxt"
    model = "./mobilenet_ssd/MobileNetSSD_deploy.caffemodel"
    confidence_threshold = 0.4
    skip_frames = 30

    net = cv2.dnn.readNetFromCaffe(prototxt, model)

    if isinstance(video_source, int):
        vs = VideoStream(src=video_source).start()
        time.sleep(2.0)
    else:
        vs = cv2.VideoCapture(video_source)

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
            frame = np.zeros((150, 200, 3), dtype=np.uint8)  # Placeholder size
            frame[:] = (255, 0, 0)  # Red background to indicate an error
            cv2.putText(frame, "No video feed", (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            with lock:
                output_frames[camera_id] = frame
            continue

        frame = imutils.resize(frame, width=500)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        if W is None or H is None:
            (H, W) = frame.shape[:2]

        status = "Waiting"
        rects = []

        if totalFrames % skip_frames == 0:
            status = "Detecting"
            trackers = []

            blob = cv2.dnn.blobFromImage(frame, 0.007843, (W, H), 127.5)
            net.setInput(blob)
            detections = net.forward()

            for i in np.arange(0, detections.shape[2]):
                confidence = detections[0, 0, i, 2]

                if confidence > confidence_threshold:
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

        cv2.putText(frame, f"Entered: {totalDown}", (10, H - 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        cv2.putText(frame, f"Exited: {totalUp}", (10, H - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

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
    root.geometry("1200x800")

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("TButton", padding=6, relief="flat", background="#0078d7", foreground="#ffffff")
    style.configure("TLabel", background="#f0f0f0", font=("Arial", 12))
    style.configure("TFrame", background="#ffffff")

    notebook = ttk.Notebook(root)
    notebook.pack(expand=1, fill='both')

    people_counter_tab = ttk.Frame(notebook)
    notebook.add(people_counter_tab, text="Add Cameras")

    # Create input fields for Camera ID, Hall Number, and Camera URL
    camera_id_label = ttk.Label(people_counter_tab, text="Camera ID:")
    camera_id_label.pack(pady=5)
    camera_id_entry = ttk.Entry(people_counter_tab)
    camera_id_entry.pack(pady=5)

    hall_number_label = ttk.Label(people_counter_tab, text="Hall Number:")
    hall_number_label.pack(pady=5)
    hall_number_entry = ttk.Entry(people_counter_tab)
    hall_number_entry.pack(pady=5)

    camera_url_label = ttk.Label(people_counter_tab, text="Camera URL:")
    camera_url_label.pack(pady=5)
    camera_url_entry = ttk.Entry(people_counter_tab)
    camera_url_entry.pack(pady=5)

    def add_camera():
        camera_id = camera_id_entry.get().strip()
        hall_number = hall_number_entry.get().strip()
        camera_url = camera_url_entry.get().strip()

        if not camera_id or not hall_number or not camera_url:
            messagebox.showerror("Input Error", "All fields are required.")
            return

        try:
            camera_id = int(camera_id)
        except ValueError:
            messagebox.showerror("Input Error", "Camera ID must be a number.")
            return

        if camera_id in camera_trackers:
            messagebox.showerror("Error", f"Camera ID {camera_id} already exists.")
            return

        hall_tab = None
        for tab in notebook.tabs():
            if notebook.tab(tab, "text") == f"Hall {hall_number}":
                hall_tab = tab
                break

        if hall_tab is None:
            hall_tab = ttk.Frame(notebook)
            notebook.add(hall_tab, text=f"Hall {hall_number}")

        hall_frame = notebook.nametowidget(hall_tab)
        camera_count = len(hall_frame.winfo_children())

        # Define the grid layout
        rows = 2
        cols = 3
        row = camera_count // cols
        col = camera_count % cols

        new_camera_frame = ttk.Frame(hall_frame, width=200, height=150)
        new_camera_frame.grid(row=row, column=col, padx=5, pady=5, sticky='nsew')

        new_camera_label = ttk.Label(new_camera_frame, text=f"Camera {camera_id} - Hall {hall_number}")
        new_camera_label.pack(side="top")

        new_camera_img_label = ttk.Label(new_camera_frame)
        new_camera_img_label.pack(side="left", expand=True, fill="both")

        camera_trackers[camera_id] = {'up': 0, 'down': 0}

        def update_counts(camera_id, up, down):
            camera_trackers[camera_id]['up'] = up
            camera_trackers[camera_id]['down'] = down

        camera_thread = threading.Thread(target=run_video_processing, args=(camera_id, camera_url, update_counts))
        camera_thread.start()

        update_gui(camera_id, new_camera_img_label, new_camera_img_label)

    add_camera_button = ttk.Button(people_counter_tab, text="Add Camera", command=add_camera)
    add_camera_button.pack(pady=10)

    def on_closing():
        stop_event.set()
        root.destroy()
        sys.exit()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    start_gui()
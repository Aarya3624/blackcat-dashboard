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
import logging
from datetime import datetime

# Global variables
output_frames = {}
camera_trackers = {}
stop_event = threading.Event()
lock = threading.Lock()
PLACEHOLDER_IMAGE = "path_to_placeholder_image.png"  # Path to your placeholder image

# Set up logging
logging.basicConfig(filename='hall_log.txt', level=logging.INFO, format='%(asctime)s - %(message)s')

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
                        # Log entry
                        logging.info(f"Camera ID {camera_id} - Entered")
                    elif direction > 0 and centroid[1] > H // 2:
                        totalDown += 1
                        to.counted = True
                        # Log exit
                        logging.info(f"Camera ID {camera_id} - Exited")

            trackableObjects[objectID] = to

            text = "ID {}".format(objectID)
            cv2.putText(frame, text, (centroid[0] - 10, centroid[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            cv2.circle(frame, (centroid[0], centroid[1]), 4, (0, 0, 255), -1)

        # Overlay entered and exited counts inside the video
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

def update_gui(camera_id, img_label):
    global output_frames

    with lock:
        if camera_id in output_frames:
            frame = cv2.cvtColor(output_frames[camera_id], cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame)
            img_tk = ImageTk.PhotoImage(image=img)
            img_label.img_tk = img_tk  # Keep a reference
            img_label.configure(image=img_tk)

    img_label.after(10, update_gui, camera_id, img_label)

def start_gui():
    root = tk.Tk()
    root.title("People Counter Dashboard")
    root.geometry("1200x800")
    root.configure(bg="#2E2E2E")  # Dark background

    style = ttk.Style()
    style.theme_use("clam")

    # Style configurations for dark mode and glassy effect
    style.configure("TButton", 
                    padding=8, 
                    relief="flat", 
                    background="#3A3A3A", 
                    foreground="#FFFFFF", 
                    font=("Arial", 12),
                    borderwidth=0)
    style.map("TButton",
              background=[("active", "#555555")])

    style.configure("TLabel", 
                    background="#2E2E2E", 
                    foreground="#FFFFFF", 
                    font=("Arial", 12))

    style.configure("TFrame", 
                    background="#2E2E2E")

    style.configure("TNotebook",
                    background="#2E2E2E", 
                    borderwidth=0, 
                    font=("Arial", 12))

    style.configure("TNotebook.Tab",
                    background="#3A3A3A",
                    foreground="#FFFFFF",
                    padding=[10, 5],
                    font=("Arial", 12),
                    borderwidth=0)
    style.map("TNotebook.Tab",
              background=[("selected", "#555555")],
              foreground=[("selected", "#FFFFFF")])

    # Header Frame
    header_frame = ttk.Frame(root, padding=(10, 5), style="TFrame")
    header_frame.pack(fill='x', padx=10, pady=10)

    header_label = ttk.Label(header_frame, text="People Counter Dashboard", font=("Arial", 16, "bold"))
    header_label.pack()

    instructions_label = ttk.Label(header_frame, text="Add cameras to track people count in different halls.", font=("Arial", 12))
    instructions_label.pack()

    # Camera setup frame
    setup_frame = ttk.Frame(root, padding=(10, 5), style="TFrame")
    setup_frame.pack(fill='x', padx=10, pady=10)

    ttk.Label(setup_frame, text="Camera ID:").grid(row=0, column=0, padx=5, pady=5)
    camera_id_entry = ttk.Entry(setup_frame)
    camera_id_entry.grid(row=0, column=1, padx=5, pady=5)

    ttk.Label(setup_frame, text="Hall Number:").grid(row=1, column=0, padx=5, pady=5)
    hall_number_entry = ttk.Entry(setup_frame)
    hall_number_entry.grid(row=1, column=1, padx=5, pady=5)

    ttk.Label(setup_frame, text="Camera URL/Index:").grid(row=2, column=0, padx=5, pady=5)
    camera_url_entry = ttk.Entry(setup_frame)
    camera_url_entry.grid(row=2, column=1, padx=5, pady=5)

    add_camera_button = ttk.Button(setup_frame, text="Add Camera", command=lambda: add_camera(camera_id_entry, hall_number_entry, camera_url_entry))
    add_camera_button.grid(row=3, column=0, columnspan=2, pady=10)

    # Notebook for halls
    notebook = ttk.Notebook(root)
    notebook.pack(fill='both', expand=True)

    def add_camera(camera_id_entry, hall_number_entry, camera_url_entry):
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
            hall_tab = ttk.Frame(notebook, style="TFrame")
            notebook.add(hall_tab, text=f"Hall {hall_number}")

        hall_frame = notebook.nametowidget(hall_tab)
        camera_count = len(hall_frame.winfo_children())

        # Define the grid layout
        rows = 2
        cols = 3
        row = camera_count // cols
        col = camera_count % cols

        new_camera_frame = ttk.Frame(hall_frame, width=250, height=200, padding=5, style="TFrame")
        new_camera_frame.grid(row=row, column=col, padx=5, pady=5, sticky='nsew')

        new_camera_label = ttk.Label(new_camera_frame, text=f"Camera {camera_id} - Hall {hall_number}", font=("Arial", 12, "bold"))
        new_camera_label.pack(side="top", pady=(0, 5))

        new_camera_img_label = ttk.Label(new_camera_frame)
        new_camera_img_label.pack(side="left", expand=True, fill="both")

        camera_trackers[camera_id] = {'up': 0, 'down': 0}

        # Initialize logging for the hall
        if hall_number not in hall_logs:
            hall_logs[hall_number] = []
            hall_log_label = ttk.Label(hall_frame, text="", font=("Arial", 10), background="#2E2E2E", foreground="#FFFFFF", anchor="w")
            hall_log_label.grid(row=camera_count // cols + 1, column=0, columnspan=cols, padx=5, pady=5, sticky='w')
            hall_log_labels[hall_number] = hall_log_label

        def update_counts(camera_id, up, down):
            camera_trackers[camera_id]['up'] = up
            camera_trackers[camera_id]['down'] = down

            # Update the logs for the relevant hall
            log_event(hall_number, camera_id, "Person entered" if down > camera_trackers[camera_id]['down'] else "Person exited")

        camera_thread = threading.Thread(target=run_video_processing, args=(camera_id, camera_url, update_counts))
        camera_thread.start()

        update_gui(camera_id, new_camera_img_label)

    def log_event(hall_number, camera_id, event_type):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} - Camera {camera_id}: {event_type} in Hall {hall_number}"
        
        # Write the log entry to a file specific to the hall
        log_file_path = f"hall_{hall_number}_log.txt"
        with open(log_file_path, "a") as log_file:
            log_file.write(log_entry + "\n")
        
        # Update the GUI with the new log entry
        if hall_number in hall_logs:
            hall_logs[hall_number].append(log_entry)
            hall_log_labels[hall_number].configure(text="\n".join(hall_logs[hall_number]))

    hall_logs = {}
    hall_log_labels = {}

    root.protocol("WM_DELETE_WINDOW", lambda: stop_event.set() or root.destroy())
    root.mainloop()

if __name__ == "__main__":
    start_gui()

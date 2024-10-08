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
from tkinter import ttk, messagebox, filedialog
from mylib.centroidtracker import CentroidTracker
from mylib.trackableobject import TrackableObject
import logging
from datetime import datetime
import csv
from tkcalendar import DateEntry
import datetime
import time

# Global variables
output_frames = {}
camera_trackers = {}
stop_event = threading.Event()
lock = threading.Lock()
PLACEHOLDER_IMAGE = "path_to_placeholder_image.png"  # Path to your placeholder image

logging.basicConfig(filename='app.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Set up logging


def log_to_csv(camera_id, hall_id, timestamp, entered, exited):
    try:
        with open('hall_log.csv', 'a', newline='') as csvfile:
            fieldnames = ['camera_id', 'hall_id',
                          'timestamp', 'entered', 'exited']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            # Check if the file is empty, if so, write the header
            if csvfile.tell() == 0:
                writer.writeheader()
            writer.writerow({'camera_id': camera_id, 'hall_id': hall_id, 'timestamp': timestamp,
                            'entered': entered, 'exited': exited})
    except IOError as e:
        logging.error(f"Failed to log to CSV: {e}")


def download_log(hall_number):
    def download():
        try:
            start_date = start_date_entry.get_date()
            start_time_obj = datetime.time(
                hour=int(start_hour_var.get()), minute=int(start_minute_var.get()))
            start_time = datetime.combine(start_date, start_time_obj)

            end_date = end_date_entry.get_date()
            end_time_obj = datetime.time(
                hour=int(end_hour_var.get()), minute=int(end_minute_var.get()))
            end_time = datetime.combine(end_date, end_time_obj)

            file_path = filedialog.asksaveasfilename(defaultextension=".csv")
            if not file_path:
                return  # User canceled

            with open(file_path, 'w', newline='') as csvfile:
                fieldnames = ['camera_id', 'hall_id',
                              'timestamp', 'entered', 'exited']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                with open('hall_log.csv', 'r') as main_logfile:
                    reader = csv.DictReader(main_logfile)
                    for row in reader:
                        timestamp = datetime.strptime(
                            row['timestamp'], "%Y-%m-%d %H:%M:%S")
                        if start_time <= timestamp <= end_time:
                            writer.writerow(row)

            messagebox.showinfo("Download Complete",
                                "Log downloaded successfully!")
        except ValueError:
            messagebox.showerror("Error", "Invalid date/time format.")
        except Exception as e:
            logging.error(f"Error downloading log: {e}")
            messagebox.showerror("Error", "Failed to download log.")
    threading.Thread(target=download).start()

    download_window = tk.Toplevel()
    download_window.title("Download Log")

    # Start Date
    start_date_label = ttk.Label(download_window, text="Start Date:")
    start_date_label.grid(row=0, column=0, padx=5, pady=5)
    start_date_entry = DateEntry(download_window, width=12, background='darkblue',
                                 foreground='white', borderwidth=2)
    start_date_entry.grid(row=0, column=1, padx=5, pady=5)

    # Start Time
    start_hour_var = tk.StringVar(value="00")
    start_minute_var = tk.StringVar(value="00")
    ttk.Label(download_window, text="Start Time:").grid(
        row=1, column=0, padx=5, pady=5)
    start_hour_spinbox = ttk.Spinbox(
        download_window, from_=0, to=23, textvariable=start_hour_var, width=3)
    start_hour_spinbox.grid(row=1, column=1, padx=5, pady=5, sticky="w")
    ttk.Label(download_window, text=":").grid(row=1, column=2, pady=5)
    start_minute_spinbox = ttk.Spinbox(
        download_window, from_=0, to=59, textvariable=start_minute_var, width=3)
    start_minute_spinbox.grid(row=1, column=3, padx=5, pady=5, sticky="w")

    # End Date
    end_date_label = ttk.Label(download_window, text="End Date:")
    end_date_label.grid(row=2, column=0, padx=5, pady=5)
    end_date_entry = DateEntry(download_window, width=12, background='darkblue',
                               foreground='white', borderwidth=2)
    end_date_entry.grid(row=2, column=1, padx=5, pady=5)

    # End Time
    end_hour_var = tk.StringVar(value="23")
    end_minute_var = tk.StringVar(value="59")
    ttk.Label(download_window, text="End Time:").grid(
        row=3, column=0, padx=5, pady=5)
    end_hour_spinbox = ttk.Spinbox(
        download_window, from_=0, to=23, textvariable=end_hour_var, width=3)
    end_hour_spinbox.grid(row=3, column=1, padx=5, pady=5, sticky="w")
    ttk.Label(download_window, text=":").grid(row=3, column=2, pady=5)
    end_minute_spinbox = ttk.Spinbox(
        download_window, from_=0, to=59, textvariable=end_minute_var, width=3)
    end_minute_spinbox.grid(row=3, column=3, padx=5, pady=5, sticky="w")

    download_button = ttk.Button(
        download_window, text="Download", command=download)
    download_button.grid(row=4, column=0, columnspan=4, pady=10)


def log_event(hall_number, camera_id, event_type):
    try:
        timestamp = datetime.time.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} - Camera {camera_id}: {event_type} in Hall {hall_number}"

        log_file_path = f"hall_{hall_number}_log.txt"
        with open(log_file_path, "a") as log_file:
            log_file.write(log_entry + "\n")

        if hall_number in hall_logs:
            hall_logs[hall_number].append(log_entry)
            hall_log_labels[hall_number].configure(
                text="\n".join(hall_logs[hall_number]))

    except Exception as e:
        logging.error(
            f"Failed to log event for hall {hall_number}: {e}")


def run_video_processing(camera_id, hall_id, video_source, update_counts):
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

    # Determine if the video source is a webcam or an RTSP URL
    try:
        # Try converting video_source to an integer (for webcams)
        video_source = int(video_source)
        vs = VideoStream(src=video_source).start()
        time.sleep(2.0)
    except ValueError:
        # If not an integer, assume it's an RTSP URL
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
            cv2.putText(frame, "No video feed", (10, 75),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
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
            rects = []

            blob = cv2.dnn.blobFromImage(
                frame, 0.007843, (W, H), 127.5)
            net.setInput(blob)
            detections = net.forward()

            rects = []
            for i in np.arange(0, detections.shape[2]):
                confidence = detections[0, 0, i, 2]

                if confidence > confidence_threshold:
                    idx = int(detections[0, 0, i, 1])

                    if CLASSES[idx] != "person":
                        continue

                    box = detections[0, 0, i, 3:7] * \
                        np.array([W, H, W, H])
                    (startX, startY, endX, endY) = box.astype("int")

                    tracker = dlib.correlation_tracker()
                    rect = dlib.rectangle(startX, startY, endX, endY)
                    tracker.start_track(rgb, rect)

                    trackers.append(tracker)
        else:
            status = "Tracking"
            for tracker in trackers:
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
                        log_to_csv(camera_id, hall_id, datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"), 1, 0)  # Log to CSV
                    elif direction > 0 and centroid[1] > H // 2:
                        totalDown += 1
                        to.counted = True
                        # Log exit
                        log_to_csv(camera_id, hall_id, datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"), 0, 1)  # Log to CSV

            trackableObjects[objectID] = to

            text = "ID {}".format(objectID)
            cv2.putText(frame, text, (centroid[0] - 10, centroid[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            cv2.circle(frame, (centroid[0], centroid[1]),
                       4, (0, 0, 255), -1)

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


def update_gui(camera_id, img_label, count_label):
    global output_frames

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


def signal_handler(sig, frame):
    logging.info("Signal received, shutting down...")
    stop_event.set()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


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

    header_label = ttk.Label(header_frame, text="People Counter Dashboard",
                             font=("Arial", 16, "bold"))
    header_label.pack()

    instructions_label = ttk.Label(
        header_frame, text="Add cameras to track people count in different halls.", font=("Arial", 12))
    instructions_label.pack()

    # Camera setup frame
    setup_frame = ttk.Frame(root, padding=(10, 5), style="TFrame")
    setup_frame.pack(fill='x', padx=10, pady=10)

    ttk.Label(setup_frame, text="Camera ID:").grid(
        row=0, column=0, padx=5, pady=5)
    camera_id_entry = ttk.Entry(setup_frame)
    camera_id_entry.grid(row=0, column=1, padx=5, pady=5)

    ttk.Label(setup_frame, text="Hall Number:").grid(
        row=1, column=0, padx=5, pady=5)
    hall_number_entry = ttk.Entry(setup_frame)
    hall_number_entry.grid(row=1, column=1, padx=5, pady=5)

    ttk.Label(setup_frame, text="Camera URL/Index:").grid(
        row=2, column=0, padx=5, pady=5)
    camera_url_entry = ttk.Entry(setup_frame)
    camera_url_entry.grid(row=2, column=1, padx=5, pady=5)

    add_camera_button = ttk.Button(setup_frame, text="Add Camera", command=lambda: add_camera(
        camera_id_entry, hall_number_entry, camera_url_entry))
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
            messagebox.showerror(
                "Error", f"Camera ID {camera_id} already exists.")
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

        new_camera_frame = ttk.Frame(
            hall_frame, width=250, height=200, padding=5, style="TFrame")
        new_camera_frame.grid(row=row, column=col, padx=5,
                              pady=5, sticky='nsew')

        new_camera_label = ttk.Label(new_camera_frame, text=f"Camera {camera_id} - Hall {hall_number}",
                                     font=("Arial", 12, "bold"))
        new_camera_label.pack(side="top", pady=(0, 5))

        new_camera_img_label = ttk.Label(new_camera_frame)
        new_camera_img_label.pack(side="left", expand=True, fill="both")

        count_label = ttk.Label(new_camera_frame, text="", font=("Arial", 10))
        count_label.pack(side="top", pady=(0, 5))

        camera_trackers[camera_id] = {'up': 0, 'down': 0}

        # Initialize logging for the hall
        if hall_number not in hall_logs:
            hall_logs[hall_number] = []
            hall_log_label = ttk.Label(hall_frame, text="", font=("Arial", 10), background="#2E2E2E",
                                       foreground="#FFFFFF", anchor="w")
            hall_log_label.grid(row=camera_count // cols + 1, column=0,
                                columnspan=cols, padx=5, pady=5, sticky='w')
            hall_log_labels[hall_number] = hall_log_label

        def update_counts(camera_id, up, down):
            camera_trackers[camera_id]['up'] = up
            camera_trackers[camera_id]['down'] = down

            # Update the logs for the relevant hall
            log_event(hall_number, camera_id, "Person entered" if down >
                      camera_trackers[camera_id]['down'] else "Person exited")

        camera_thread = threading.Thread(
            target=run_video_processing, args=(camera_id, hall_number, camera_url, update_counts))
        camera_thread.start()

        update_gui(camera_id, new_camera_img_label, count_label)

        # Add download button for the hall
        download_button = ttk.Button(hall_frame, text="Download Log",
                                     command=lambda: download_log(hall_number))
        download_button.grid(
            row=camera_count // 3 + 2, column=0, columnspan=3, pady=10)

    def log_event(hall_number, camera_id, event_type):
        timestamp = datetime.time.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"{timestamp} - Camera {camera_id}: {event_type} in Hall {hall_number}"

        # Write the log entry to a file specific to the hall
        log_file_path = f"hall_{hall_number}_log.txt"
        with open(log_file_path, "a") as log_file:
            log_file.write(log_entry + "\n")

        # Update the GUI with the new log entry
        if hall_number in hall_logs:
            hall_logs[hall_number].append(log_entry)
            hall_log_labels[hall_number].configure(
                text="\n".join(hall_logs[hall_number]))

    hall_logs = {}
    hall_log_labels = {}

    root.protocol("WM_DELETE_WINDOW", lambda: stop_event.set()
                  or root.destroy())
    root.mainloop()


if __name__ == "__main__":
    start_gui()
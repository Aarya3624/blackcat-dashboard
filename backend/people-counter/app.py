import signal
import sys
import threading
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

# Create Flask app
app = Flask(__name__)
CORS(app)

# Global variable to store the current frame
output_frame = None
video_thread = None
stop_event = threading.Event()

totalUp = 0
totalDown = 0

# Python main.py --prototxt mobilenet_ssd/MobileNetSSD_deploy.prototxt --model mobilenet_ssd/MobileNetSSD_deploy.caffemodel --input videos/example_01.mp4

t0 = time.time()

def run():
    global output_frame, totalDown, totalUp

    # construct the argument parse and parse the arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-p", "--prototxt", required=False, default="./mobilenet_ssd/MobileNetSSD_deploy.prototxt",
                    help="path to Caffe 'deploy' prototxt file")
    ap.add_argument("-m", "--model", required=False, default="./mobilenet_ssd/MobileNetSSD_deploy.caffemodel",
                    help="path to Caffe pre-trained model")
    ap.add_argument("-i", "--input", type=str,
                    help="path to optional input video file")
    ap.add_argument("-o", "--output", type=str,
                    help="path to optional output video file")
    # confidence default 0.4
    ap.add_argument("-c", "--confidence", type=float, default=0.4,
                    help="minimum probability to filter weak detections")
    ap.add_argument("-s", "--skip-frames", type=int, default=30,
                    help="# of skip frames between detections")
    args = vars(ap.parse_args())

    # initialize the list of class labels MobileNet SSD was trained to detect
    CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat",
               "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
               "dog", "horse", "motorbike", "person", "pottedplant", "sheep",
               "sofa", "train", "tvmonitor"]

    # load our serialized model from disk
    net = cv2.dnn.readNetFromCaffe(args["prototxt"], args["model"])

    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)

    # if a video path was not supplied, grab a reference to the ip camera
    if not args.get("input", False):
        print("[INFO] Starting the live stream..")
        vs = VideoStream(config.url).start()
        time.sleep(2.0)

    # otherwise, grab a reference to the video file
    else:
        print("[INFO] Starting the video..")
        vs = cv2.VideoCapture(args["input"])

    # initialize the video writer (we'll instantiate later if need be)
    writer = None

    # initialize the frame dimensions (we'll set them as soon as we read the first frame from the video)
    W = None
    H = None

    # instantiate our centroid tracker, then initialize a list to store each of our dlib correlation trackers, followed by a dictionary to map each unique object ID to a TrackableObject
    ct = CentroidTracker(maxDisappeared=40, maxDistance=50)
    trackers = []
    trackableObjects = {}

    # initialize the total number of frames processed thus far, along with the total number of objects that have moved either up or down
    totalFrames = 0
    totalDown = 0
    totalUp = 0
    x = []
    empty = []
    empty1 = []

    # start the frames per second throughput estimator
    fps = FPS().start()

    if config.Thread:
        vs = thread.ThreadingClass(config.url)

    # loop over frames from the video stream
    while not stop_event.is_set():
        # grab the next frame and handle if we are reading from either VideoCapture or VideoStream
        frame = vs.read()
        frame = frame[1] if args.get("input", False) else frame

        # if we are viewing a video and we did not grab a frame then we have reached the end of the video
        if args["input"] is not None and frame is None:
            break

        # resize the frame to have a maximum width of 500 pixels (the less data we have, the faster we can process it), then convert the frame from BGR to RGB for dlib
        frame = imutils.resize(frame, width=500)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # if the frame dimensions are empty, set them
        if W is None or H is None:
            (H, W) = frame.shape[:2]

        # if we are supposed to be writing a video to disk, initialize the writer
        if args["output"] is not None and writer is None:
            fourcc = cv2.VideoWriter_fourcc(*"MJPG")
            writer = cv2.VideoWriter(args["output"], fourcc, 30, (W, H), True)

        # initialize the current status along with our list of bounding box rectangles returned by either (1) our object detector or (2) the correlation trackers
        status = "Waiting"
        rects = []

        # check to see if we should run a more computationally expensive object detection method to aid our tracker
        if totalFrames % args["skip_frames"] == 0:
            # set the status and initialize our new set of object trackers
            status = "Detecting"
            trackers = []

            # convert the frame to a blob and pass the blob through the network and obtain the detections
            blob = cv2.dnn.blobFromImage(frame, 0.007843, (W, H), 127.5)
            net.setInput(blob)
            detections = net.forward()

            # loop over the detections
            for i in np.arange(0, detections.shape[2]):
                # extract the confidence (i.e., probability) associated with the prediction
                confidence = detections[0, 0, i, 2]

                # filter out weak detections by requiring a minimum confidence
                if confidence > args["confidence"]:
                    # extract the index of the class label from the detections list
                    idx = int(detections[0, 0, i, 1])

                    # if the class label is not a person, ignore it
                    if CLASSES[idx] != "person":
                        continue

                    # compute the (x, y)-coordinates of the bounding box for the object
                    box = detections[0, 0, i, 3:7] * np.array([W, H, W, H])
                    (startX, startY, endX, endY) = box.astype("int")

                    # construct a dlib rectangle object from the bounding box coordinates and then start the dlib correlation tracker
                    tracker = dlib.correlation_tracker()
                    rect = dlib.rectangle(startX, startY, endX, endY)
                    tracker.start_track(rgb, rect)

                    # add the tracker to our list of trackers so we can utilize it during skip frames
                    trackers.append(tracker)

        # otherwise, we should utilize our object *trackers* rather than object *detectors* to obtain a higher frame processing throughput
        else:
            # loop over the trackers
            for tracker in trackers:
                # set the status of our system to be 'tracking' rather than 'waiting' or 'detecting'
                status = "Tracking"

                # update the tracker and grab the updated position
                tracker.update(rgb)
                pos = tracker.get_position()

                # unpack the position object
                startX = int(pos.left())
                startY = int(pos.top())
                endX = int(pos.right())
                endY = int(pos.bottom())

                # add the bounding box coordinates to the rectangles list
                rects.append((startX, startY, endX, endY))

        # draw a horizontal line in the center of the frame -- once an object crosses this line we will determine whether they were moving 'up' or 'down'
        cv2.line(frame, (0, H // 2), (W, H // 2), (0, 0, 0), 3)
        cv2.putText(frame, "-Prediction border - Entrance-", (10, H - ((i * 20) + 200)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

        # use the centroid tracker to associate the (1) old object centroids with (2) the newly computed object centroids
        objects = ct.update(rects)

        # loop over the tracked objects
        for (objectID, centroid) in objects.items():
            # check to see if a trackable object exists for the current object ID
            to = trackableObjects.get(objectID, None)

            # if there is no existing trackable object, create one
            if to is None:
                to = TrackableObject(objectID, centroid)

            # otherwise, there is a trackable object so we can utilize it to determine direction
            else:
                # the difference between the y-coordinate of the *current* centroid and the mean of *previous* centroids will tell us in which direction the object is moving (negative for 'up' and positive for 'down')
                y = [c[1] for c in to.centroids]
                direction = centroid[1] - np.mean(y)
                to.centroids.append(centroid)

                # check to see if the object has been counted or not
                if not to.counted:
                    # if the direction is negative (indicating the object is moving up) AND the centroid is above the center line, count the object
                    if direction < 0 and centroid[1] < H // 2:
                        totalUp += 1
                        empty.append(totalUp)
                        to.counted = True

                    # if the direction is positive (indicating the object is moving down) AND the centroid is below the center line, count the object
                    elif direction > 0 and centroid[1] > H // 2:
                        totalDown += 1
                        empty1.append(totalDown)
                        # store the end time
                        to.counted = True

            # store the trackable object in our dictionary
            trackableObjects[objectID] = to

            # draw both the ID of the object and the centroid of the object on the output frame
            text = "ID {}".format(objectID)
            cv2.putText(frame, text, (centroid[0] - 10, centroid[1] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            cv2.circle(frame, (centroid[0], centroid[1]), 4, (0, 0, 255), -1)

        # construct a tuple of information we will be displaying on the frame
        info = [
            ("Exited", totalUp),
            ("Entered", totalDown),
            ("Status", status),
        ]

        info2 = [
            ("Total people inside", totalDown - totalUp),
        ]

        # loop over the info tuples and draw them on our frame
        for (i, (k, v)) in enumerate(info):
            text = "{}: {}".format(k, v)
            cv2.putText(frame, text, (10, H - ((i * 20) + 20)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        for (i, (k, v)) in enumerate(info2):
            text = "{}: {}".format(k, v)
            cv2.putText(frame, text, (265, H - ((i * 20) + 60)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

        # check to see if we should write the frame to disk
        if writer is not None:
            writer.write(frame)

        # show the output frame
        cv2.imshow("Frame", frame)
        output_frame = frame.copy()
        key = cv2.waitKey(1) & 0xFF

        # if the `q` key was pressed, break from the loop
        if key == ord("q"):
            break

        # increment the total number of frames processed thus far and then update the FPS counter
        totalFrames += 1
        fps.update()

    # stop the timer and display FPS information
    fps.stop()
    print("[INFO] elapsed time: {:.2f}".format(fps.elapsed()))
    print("[INFO] approx. FPS: {:.2f}".format(fps.fps()))

    # check to see if we need to release the video writer pointer
    if writer is not None:
        writer.release()

    # if we are not using a video file, stop the camera video stream
    if not args.get("input", False):
        vs.stop()

    # otherwise, release the video file pointer
    else:
        vs.release()

    # close any open windows
    cv2.destroyAllWindows()

def generate():
    global output_frame
    while not stop_event.is_set():
        if output_frame is None:
            continue
        (flag, encodedImage) = cv2.imencode(".jpg", output_frame)
        if not flag:
            continue
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route('/count')
def get_count():
    global totalUp, totalDown, totalInside
    return jsonify({
        'entered': totalDown,
        'exited': totalUp,
        'inside': totalDown - totalUp
    })

@app.route('/shutdown', methods=['POST'])
def shutdown():
    stop_event.set()
    shutdown_server = request.environ.get('werkzeug.server.shutdown')
    if shutdown_server is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    shutdown_server()
    return 'Server shutting down...'

def signal_handler(sig, frame):
    stop_event.set()
    request.post('http://127.0.0.1:8000/shutdown')
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    video_thread = threading.Thread(target=run)
    video_thread.start()
    app.run(host="0.0.0.0", port=5000, threaded=True, use_reloader=False)

# import signal
# import sys
# import threading
# from mylib.centroidtracker import CentroidTracker
# from mylib.trackableobject import TrackableObject
# from imutils.video import VideoStream
# from imutils.video import FPS
# from mylib.mailer import Mailer
# from mylib import config, thread
# import time, schedule, csv
# import numpy as np
# import argparse, imutils
# import time, dlib, cv2, datetime
# from itertools import zip_longest
# from flask import Flask, Response, request, jsonify
# from flask_cors import CORS
# import logging

# app = Flask(__name__)
# CORS(app)

# logging.basicConfig(level=logging.DEBUG)

# output_frames = {}
# camera_threads = {}
# stop_events = {}
# counters = {}

# # Global structure to store counts for each camera
# counts = {
#     "entered": {},
#     "exited": {},
#     "inside": {}
# }

# def run_camera(camera_id, url):
#     global output_frames, counts

#     ap = argparse.ArgumentParser()
#     ap.add_argument("-p", "--prototxt", required=False, default="../backend/people-counter/mobilenet_ssd/MobileNetSSD_deploy.prototxt",
#                     help="path to Caffe 'deploy' prototxt file")
#     ap.add_argument("-m", "--model", required=False, default="../backend/people-counter/mobilenet_ssd/MobileNetSSD_deploy.caffemodel",
#                     help="path to Caffe pre-trained model")
#     ap.add_argument("-c", "--confidence", type=float, default=0.4,
#                     help="minimum probability to filter weak detections")
#     ap.add_argument("-s", "--skip-frames", type=int, default=30,
#                     help="# of skip frames between detections")
#     args = vars(ap.parse_args())

#     CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat", "bottle", "bus", "car", "cat", "chair", "cow",
#                "diningtable", "dog", "horse", "motorbike", "person", "pottedplant", "sheep", "sofa", "train", "tvmonitor"]

#     net = cv2.dnn.readNetFromCaffe(args["prototxt"], args["model"])

#     vs = VideoStream(url).start()
#     time.sleep(2.0)

#     writer = None
#     W = None
#     H = None

#     ct = CentroidTracker(maxDisappeared=40, maxDistance=50)
#     trackers = []
#     trackableObjects = {}

#     totalFrames = 0
#     totalDown = 0
#     totalUp = 0

#     fps = FPS().start()

#     if config.Thread:
#         vs = thread.ThreadingClass(url)

#     while not stop_events[camera_id].is_set():
#         frame = vs.read()
#         frame = frame[1] if isinstance(vs, cv2.VideoCapture) else frame

#         if frame is None:
#             break

#         frame = imutils.resize(frame, width=500)
#         rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

#         if W is None or H is None:
#             (H, W) = frame.shape[:2]

#         status = "Waiting"
#         rects = []

#         if totalFrames % args["skip_frames"] == 0:
#             status = "Detecting"
#             trackers = []

#             blob = cv2.dnn.blobFromImage(frame, 0.007843, (W, H), 127.5)
#             net.setInput(blob)
#             detections = net.forward()

#             for i in np.arange(0, detections.shape[2]):
#                 confidence = detections[0, 0, i, 2]

#                 if confidence > args["confidence"]:
#                     idx = int(detections[0, 0, i, 1])

#                     if CLASSES[idx] != "person":
#                         continue

#                     box = detections[0, 0, i, 3:7] * np.array([W, H, W, H])
#                     (startX, startY, endX, endY) = box.astype("int")

#                     tracker = dlib.correlation_tracker()
#                     rect = dlib.rectangle(startX, startY, endX, endY)
#                     tracker.start_track(rgb, rect)

#                     trackers.append(tracker)

#         else:
#             for tracker in trackers:
#                 status = "Tracking"
#                 tracker.update(rgb)
#                 pos = tracker.get_position()

#                 startX = int(pos.left())
#                 startY = int(pos.top())
#                 endX = int(pos.right())
#                 endY = int(pos.bottom())

#                 rects.append((startX, startY, endX, endY))

#         cv2.line(frame, (0, H // 2), (W, H // 2), (0, 0, 0), 3)
#         cv2.putText(frame, "-Prediction border - Entrance-", (10, H - 20),
#                     cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)

#         objects = ct.update(rects)

#         for (objectID, centroid) in objects.items():
#             to = trackableObjects.get(objectID, None)

#             if to is None:
#                 to = TrackableObject(objectID, centroid)
#             else:
#                 y = [c[1] for c in to.centroids]
#                 direction = centroid[1] - np.mean(y)
#                 to.centroids.append(centroid)

#                 if not to.counted:
#                     if direction < 0 and centroid[1] < H // 2:
#                         totalUp += 1
#                         to.counted = True

#                     elif direction > 0 and centroid[1] > H // 2:
#                         totalDown += 1
#                         to.counted = True

#             trackableObjects[objectID] = to

#             text = "ID {}".format(objectID)
#             cv2.putText(frame, text, (centroid[0] - 10, centroid[1] - 10),
#                         cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
#             cv2.circle(frame, (centroid[0], centroid[1]), 4, (0, 0, 255), -1)

#         counts["entered"][camera_id] = totalDown
#         counts["exited"][camera_id] = totalUp
#         counts["inside"][camera_id] = totalDown - totalUp

#         if writer is not None:
#             writer.write(frame)

#         cv2.imshow("Frame", frame)
#         output_frames[camera_id] = frame.copy()
#         key = cv2.waitKey(1) & 0xFF

#         if key == ord("q"):
#             break

#         totalFrames += 1
#         fps.update()

#     fps.stop()
#     print("[INFO] elapsed time: {:.2f}".format(fps.elapsed()))
#     print("[INFO] approx. FPS: {:.2f}".format(fps.fps()))

#     if writer is not None:
#         writer.release()

#     vs.stop()
#     cv2.destroyAllWindows()

# def generate(camera_id):
#     global output_frames
#     while not stop_events[camera_id].is_set():
#         if camera_id not in output_frames or output_frames[camera_id] is None:
#             continue
#         (flag, encodedImage) = cv2.imencode(".jpg", output_frames[camera_id])
#         if not flag:
#             continue
#         yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n')

# @app.route('/video_feed/<camera_id>')
# def video_feed(camera_id):
#     return Response(generate(camera_id), mimetype="multipart/x-mixed-replace; boundary=frame")

# @app.route('/count')
# def get_count():
#     return jsonify(counts)


# def is_valid_camera_link(camera_link):
#     # Try to open the video capture
#     cap = cv2.VideoCapture(camera_link)
#     if not cap.isOpened():
#         return False
#     # Release the capture
#     cap.release()
#     return True


# @app.route('/add_camera', methods=['POST'])
# def add_camera():
#     try:
#         data = request.get_json()
#         camera_id = data.get('camera_id')
#         camera_link = data.get('camera_link')

#         if not camera_id or not camera_link:
#             return jsonify({"error": "Camera ID and link are required"}), 400

#         if not is_valid_camera_link(camera_link):
#             logging.debug(f"Camera {camera_id} link is invalid.")
#             return jsonify({"error": "Invalid camera link"}), 400

#         # Create a stop event for the camera
#         stop_events[camera_id] = threading.Event()

#         # Start the camera processing thread
#         camera_thread = threading.Thread(target=run_camera, args=(camera_id, camera_link))
#         camera_threads[camera_id] = camera_thread
#         camera_thread.start()

#         logging.debug(f"Camera {camera_id} thread started. Current threads: {camera_threads.keys()}")

#         return jsonify({"message": f"Camera {camera_id} added successfully"}), 200

#     except Exception as e:
#         logging.error(f"Error occurred: {e}")
#         return jsonify({"error": "An error occurred while adding the camera"}), 500


# @app.route('/remove_camera', methods=['POST'])
# def remove_camera():
#     try:
#         data = request.get_json()
#         camera_id = data.get('camera_id')

#         if not camera_id:
#             return jsonify({"error": "Camera ID is required"}), 400

#         # Remove the camera_id if it exists in the dictionary
#         if camera_id in output_frames:
#             del output_frames[camera_id]
#             logging.debug(f"Camera {camera_id} removed. Current output_frames: {output_frames}")
#         else:
#             logging.debug(f"Camera {camera_id} not found in output_frames. Attempting to remove it anyway.")

#         return jsonify({"message": f"Camera {camera_id} removed successfully"}), 200

#     except Exception as e:
#         logging.error(f"Error occurred: {e}")
#         return jsonify({"error": "An error occurred while removing the camera"}), 500

# @app.route('/shutdown', methods=['POST'])
# def shutdown():
#     for event in stop_events.values():
#         event.set()
#     shutdown_server = request.environ.get('werkzeug.server.shutdown')
#     if shutdown_server is None:
#         raise RuntimeError('Not running with the Werkzeug Server')
#     shutdown_server()
#     return 'Server shutting down...'

# def signal_handler(sig, frame):
#     print("Shutting down gracefully...")
#     for event in stop_events.values():
#         event.set()
#     for thread in camera_threads.values():
#         thread.join()
#     sys.exit(0)

# if __name__ == "__main__":
#     signal.signal(signal.SIGINT, signal_handler)
#     app.run(host='0.0.0.0', port=5000, threaded=True)

from flask import Flask, Response, jsonify
import cv2
import easyocr
import os
import base64

app = Flask(__name__)

# Load the OCR reader
reader = easyocr.Reader(['en'])

# Create directory if not exists
detected_dir = 'Detected'
if not os.path.exists(detected_dir):
    os.makedirs(detected_dir)

# Initialize camera
cap = cv2.VideoCapture(0)  # Use 0 for your default camera, or specify another index if you have multiple cameras

number_plate_text = ""
latest_image_path = ""
last_contour = None
last_detection_time = 0

def generate_frames():
    global number_plate_text, latest_image_path, last_contour, last_detection_time
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Convert frame to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Perform edge detection
        edges = cv2.Canny(gray, 50, 150)

        # Find contours in the edged image
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        detection_found = False

        # Loop over the contours to find the potential number plate area
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)

            # Filter out contours based on aspect ratio and area
            aspect_ratio = w / float(h)
            if 2.5 <= aspect_ratio <= 4.0:
                if 1000 <= cv2.contourArea(contour) <= 8000:
                    # Draw a rectangle around the number plate
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                    # Crop the region of interest (ROI) containing the number plate
                    plate_img = frame[y:y + h, x:x + w]

                    # Perform OCR on the cropped image
                    result = reader.readtext(plate_img)

                    # Print OCR result
                    if result:
                        number_plate_text = result[0][-2]  # Get the detected number plate text
                        print(number_plate_text)

                        # Clean the filename (remove spaces)
                        filename = ''.join(e for e in number_plate_text if e.isalnum())

                        # Save the image with the number plate text as filename
                        img_path = os.path.join(detected_dir, f'{filename}.jpg')
                        cv2.imwrite(img_path, plate_img)
                        latest_image_path = img_path
                        print(f"Saved image as: {img_path}")

                        # Display the detected number plate text
                        cv2.putText(frame, number_plate_text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

                        last_contour = (x, y, w, h)
                        last_detection_time = cv2.getTickCount()
                        detection_found = True

                        # Break the loop after processing the first valid number plate found
                        break

        # If no new detection found, retain the last detection box
        if not detection_found and last_contour is not None:
            x, y, w, h = last_contour
            if (cv2.getTickCount() - last_detection_time) / cv2.getTickFrequency() < 2.0:  # Keep the box for 2 seconds
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, number_plate_text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            else:
                last_contour = None  # Reset if no detection for more than 2 seconds

        # Encode the frame in JPEG format
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()

        # Yield the frame as part of a multipart response
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(debug=True)

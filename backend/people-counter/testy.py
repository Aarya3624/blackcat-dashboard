import gevent
from gevent import monkey
monkey.patch_all()

from flask import Flask, Response, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, Namespace

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Create a custom namespace for Socket.IO
class VideoNamespace(Namespace):
    def on_connect(self):
        print('Client connected')

    def on_disconnect(self):
        print('Client disconnected')

# Use the custom namespace when creating the Socket.IO instance
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent', namespace='/video')
socketio.on_namespace(VideoNamespace('/video'))

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, use_reloader=False)
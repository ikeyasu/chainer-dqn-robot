import base64
import json
import threading

import argparse
import cv2
import numpy as np

import utils
from game import Game

parser = argparse.ArgumentParser(description='Deep Q-learning Network for robot')
parser.add_argument('--camera', action='store_true',
                    help='using usb camera')
parser.add_argument('--hidden', action='store_true',
                    help='hide window')
args = parser.parse_args()

cv2.namedWindow("camera", 1)


class Capture(object):
    def capture(self):
        pass

    def release(self):
        pass


class OpenCVCapture(Capture):
    def __init__(self):
        self.capture = cv2.VideoCapture(0)

    def capture(self):
        return self.capture.read()[:2]

    def release(self):
        self.capture.release()


class VirtualCapture(Capture):
    def __init__(self, mqtt_client):
        self.mqtt_client = mqtt_client
        self.mqtt_client.message_callback_add("/screenshot", lambda c, u, m: self._on_message(c, u, m))
        self.screenshot_event = threading.Event()
        self.screenshot = None

    def _on_message(self, client, userdata, msg):
        obj = json.loads(msg.payload)
        if obj["command"] == "screenshot":
            img = base64.b64decode(obj["screenshot"])
            npimg = np.fromstring(img, dtype=np.uint8)
            self.screenshot = cv2.imdecode(npimg, 1)
            self.screenshot_event.set()

    def capture(self):
        self.screenshot_event.wait()
        return self.screenshot


capture = None
mqtt_client = utils.connect_mqtt_server()
mqtt_client.loop_start()
if args.camera:
    capture = OpenCVCapture()
else:
    capture = VirtualCapture(mqtt_client)
game = Game(mqtt_client)

while True:
    frame = capture.capture()
    if args.hidden is False:
        if args.camera:
            cv2.imshow("camera", frame[:, ::-1])  # mirror
        else:
            cv2.imshow("camera", frame)
    game.scan_cvimage(frame)

    k = cv2.waitKey(500) & 0xFF
    if k == ord('q'):
        break

capture.release()
cv2.destroyAllWindows()

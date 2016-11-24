import argparse
import cv2

from virtual_agent import VirtualAgent
from game import Game

parser = argparse.ArgumentParser(description='Deep Q-learning Network for robot')
parser.add_argument('--camera', action='store_true',
                    help='using usb camera')
args = parser.parse_args()

cv2.namedWindow("camera", 1)

capture = None
agent = None
if args.camera:
    capture = cv2.VideoCapture(0)
else:
    agent = VirtualAgent(800, 600)
game = Game()

while True:
    frame = None
    if capture is not None:
        frame = capture.read()[:2]
        cv2.imshow("camera", frame[:,::-1]) # mirror
    else:
        frame = agent.background
        cv2.imshow("camera", frame)
    #game.scan_cvimage(frame)
    agent.run_once()

    k = cv2.waitKey(500) & 0xFF
    if k == ord('q'):
        break

if args.camera:
    capture.release()
cv2.destroyAllWindows()
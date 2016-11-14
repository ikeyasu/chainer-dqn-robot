import random

import numpy as np
import threading

import zbar


class Agent(object):
    ACTIONS = np.array([[left, right] for left in range(-1, 2) for right in range(-1, 2)], dtype=np.int32)
    def __init__(self):
        self.send_image_event = threading.Event()
        self.play_event = threading.Event()
        self.image = None
        self.action = None
        # create a reader
        self.scanner = zbar.ImageScanner()
        # configure the reader
        self.scanner.parse_config('enable')

    def get_events(self):
        return self.send_image_event, self.play_event

    def action_size(self):
        return len(self.ACTIONS)

    def send_image(self, image):
        print "agent: send image."
        self.image = image
        self.send_image_event.set()

    def receive_image(self):
        self.send_image_event.wait()
        print "agent: receive image."
        self.send_image_event.clear()
        return self.image

    def send_action(self, action):
        print "agent: send action. action=" + str(action)
        self.action = action
        self.play_event.set()

    def receive_action(self):
        self.play_event.wait()
        print "agent: action=" + str(self.action)
        self.play_event.clear()
        return self.action

    def process(self, image):
        pil = image.convert('L')
        width, height = pil.size
        raw = pil.tobytes()
        image = zbar.Image(width, height, 'Y800', raw)
        self.scanner.scan(image)
        if len(image.symbols) > 0:
            print "agent: reword=100"
            return 100, True
        else:
            print "agent: reword=-100"
            return -100, False

    def randomize_action(self, action, random_probability):
        if random.random() < random_probability:
            return random.randint(0, self.action_size() - 1)
        return action

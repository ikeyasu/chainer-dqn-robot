from __future__ import print_function
from __future__ import print_function

import base64
import json
import random
import PIL
import cStringIO
import numpy as np
import zbar
import six.moves.queue as queue

import utils


class AbstractAgent(object):
    ACTIONS = np.array([[left, right] for left in range(-1, 2) for right in range(-1, 2)], dtype=np.int32)

    def __init__(self):
        pass

    def action_size(self):
        return len(self.ACTIONS)

    def process(self, image):
        return 100, True

    def randomize_action(self, action, random_probability):
        if random.random() < random_probability:
            return random.randint(0, self.action_size() - 1)
        return action


class Agent(AbstractAgent):
    USE_HTTP_SERVER = False

    def __init__(self):
        super(Agent, self).__init__()
        self.image = None
        self.action = None
        self.reward = None
        self.termination = None
        self.reply_queue = queue.Queue()

        self.scanner = zbar.ImageScanner()
        self.scanner.parse_config('enable')

        self.mqtt_client = utils.connect_mqtt_server()
        self.mqtt_client.message_callback_add("/robot", lambda c, u, m: self._on_message(c, u, m))
        self.mqtt_client.loop_start()

    def _on_message(self, client, userdata, msg):
        msg = json.loads(msg.payload)
        q = self.reply_queue.get()
        if msg["command"] == "reply" and msg["source"]["command"] == q["command"]:
            if q.has_key("_callback"):
                q["_callback"](msg)
            self.reply_queue.task_done()
        else:
            self.reply_queue.put(q)
            self.reply_queue.task_done()

    def receive_image(self):
        def _callback(msg):
            image_string = cStringIO.StringIO(base64.b64decode(msg["image"]))
            self.image = PIL.Image.open(image_string)

        obj = {
            "command": "request-image"
        }
        self.mqtt_client.publish("/robot", json.dumps(obj))
        obj["_callback"] = _callback
        self.reply_queue.put(obj)
        self.reply_queue.join()
        print("agent: receive image.")
        return self.image

    def send_action(self, action):
        print("agent: send action. action=" + str(action))
        obj = {
            "command": "action",
            "action": action
        }
        self.mqtt_client.publish("/robot", json.dumps(obj))
        self.reply_queue.put(obj)
        self.reply_queue.join()
        self.action = action

    def process(self, image):

        def _callback(msg):
            self.reward = msg["reward"]
            self.termination = msg["termination"]

        obj = {
            "command": "request-reward"
        }
        self.mqtt_client.publish("/robot", json.dumps(obj))
        obj["_callback"] = _callback
        self.reply_queue.put(obj)
        self.reply_queue.join()
        print("agent: receive reward: reward=" + str(self.reward) + " termination=" + str(self.termination))
        return self.reward, self.termination
        # pil = image.convert('L')
        # width, height = pil.size
        # raw = pil.tobytes()
        # image = zbar.Image(width, height, 'Y800', raw)
        # self.scanner.scan(image)
        # if len(image.symbols) > 0:
        #    print "agent: reword=100"
        #    return 100, True
        # else:
        #    print "agent: reword=-100"
        #    return -100, False

    def randomize_action(self, action, random_probability):
        if random.random() < random_probability:
            return random.randint(0, self.action_size() - 1)
        return action

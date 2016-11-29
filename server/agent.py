import random
import thread
import PIL
import numpy as np
import threading
import zbar
import paho.mqtt.client as mqtt
from flask import Flask
from flask import request


class AbstractAgent(object):
    ACTIONS = np.array([[left, right] for left in range(-1, 2) for right in range(-1, 2)], dtype=np.int32)

    def __init__(self):
        pass

    def process(self, image):
        return 100, True

    def randomize_action(self, action, random_probability):
        if random.random() < random_probability:
            return random.randint(0, self.action_size() - 1)
        return action


class Agent(AbstractAgent):
    USE_HTTP_SERVER = False

    def __init__(self, host='127.0.0.1'):
        self.send_image_event = threading.Event()
        self.play_event = threading.Event()
        self.image = None
        self.action = None
        self.host = host

        self.scanner = zbar.ImageScanner()
        self.scanner.parse_config('enable')

        self.mqtt_client = self.connect_mqtt_server_(host)

    def loop_forever(self):
        thread.start_new_thread(self.run_http_server_, (self.host,))
        self.mqtt_client.loop_forever()

    @staticmethod
    def connect_mqtt_server_(host):
        def on_connect(client, userdata, flags, respons_code):
            client.subscribe("/robot")
            print('status {0}'.format(respons_code))

        def on_message(client, userdata, msg):
            print(msg.topic + ' ' + str(msg.payload))

        mqtt_client = mqtt.Client(protocol=mqtt.MQTTv311)
        mqtt_client.on_connect = on_connect
        mqtt_client.on_message = on_message
        mqtt_client.connect(host, port=1883, keepalive=60)
        return mqtt_client

    def run_http_server_(self, host):
        app = Flask(__name__)

        @app.route("/", methods=['GET', 'POST'])
        def index():
            if request.method == 'POST':
                print("image size: " + str(len(request.data)))
                jpg = 'robot_images/img' + request.args['n'] + '.jpg'
                print 1
                outfile = open(jpg, 'ab')
                print 2
                outfile.write(request.data)
                print 3
                outfile.close()
                print 4
                if request.args['last'] == 'y':
                    print "sending image."
                    image = PIL.Image.open(jpg)
                    print "image opened."
                    self.send_image(image)
                    action = self.receive_action()
                    return str(action)
                return '-'
            else:
                return '-'

        app.run(host)

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

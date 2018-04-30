import json
import zbar

import cv2
import math
from PIL import Image


class Game(object):
    def __init__(self, mqtt_client, self_name="0"):
        self.mqtt_client = mqtt_client
        self.self_name = self_name
        self.symbols = None
        self.mqtt_client.message_callback_add("/robot", lambda c, u, m: self._on_message(c, u, m))

    def _on_message(self, client, userdata, msg):
        obj = json.loads(msg.payload)
        if obj["command"] == "request-reward":
            self._exec_request_reward(obj)

    def _exec_request_reward(self, msg):
        reward, termination = self.get_reward_and_termination()
        obj = {
            "command": "reply",
            "reward": reward,
            "termination": termination,
            "source": msg
        }
        self.mqtt_client.publish("/robot", json.dumps(obj))

    @staticmethod
    def get_center_(location):
        if len(location) != 4:
            raise Exception('location need to have 4 points')
        sorted_x = sorted(location, key=lambda pos: pos[0])
        sorted_y = sorted(location, key=lambda pos: pos[1])
        center_x = sorted_x[0][0] + (sorted_x[3][0] - sorted_x[0][0]) / 2
        center_y = sorted_y[0][1] + (sorted_y[3][1] - sorted_y[0][1]) / 2
        return center_x, center_y

    @staticmethod
    def get_centered_symbol_(symbol):
        symbol["center"] = Game.get_center_(symbol["location"])
        return symbol

    @staticmethod
    def get_distance_(position1, position2):
        x = abs(position1[0] - position2[0])
        y = abs(position1[1] - position2[1])
        return math.sqrt(x ** 2 + y ** 2)

    def calc_distance(self, symbols):
        centered_symbols = [Game.get_centered_symbol_(symbol) for symbol in symbols]
        self_symbol = filter(lambda s: s["data"] == self.self_name, centered_symbols)
        if len(self_symbol) > 0:
            self_symbol = self_symbol[0]
            self_symbol["distance"] = 0
        else:
            return None
        target_symbols = filter(lambda s: s["data"] != self.self_name, centered_symbols)
        for symbol in target_symbols:
            symbol["distance"] = Game.get_distance_(symbol["center"], self_symbol["center"])
        return centered_symbols

    @staticmethod
    def _symbols_to_json(symbols):
        outputs = []
        for symbol in symbols:
            output = {
                'count': symbol.count,
                'data': symbol.data,
                'location': symbol.location,
                'quality': symbol.quality,
                'type': symbol.type
            }
            outputs.append(output)
        return outputs

    def scan_cvimage(self, cvimage):
        output = cvimage.copy()
        gray = cv2.cvtColor(output, cv2.COLOR_BGR2GRAY, dstCn=0)
        pil = Image.fromarray(gray)
        width, height = pil.size
        zbarimage = zbar.Image(width, height, 'Y800', pil.tobytes())
        return self.scan_zbarimage(zbarimage)

    def scan_zbarimage(self, zbar_img):
        scanner = zbar.ImageScanner()
        scanner.parse_config('enable')
        scanner.scan(zbar_img)
        self.symbols = self.calc_distance(Game._symbols_to_json(zbar_img.symbols))
        return self.symbols

    def get_reward_and_termination(self, cvimage = None):
        if cvimage is not None:
            self.scan_cvimage(cvimage)
        if self.symbols is None:
            return 0, False
        sorted_symbols = sorted(self.symbols, key=lambda s: s["distance"])
        reward = 0
        termination = False
        if sorted_symbols[1]["distance"] < 120:
            print sorted_symbols[1]["distance"]
            reward = int(sorted_symbols[1]["data"])
        if sorted_symbols[1]["distance"] < 110:
            print "termination"
            termination = True
        return reward, termination

import zbar

import cv2
import math
from PIL import Image


class Game(object):
    def __init__(self, self_name="0"):
        self.self_name = self_name

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
        symbol.center = Game.get_center_(symbol.location)
        return symbol

    @staticmethod
    def get_distance_(position1, position2):
        x = abs(position1[0] - position2[0])
        y = abs(position1[1] - position2[1])
        return math.sqrt(x ** 2 + y ** 2)

    def calc_distance(self, symbols):
        centered_symbols = [Game.get_centered_symbol_(symbol) for symbol in symbols]
        self_symbol = filter(lambda s: s.data == self.self_name, centered_symbols)
        if len(self_symbol) > 0:
            self_symbol = self_symbol[0]
        else:
            return None
        target_symbols = filter(lambda s: s.data != self.self_name, centered_symbols)
        for symbol in target_symbols:
            symbol.distance = Game.get_distance_(symbol.center, self_symbol.center)
        return centered_symbols

    def scan_cvimage(self, frame):
        output = frame.copy()
        gray = cv2.cvtColor(output, cv2.COLOR_BGR2GRAY, dstCn=0)
        pil = Image.fromarray(gray)
        width, height = pil.size
        zbarimage = zbar.Image(width, height, 'Y800', pil.tobytes())
        return self.scan_zbarimage(zbarimage)

    @staticmethod
    def scan_zbarimage(zbar_img):
        scanner = zbar.ImageScanner()
        scanner.parse_config('enable')
        scanner.scan(zbar_img)

        for symbol in zbar_img:
            print 'decoded', symbol.type, 'symbol', '"%s"' % symbol.data
            print symbol.location
        return zbar_img.symbols

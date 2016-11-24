import numpy as np
import cv2
import math

import subprocess


class VirtualAgent(object):
    VECTOR_SIZE = 100

    def __init__(self, width, height, host='127.0.0.1'):
        self.background = VirtualAgent.create_field_(width, height)
        self.vector = np.array([[width / 2, height / 2], [width / 2, height / 2 - self.VECTOR_SIZE]])
        self.agent_image = cv2.imread("samples/qr_0.png")
        self.host = host
        self.draw_agent_()
        self.draw_vector_()

    def run_once(self):
        cv2.imwrite('result.jpg', self.background)
        cmd = "curl -H 'Content-Type: image/jpeg' --data-binary '@result.jpg' http://" + self.host + ":5000/?n=20&last=y"
        ret = subprocess.check_output(cmd, shell=True)
        print ret

    @staticmethod
    def create_field_(width, height):
        background = np.zeros((height, width, 3), np.uint8)
        background.fill(255)
        qr_n100 = cv2.imread("samples/qr_-100_half.png")
        w, h = qr_n100.shape[:2]
        for y in range(0, height, h):
            for x in range(0, width, w):
                background[y:y + qr_n100.shape[0], x:x + qr_n100.shape[1]] = qr_n100
        cv2.rectangle(background, (w, h), (width - w, height - h), (255, 255, 255), cv2.cv.CV_FILLED)
        return background

    @staticmethod
    def draw_arrow_(img, pt1, pt2, color, thickness=1, lineType=8, shift=0):
        cv2.line(img, tuple(pt1), tuple(pt2), color, thickness, lineType, shift)
        vx = pt2[0] - pt1[0]
        vy = pt2[1] - pt1[1]
        v = math.sqrt(vx ** 2 + vy ** 2)
        ux = vx / v
        uy = vy / v
        w = 5
        h = 10
        ptl = (int(pt2[0] - uy * w - ux * h), int(pt2[1] + ux * w - uy * h))
        ptr = (int(pt2[0] + uy * w - ux * h), int(pt2[1] - ux * w - uy * h))
        cv2.line(img, tuple(pt2), tuple(ptl), color, thickness, lineType, shift)
        cv2.line(img, tuple(pt2), tuple(ptr), color, thickness, lineType, shift)

    def draw_vector_(self):
        VirtualAgent.draw_arrow_(self.background, self.vector[0], self.vector[1], (0, 0, 255), 1)

    def draw_agent_(self, img = None):
        if img is None:
            img = self.agent_image
        w, h = img.shape[:2]
        x = self.vector[0][0] - w / 2
        y = self.vector[0][1] - h / 2
        self.background[y:y + img.shape[0], x:x + img.shape[1]] = img

    def move(self, dx, dy):
        dv = np.array([[dx, dy], [dx, dy]])
        self.vector += dv

    def rotate(self, deg):
        theta = (float(-deg) / 180.) * np.pi
        rot_matrix = np.array([[np.cos(theta), -np.sin(theta)],
                               [np.sin(theta), np.cos(theta)]])
        self.vector[1] = np.dot(rot_matrix, self.vector[1] - self.vector[0]) + self.vector[0]
        #w, h = self.agent_image.shape[:2]
        #dst = np.zeros((w * 1.5, h * 1.5, 3), np.uint8)
        #dst.fill(255)
        #m = cv2.getRotationMatrix2D((w / 2, h / 2), deg, 1)
        #m[0][2] += w / 3
        #m[1][2] += w / 3
        #dst = cv2.warpAffine(self.agent_image, m, dst.shape[:2], dst, cv2.INTER_LINEAR, cv2.BORDER_TRANSPARENT)


import base64
import math
import threading

import pyglet
import numpy as np
import utils
import json
import six.moves.queue as queue


class VirtualField(object):
    #[[-1, -1], # 0
    # [-1, 0],  # 1
    # [-1, 1],  # 2
    # [0, -1],  # 3
    # [0, 0],   # 4
    # [0, 1],   # 5
    # [1, -1],  # 6
    # [1, 0],   # 7
    # [1, 1]]   # 8
    ACTIONS = np.array([[left, right] for left in range(-1, 2) for right in range(-1, 2)], dtype=np.int32)
    VELOCITY = 30
    ROTATION_STEP = 10

    def __init__(self):
        self.window = window = pyglet.window.Window()
        self.images = self._load_images()
        self.batch = pyglet.graphics.Batch()
        self.sprites = self._make_sprites(self.images, self.batch, window.width, window.height)
        self.blocks = {key: value for key, value in self.sprites.iteritems() if key != "agent"}
        self.agent = self.sprites["agent"]
        self.queue = queue.Queue()

        pyglet.clock.schedule_interval(lambda dt: self._dequeue_task(), 0.1)

        @window.event
        def on_draw():
            self.window.clear()
            self.batch.draw()
            self._draw_arrow()

        @window.event
        def on_key_press(symbol, modifiers):
            if symbol == pyglet.window.key.UP:
                self.motor(8)
            if symbol == pyglet.window.key.LEFT:
                self._rotate(-self.ROTATION_STEP)
            if symbol == pyglet.window.key.RIGHT:
                self._rotate(self.ROTATION_STEP)
            if symbol == pyglet.window.key.DOWN:
                self.motor(0)
            self._draw_arrow()

    def _draw_arrow(self):
        rad = float(self.agent.rotation) / 180. * math.pi
        line = np.array(self.agent.position) + np.array([math.sin(rad), math.cos(rad)]) * self.VELOCITY
        line = line.astype(np.int)
        pyglet.graphics.draw(2, pyglet.gl.GL_LINES,
                             ('v2i', self.agent.position + tuple(line)),
                             ('c3B', (255, 0, 0, 255, 0, 0))
                             )

    def _go_forward(self, velocity=None):
        if velocity is None:
            velocity = self.VELOCITY
        rad = float(self.agent.rotation) / 180. * math.pi
        move = np.array([math.sin(rad), math.cos(rad)]) * velocity
        move = move.astype(np.int)
        self.agent.position = tuple(np.array(self.agent.position) + move)

    def _rotate(self, rotation_step=None):
        rotation_step = self.ROTATION_STEP if rotation_step is None else rotation_step
        self.agent.rotation += rotation_step

    def _distancesq(self, target):
        x, y = self.agent.position
        tx, ty = target.position
        return (x - tx) ** 2 + (y - ty) ** 2

    def _check_collision(self):
        for i in self.blocks.values():
            if self._distancesq(i) < (self.agent.width / 2 + i.width / 2) ** 2:
                return True
        return False

    def motor(self, action_id):
        if action_id > len(self.ACTIONS) - 1:
            return
        a = tuple(self.ACTIONS[action_id])
        print(a)
        if a == (0, 0):
            return
        if a[0] == a[1]:  # back/foward
            dir = self.VELOCITY if a[0] > 0 else -self.VELOCITY
            self._go_forward(dir)
            if self._check_collision():
                self._go_forward(-dir)
        if a == (1, 0):
            self._rotate(self.ROTATION_STEP)
        if a == (1, -1):
            self._rotate(self.ROTATION_STEP)
        if a == (0, 1):
            self._rotate(-self.ROTATION_STEP)
        if a == (-1, 1):
            self._rotate(-self.ROTATION_STEP)
        if a == (0, -1):
            self._rotate(self.ROTATION_STEP)
        if a == (-1, 0):
            self._rotate(-self.ROTATION_STEP)
        self.window.dispatch_event('on_draw')

    @staticmethod
    def _make_sprites(images, batch, window_width, window_height):
        h, w = images["-100"].height, images["-100"].width
        s = pyglet.sprite.Sprite(images["agent"], batch=batch)
        s.position = (w * (window_width / w) / 2, h * (window_height / h) / 2)
        sprites = {"agent": s}
        cnt = 0
        for x in range(0, window_width - w, w):
            s = sprites["-100_" + str(cnt)] = pyglet.sprite.Sprite(images["-100"], batch=batch)
            s.position = (x, 0)
            cnt += 1
            s = sprites["-100_" + str(cnt)] = pyglet.sprite.Sprite(images["-100"], batch=batch)
            s.position = (x, (window_height / h) * h - h)
            cnt += 1
        for y in range(h, window_height - h * 2, h):
            s = sprites["-100_" + str(cnt)] = pyglet.sprite.Sprite(images["-100"], batch=batch)
            s.position = ((window_width / w) * w - w, y)
            cnt += 1
            s = sprites["-100_" + str(cnt)] = pyglet.sprite.Sprite(images["-100"], batch=batch)
            s.position = (0, y)
            cnt += 1

        return sprites

    @staticmethod
    def _anchor_center(img):
        img.anchor_x = img.width / 2
        img.anchor_y = img.height / 2

    @staticmethod
    def _load_images():

        images = {
            "agent": pyglet.image.load("samples/qr_0.png"),
            "-100": pyglet.image.load("samples/qr_-100_half.png")
        }
        VirtualField._anchor_center(images["agent"])
        return images

    def _dequeue_task(self):
        if self.queue.empty():
            return
        msg_obj = self.queue.get()
        if msg_obj["command"] == "action":
            self._exec_action(msg_obj)
        self.queue.task_done()

    def _exec_action(self, msg_obj):
        self.motor(int(msg_obj["action"]))

    def loop_infinity(self):
        pyglet.app.run()


class VirtualAgent(object):
    def __init__(self, virtual_field, mqtt_client):
        self.virtual_field = virtual_field
        self.mqtt_client = mqtt_client
        self.mqtt_client.message_callback_add("/robot", lambda c, u, m: self._on_message(c, u, m))
        self.reply_image_event = threading.Event()

        def _screenshot(dt):
            pyglet.image.get_buffer_manager().get_color_buffer().save('screenshot.png')
            with open("screenshot.png", "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read())
                self._publish({"command": "screenshot", "screenshot": encoded_string}, "/screenshot")
                if self.reply_image_event.is_set():
                    self._publish({"command": "reply", "image": encoded_string, "source": {"command": "request-image"}})
                    self.reply_image_event.clear()

        pyglet.clock.schedule_interval(_screenshot , 0.3)

    def _on_message(self, client, userdata, msg):
        obj = json.loads(msg.payload)
        if obj["command"] == "action":
            self._forward_command(obj)
        if obj["command"] == "request-image":
            self._exec_request_image(obj)

    def _forward_command(self, msg_obj):
        self.virtual_field.queue.put(msg_obj)
        self.virtual_field.queue.join()
        reply_obj = {"command": "reply", "source": msg_obj}
        self._publish(reply_obj)

    def _exec_request_image(self, msg_obj):
        self.reply_image_event.set()

    def _publish(self, obj, topic="/robot"):
        self.mqtt_client.publish(topic, json.dumps(obj))

if __name__ == "__main__":
    def main():
        mqtt_client = utils.connect_mqtt_server()
        mqtt_client.loop_start()
        field = VirtualField()
        agent = VirtualAgent(field, mqtt_client)
        field.loop_infinity()


    main()

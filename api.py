__author__ = 'sserrano'

import logging
import json
import time
import threading
from Queue import Queue, Empty

import tornado.ioloop
import tornado.web

from pyMultiwii import MultiWii

#Globals
RUNNING = True

from config import (THROTTLE_MIN, THROTTLE_MAX, INITIAL_ROLL, INITIAL_PITCH, INITIAL_YAW, INITIAL_THROTTLE, SERIAL)

#multi-thread safe queue
QUEUE = Queue()

class RC(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        global RUNNING

        values = {
            'roll': INITIAL_ROLL,
            'pitch': INITIAL_PITCH,
            'yaw': INITIAL_YAW,
            'throttle': INITIAL_THROTTLE
        }

        board = MultiWii(SERIAL, PRINT=False)
        last_command = time.time()
        armed = False

        try:
            while RUNNING:
                command = None
                try:
                    command = QUEUE.get_nowait()
                    QUEUE.task_done() # we don't retry commands
                except Empty:
                    if (time.time() - last_command) > 2:
                        #fail safe - if no commands stop the drone
                        board.disarm()
                        armed = False
                        continue
                    if armed:
                        data = [values['roll'], values['pitch'], values['yaw'], values['throttle']]
                        board.sendCMD(8,MultiWii.SET_RAW_RC,data)
                        time.sleep(0.05)
                        continue

                last_command = time.time()
                if not command or not 'action' in command:
                    continue

                print "got command: %s" % command
                if command['action'] == 'arm':
                    board.arm()
                    armed = True
                elif command['action'] == 'disarm':
                    board.disarm()
                    armed = False
                elif command['action'] == 'update':
                    try:
                        values.update(command['data'])
                    except:
                        logging.exception('error update values')
                else:
                    logging.debug('invalid command %s' % command)
        except:
            logging.exception("Error")
        board.disarm()

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("ok")

    def post(self):
        QUEUE.put(json.loads(self.request.body))
        self.write("ok")

def make_app():
    return tornado.web.Application([
        (r"/", MainHandler),
    ])

if __name__ == "__main__":
    rc = RC()
    rc.start()

    app = make_app()
    app.listen(8888)
    try:
        tornado.ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        RUNNING = False


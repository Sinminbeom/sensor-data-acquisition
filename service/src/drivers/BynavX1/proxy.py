import logging
import random
import threading
import time

import websocket


class ProtocolError(Exception):
    pass


class BynavX1Proxy(threading.Thread):
    def __init__(self, url: str):
        super().__init__()
        self.keepAlive = False
        self.url = url
        self.ws = None
        self.event = threading.Event()
        self.lock = threading.Lock()
        self.result = {}

    def start(self) -> 'BynavX1Proxy':
        super().start()
        return self

    def stop(self):
        self.event.set()
        self.join()

    def run(self):
        # create websocket
        self.ws = websocket.WebSocket()

        # connect
        while not self.event.is_set():
            try:
                self.ws.connect(self.url)
                break
            except Exception as e:
                logging.warning(f'Failed to connect to {self.url} - {e}')
                time.sleep(1)
                continue

        # send init code
        self.on_open()

        # wait for response
        while not self.event.is_set():
            result = self.on_message(self.ws.recv())
            if result:
                with self.lock:
                    self.result = result

        # close
        self.keepAlive = False
        self.ws.close()

    def on_open(self):
        init_code = "init " + str(round(random.random() * 4294967294 + 1))
        self.ws.send(init_code)
        self.keepAlive = True
        self.web_sock_keep_alive()

    def web_sock_keep_alive(self):
        if self.ws and self.keepAlive:
            self.ws.send('ping')
            threading.Timer(5, self.web_sock_keep_alive).start()

    def on_message(self, message) -> dict:
        begin = message.find("#")
        if begin == -1:
            begin = message.find("$")
        if begin != -1:
            valid_data = message[begin:]
            if valid_data[0] == "#" or valid_data[0] == "$":
                return self.gps_update(valid_data)
        return {}

    def gps_update(self, valid_data) -> dict:
        try:
            parsed = self.gps_parse(valid_data)
            if parsed:
                return parsed
        except ProtocolError:
            return {}

    def gps_parse(self, line) -> dict:
        if not isinstance(line, str):
            raise ProtocolError(f'Invalid input type: {type(line)}')

        ptl_type = 0 if line[0] == '$' else 1 if line[0] == '#' else False
        if not ptl_type:
            raise ProtocolError(f'Invalid protocol type: {line}')

        # noinspection PyUnresolvedReferences
        nmea = line.split(',') if ptl_type == 0 else line.split(';')[0].split(',') + line.split(';')[1].split(',')
        if len(nmea) < 2:
            raise ProtocolError(f'Invalid NMEA data: {line}')

        last = nmea.pop()
        if len(nmea) < 2 or '*' not in last:
            raise ProtocolError(f'Invalid NMEA data: {last}')

        last = last.split('*')
        nmea.append(last[0])
        nmea.append(last[1])

        if ptl_type == 0:
            nmea[0] = nmea[0][3:]
        else:
            nmea[0] = nmea[0][1:]

        try:
            # noinspection PyUnresolvedReferences
            class_method = getattr(self, nmea[0])
            return class_method(line, nmea)
        except AttributeError:
            # Ignore
            return {}

    # noinspection PyPep8Naming
    def BESTPOSA(self, line, bestposa):
        if len(bestposa) != 32:
            raise Exception(f'Invalid BESTPOSA length: {line}')
        return self.parse_best(bestposa)

    # noinspection PyPep8Naming
    def BESTGNSSPOSA(self, line, bestgnss):
        if len(bestgnss) < 10:
            raise Exception(f'Invalid BESTGNSSPOSA length: {line}')
        return self.parse_best(bestgnss)

    @staticmethod
    def parse_best(bestposa):
        return {
            'solstat': bestposa[10],
            'postype': bestposa[11],
            'diffage': float(bestposa[21]),
            'latstd': float(bestposa[17]),
            'lonstd': float(bestposa[18]),

            'lat': float(bestposa[12]),
            'lon': float(bestposa[13]),
            'solnsvs': int(bestposa[24])
        }

    def get_health(self):
        while not self.result:
            time.sleep(0.01)

        with self.lock:
            return {
                'solstat': self.result['solstat'],
                'postype': self.result['postype'],
                'diffage': self.result['diffage'],
                'latstd': self.result['latstd'],
                'lonstd': self.result['lonstd'],
            }

    def get_location(self):
        while not self.result:
            time.sleep(0.01)

        with self.lock:
            return {
                'lat': self.result['lat'],
                'lon': self.result['lon'],
                'solnsvs': self.result['solnsvs']
            }


if __name__ == '__main__':
    proxy = BynavX1Proxy('ws://192.168.20.50/webSocket')
    proxy.start()

    counter = 0
    while True:
        if counter > 10:
            break
        print(proxy.get_health())
        print(proxy.get_location())
        counter += 1
        time.sleep(1)

    proxy.stop()

from drivers.utils import FakeDriverBynavX1

if __name__ == '__main__':
    config = {
        "protocol": "tcp",
        "port": 1111,
        "ntrip": {
            "from": {
                "ip": "115.84.164.202",
                "port": 2101,
                "mount_point": "YONS-RTCM32-M5",
                "user": "seoul",
                "password": "seoul",
                "timeout_s": 5,
            },
            "to": {
                "ip": "192.168.20.50",
                "port": 2222,
            }
        }
    }

    fake_driver = FakeDriverBynavX1(config)
    fake_driver.start()

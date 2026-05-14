from drivers.utils.FakeDriverBynavX1 import NtripBridge

if __name__ == '__main__':
    config_from = {
        "ip": "115.84.164.202",
        "port": 2101,
        "mount_point": "YONS-RTCM32-M5",
        "user": "seoul",
        "password": "seoul",
        "timeout_s": 5,
    }

    # config_from = {
    #     "ip": "210.117.198.84",
    #     "port": 2101,
    #     "mount_point": "SUWN-RTCM31",
    #     "user": "daeho.choi@swm.ai",
    #     "password": "gnss",
    #     "timeout_s": 5
    # }

    config_to = {
        "ip": "192.168.20.50",
        "port": 2222,
    }

    bridge = NtripBridge(config_from, config_to)
    bridge.start()
    while True:
        pass

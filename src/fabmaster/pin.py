import shape

COMPONENT_PIN_WHITE_LIST = [
        'NET_NAME',
        'PIN_NAME',
        'PIN_NUMBER'
    ]

PACKAGE_PIN_WHITE_LIST = [
        'PIN_X',
        'PIN_Y',
        'PIN_ROTATION'
    ]


class ComponentPin(object):
    def __init__(self, data):
        for key in data:
            if key in COMPONENT_PIN_WHITE_LIST:
                self.__dict__[key] = data[key]


class PackagePin(object):


    def __init__(self, data):
        for key in data:
            if key in PACKAGE_PIN_WHITE_LIST:
                self.__dict__[key] = float(data[key])
            else:
                self.__dict__[key] = data[key]

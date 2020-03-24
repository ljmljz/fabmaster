import shape


class VIA(object):
    def __init__(self, data=None):
        if data:
            for key in data:
                self.__dict__[key] = data[key]
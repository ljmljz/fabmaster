import shape


class Copper(object):
    def __init__(self, data=None):
        self.geometry = None
        self.type = ''

        if data:
            self.append(data)

    def append(self, data):
        """
        Append data to the copper
        :param dict data:
        :return:
        """
        self._identify_type(data)
        if self.type == 'LINE':
            self.geometry = shape.Polygon()
            self._append_polygon_data(data)
        else:
            if not self.geometry:
                self.geometry = shape.Polygon()

            self._append_polygon_data(data)

    def add_hole(self):
        """
        Add a Hole object to the copper
        :return:
        """
        self.geometry.add_hole()

    def append_hole_data(self, data):
        """
        Append the data to the last hole
        :param data:
        :return:
        """
        if self.type == 'LINE':
            return

        if data['GRAPHIC_DATA_NAME'] == 'LINE':
            start = [float(data['GRAPHIC_DATA_1']), float(data['GRAPHIC_DATA_2'])]
            end = [float(data['GRAPHIC_DATA_3']), float(data['GRAPHIC_DATA_4'])]

            line = shape.Line(start, end)
            # self.hole.append(line)
            self.geometry.append_hole_data(line)
        elif data['GRAPHIC_DATA_NAME'] == 'ARC':
            start = [float(data['GRAPHIC_DATA_1']), float(data['GRAPHIC_DATA_2'])]
            end = [float(data['GRAPHIC_DATA_3']), float(data['GRAPHIC_DATA_4'])]
            center = [float(data['GRAPHIC_DATA_5']), float(data['GRAPHIC_DATA_6'])]
            radius = float(data['GRAPHIC_DATA_7'])
            cw = True if data['GRAPHIC_DATA_9'] == 'CLOCKWISE' else False

            arc = shape.Arc(start, end, center, radius, cw)
            # self.hole.append(arc)
            self.geometry.append_hole_data(arc)

    def _identify_type(self, data):
        """
        Identify the current data is a Line or a Polygon
        :param dict data:
        :return:
        """
        width = 0.0
        if data['GRAPHIC_DATA_NAME'] == 'LINE':
            width = float(data['GRAPHIC_DATA_5'])
        elif data['GRAPHIC_DATA_NAME'] == 'ARC':
            width = float(data['GRAPHIC_DATA_8'])

        if width > 0:
            self.type = 'LINE'
        else:
            self.type = 'POLYGON'

    def _append_polygon_data(self, data):
        """
        Append data to the copper
        :param dict data:
        :return:
        """
        if data['GRAPHIC_DATA_NAME'] == 'LINE':
            start = [float(data['GRAPHIC_DATA_1']), float(data['GRAPHIC_DATA_2'])]
            end = [float(data['GRAPHIC_DATA_3']), float(data['GRAPHIC_DATA_4'])]
            width = float(data['GRAPHIC_DATA_5'])

            line = shape.Line(start, end, width)
            self.geometry.append(line)
        elif data['GRAPHIC_DATA_NAME'] == 'ARC':
            start = [float(data['GRAPHIC_DATA_1']), float(data['GRAPHIC_DATA_2'])]
            end = [float(data['GRAPHIC_DATA_3']), float(data['GRAPHIC_DATA_4'])]
            center = [float(data['GRAPHIC_DATA_5']), float(data['GRAPHIC_DATA_6'])]
            radius = float(data['GRAPHIC_DATA_7'])
            cw = True if data['GRAPHIC_DATA_9'] == 'CLOCKWISE' else False
            width = float(data['GRAPHIC_DATA_8'])

            arc = shape.Arc(start, end, center, radius, cw, width)
            self.geometry.append(arc)
        else:
            pass

    def translate(self, offset):
        """
        Translate the copper by offset
        :param offset: (x, y)
        :return:
        """
        assert isinstance(offset, (list, tuple)), "Parameter should be a list or tuple"

        self.geometry.translate(offset)

    def scale(self, rate):
        """
        Scale the copper
        :param float rate:
        :return:
        """
        self.geometry.scale(rate)

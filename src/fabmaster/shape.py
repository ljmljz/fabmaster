import numpy
import geometry

## LINE
## ARC
## TEXT
## RECTANGLE
## FIG_RECTANGLE
## CIRCLE
## CROSS
## OBLONG_X
## OBLONG_Y
## DIAMOND
## SQUARE


class BaseShape(object):
    _points = numpy.array([])

    def __init__(self):
        pass

    def _update_points(self):
        pass

    def translate(self, offset):
        assert isinstance(offset, (list, tuple)), "Parameter should be a list or tuple"

        self._points = self._points.reshape(-1, 2) + numpy.array(offset)
        self._points = self._points.reshape(-1)

    def rotate(self, deg):
        theta = numpy.radians(deg)
        c, s = numpy.cos(theta), numpy.sin(theta)
        mat = numpy.array([[c, -s], [s, c]])
        self._points = self._points.reshape(-1, 2).dot(mat)
        self._points = self._points.reshape(-1)

    def mirror(self):
        self._points = self._points.reshape(-1, 2) * numpy.array([-1, 1])
        self._points = self._points.reshape(-1)

    def scale(self, rate):
        self._points = self._points * rate

    def reverse(self):
        self._points = self._points.reshape(-1, 2)[::-1]
        self._points = self._points.reshape(-1)

    @property
    def points(self):
        if len(self._points) == 0:
            self._update_points()

        return self._points


class Line(BaseShape):
    def __init__(self, start, end, width=0):
        super(BaseShape, self).__init__()

        assert isinstance(start, (list, tuple)), "Start point should be a list or tuple"
        assert isinstance(end, (list, tuple)), "End point should be a list or tuple"

        self.start = start
        self.end = end
        self.width = width

        self._update_points()

    def _update_points(self):
        points = numpy.array(self.start)
        points = numpy.append(points, self.end)
        self._points = points


class FigRectangle(BaseShape):
    def __init__(self):
        super(FigRectangle, self).__init__()


class Arc(BaseShape):
    def __init__(self, start, end, center, radius=0, cw=False, width=0.0):
        super(Arc, self).__init__()

        assert isinstance(start, (list, tuple)), "Parameter should be a list or tuple"
        assert isinstance(end, (list, tuple)), "Parameter should be a list or tuple"
        assert isinstance(center, (list, tuple)), "Parameter should be a list or tuple"

        self.start = start
        self.end = end
        self.center = center
        self.radius = radius
        self.cw = cw
        self._precision = 6
        self.width = width

    def _update_points(self):
        if self.radius <= 0:
            self._calc_radius()

        start_angle = numpy.arctan2(
            self.start[1] - self.center[1],
            self.start[0] - self.center[0]
        )

        if self.start[0] == self.end[0] and self.start[1] == self.end[1]:
            end_angle = 2 * numpy.pi - start_angle
        else:
            end_angle = numpy.arctan2(
                self.end[1] - self.center[1],
                self.end[0] - self.center[0]
            )
        precision = self._precision if abs(end_angle - start_angle) < numpy.pi else self._precision * 2
        prefix = -1 if self.cw else 1
        step_angle = abs(end_angle - start_angle) / precision
        points = numpy.array(self.start)

        for n in xrange(1, precision):
            x = self.center[0] + self.radius * numpy.cos(start_angle + prefix * n * step_angle)
            y = self.center[1] + self.radius * numpy.sin(start_angle + prefix * n * step_angle)
            points = numpy.append(points, [x, y])

        points = numpy.append(points, self.end)
        self._points = points

    def _calc_radius(self):
        self.radius = numpy.sqrt(
                (self.center[0] - self.start[0]) * (self.center[0] - self.start[0])
                + (self.center[1] - self.start[1]) * (self.center[1] - self.start[1])
            )


class Cross(BaseShape):
    def __init__(self):
        super(Cross, self).__init__()


class Polygon(BaseShape):
    def __init__(self):
        super(Polygon, self).__init__()
        self._holes = []
        self._shapes = []
        self._hole_vertex_indices = []
        self._geometry_inst = None

    def append(self, shape):
        assert isinstance(shape, (Line, Arc)), "Parameter should be an instance of Line or Arc"

        # self._shapes.append(shape)

        if len(self._points) == 0:
            self._points = shape.points
        else:
            points = list(self._points)
            shape_points = list(shape.points)
            if cmp(points[-2:], shape_points[:2]) == 0:
                if cmp(points[:2], shape_points[-2:]) != 0:
                    points.extend(shape_points[2:])
            else:
                points.extend(shape_points)

            self._points = numpy.array(points)

    @property
    def points(self):
        return self._points

    def add_hole(self):
        self._holes.append(Hole())

    def append_hole_data(self, data):
        self._holes[-1].append(data)


    @property
    def holes(self):
        return self._holes

    def extrude(self, z):
        data = [list(self._points)]

        for hole in self._holes:
            if hole.points:
                data.extend([list(hole.points)])

        return geometry.extrude(data, z)

    def triangulate(self):
        data = [list(self._points)]

        for hole in self._holes:
            if hole.points:
                data.extend([list(hole.points)])

        return geometry.triangulate(data)

    def translate(self, offset):
        assert isinstance(offset, (list, tuple)), "Parameter should be a list or tuple"

        self._points = self._points.reshape(-1, 2) + numpy.array(offset)
        self._points = self._points.reshape(-1)

        for hole in self._holes:
            hole.translate(offset)

    def rotate(self, deg):
        theta = numpy.radians(deg)
        c, s = numpy.cos(theta), numpy.sin(theta)
        mat = numpy.array([[c, -s], [s, c]])
        self._points = self._points.reshape(-1, 2).dot(mat)
        self._points = self._points.reshape(-1)

        for hole in self._holes:
            hole.rotate(deg)

    def mirror(self):
        self._points = self._points.reshape(-1, 2) * numpy.array([-1, 1])
        self._points = self._points.reshape(-1)

        for hole in self._holes:
            hole.mirror()

    def scale(self, rate):
        self._points = self._points * rate

        for hole in self._holes:
            hole.scale(rate)


class Hole(BaseShape):
    def __init__(self):
        super(Hole, self).__init__()
        self._shape = []

    def append(self, shape):
        # self._shape.append(shape)

        if len(self._points) == 0:
            self._points = shape.points
        else:
            points = list(self._points)
            shape_points = list(shape.points)
            if cmp(points[-2:], shape_points[:2]) == 0:
                if cmp(points[:2], shape_points[-2:]) != 0:
                    points.extend(shape_points[2:])
            else:
                points.extend(shape_points)

            self._points = numpy.array(points)

    @property
    def points(self):
        return self._points


class OblongX(Polygon):
    def __init__(self, start, end):
        super(OblongX, self).__init__()

        assert isinstance(start, (list, tuple)), "Parameter should be a list or tuple"
        assert isinstance(end, (list, tuple)), "Parameter should be a list or tuple"

        # CounterClockWise
        self.append(Line(start=start, end=[end[0], start[1]]))
        self.append(Arc(start=[end[0], start[1]], end=end, center=[end[0], (end[1] + start[1]) / 2], cw=False))
        self.append(Line(start=end, end=[start[0], end[1]]))
        self.append(Arc(start=[start[0], end[1]], end=start, center=[start[0], (end[1] + start[1]) / 2], cw=False))


class OblongY(Polygon):
    def __init__(self, start, end):
        super(OblongY, self).__init__()

        assert isinstance(start, (list, tuple)), "Parameter should be a list or tuple"
        assert isinstance(end, (list, tuple)), "Parameter should be a list or tuple"

        # CounterClockWise
        self.append(Arc(start=start, end=[end[0], start[1]], center=[(start[0] + end[0]) / 2, start[1]], cw=False))
        self.append(Line(start=[end[0], start[1]], end=end))
        self.append(Arc(start=end, end=[start[0], end[1]], center=[(start[0] + end[0]) / 2, end[1]], cw=False))
        self.append(Line(start=[start[0], end[1]], end=start))


class Rectangle(Polygon):
    def __init__(self, start, end):
        super(Rectangle, self).__init__()

        assert isinstance(start, (list, tuple)), "Parameter should be a list or tuple"
        assert isinstance(end, (list, tuple)), "Parameter should be a list or tuple"

        self.start = start
        self.end = end

        self._update_points()

    def _update_points(self):
        # CounterClockwise
        points = list(self.start)
        points.extend([self.end[0], self.start[1]])
        points.extend(list(self.end))
        points.extend([self.start[0], self.end[1]])

        self._points = numpy.array(points)


class Circle(Polygon):
    def __init__(self, start, center, cw=True):
        super(Circle, self).__init__()

        assert isinstance(start, list), "Parameter should be a list"
        assert isinstance(center, list), "Parameter should be a list"

        self.start = start
        self.center = center
        self._precision = 12
        self.cw = cw

        self._calc_radius()
        self._update_points()

    def _update_points(self):
        start_angle = numpy.arctan2(
            self.start[1] - self.center[1],
            self.start[0] - self.center[0]
        )
        prefix = -1 if self.cw else 1
        step_angle = 2 * numpy.pi / self._precision
        points = numpy.array(self.start)

        for n in xrange(1, self._precision):
            x = self.center[0] + self.radius * numpy.cos(start_angle + prefix * n * step_angle)
            y = self.center[1] + self.radius * numpy.sin(start_angle + prefix * n * step_angle)
            points = numpy.append(points, [x, y])

        self._points = points

    def _calc_radius(self):
        self.radius = numpy.sqrt(
                (self.center[0] - self.start[0]) * (self.center[0] - self.start[0])
                + (self.center[1] - self.start[1]) * (self.center[1] - self.start[1])
            )

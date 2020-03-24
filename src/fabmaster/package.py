import shape
from pin import PackagePin
from stl import mesh
import numpy as np
import os
import json

from setting import __author__, __version__
from setting import BOARD_HEIGHT, PAD_HEIGHT

try:
    import xml.etree.cElementTree as ET
except:
    import xml.etree.ElementTree as ET


# 5 package_geometry       'GRAPHIC_DATA_NAME', 'GRAPHIC_DATA_NUMBER', 'RECORD_TAG', 'GRAPHIC_DATA_1',
#                          'GRAPHIC_DATA_2', 'GRAPHIC_DATA_3', 'GRAPHIC_DATA_4', 'GRAPHIC_DATA_5',
#                          'GRAPHIC_DATA_6', 'GRAPHIC_DATA_7', 'GRAPHIC_DATA_8', 'GRAPHIC_DATA_9',
#                          'SUBCLASS', 'SYM_NAME', 'REFDES'
class Package(object):
    def __init__(self, data=None):
        self.geometries = []
        self.geometry = None
        self.pin = dict()
        self.SYM_NAME = ""
        self.REFDES = ""
        self.LAYER = ""
        self._center = None
        self.mesh = None
        self.pads = None

        if data:
            if data['SUBCLASS'] == "BODY_CENTER":
                self.update_body_center(data)
                self.REFDES = data['REFDES']
                self.SYM_NAME = data['SYM_NAME']
            else:
                self.append_geometry_data(data)

    def bind_pads(self, pads):
        self.pads = pads

    def add_geometry(self):
        self.geometries.append(shape.Polygon())
        self.geometry = self.geometries[-1]

    def append_geometry_data(self, data):
        if not self.SYM_NAME:
            self.SYM_NAME = data['SYM_NAME']

        if not self.REFDES:
            self.REFDES = data['REFDES']

        if not self.LAYER and data['SUBCLASS'] != "BODY_CENTER":
            self.LAYER = data['SUBCLASS']

        if len(self.geometries) == 0:
            self.add_geometry()

        # SUBCLASS: LAYER
        self._append_geometry_data(data)

    def update_body_center(self, data):
        if not self._center:
            self._center = []

        start = [float(data['GRAPHIC_DATA_1']), float(data['GRAPHIC_DATA_2'])]
        end = [float(data['GRAPHIC_DATA_3']), float(data['GRAPHIC_DATA_4'])]
        self._center.append(shape.Line(start, end))

    def _append_geometry_data(self, data):
        # GRAPHIC_DATA_NAME: TYPE
        if data['GRAPHIC_DATA_NAME'] == 'LINE':
            start = [float(data['GRAPHIC_DATA_1']), float(data['GRAPHIC_DATA_2'])]
            end = [float(data['GRAPHIC_DATA_3']), float(data['GRAPHIC_DATA_4'])]

            line = shape.Line(start, end)
            self.geometry.append(line)
        elif data['GRAPHIC_DATA_NAME'] == 'ARC':
            start = [float(data['GRAPHIC_DATA_1']), float(data['GRAPHIC_DATA_2'])]
            end = [float(data['GRAPHIC_DATA_3']), float(data['GRAPHIC_DATA_4'])]
            center = [float(data['GRAPHIC_DATA_5']), float(data['GRAPHIC_DATA_6'])]
            radius = float(data['GRAPHIC_DATA_7'])
            cw = True if data['GRAPHIC_DATA_9'] == 'CLOCKWISE' else False

            arc = shape.Arc(start, end, center, radius, cw)
            self.geometry.append(arc)
        else:
            pass

    def add_pin(self, data):
        pin = PackagePin(data)
        pin_number = data['PIN_NUMBER']
        self.pin[pin_number] = pin

    def save(self, basepath, height=10, pads=None):
        path = os.path.join(basepath, 'meshes', 'packages')
        if not os.path.exists(path):
            os.makedirs(path)

        filename = os.path.join(path, self.SYM_NAME + '.stl')
        for g in self.geometries:
            if len(g._shapes) == 1 and g._shapes[0].__class__.__name__ == "Line":
                self.geometries.remove(g)

        for g in self.geometries:
            if g is None:
                continue

            geometry = g.extrude(height)
            vertices = geometry["vertices"]
            m = mesh.Mesh(np.zeros(geometry["faces"].shape[0], dtype=mesh.Mesh.dtype))
            for i in range(len(geometry["faces"])):
                for j in range(3):
                    m.vectors[i][j] = vertices[geometry["faces"][i][j]]

            if self.mesh is None:
                self.mesh = m.data
            else:
                self.mesh = np.concatenate([self.mesh, m.data])

        for num in self.pin:
            # sometimes the pin-num maybe ''
            if not num:
                continue

            pin = self.pin[num]
            through_hole = True
            for pad in self.pads[pin.PAD_STACK_NAME]:
                if pad.geometry is None:
                    # through_hole is False that means the pad is a SMT pad
                    through_hole = False
                    continue

            if through_hole:
                height = BOARD_HEIGHT + PAD_HEIGHT * 2
                offset = -(BOARD_HEIGHT + PAD_HEIGHT)
            else:
                height = PAD_HEIGHT * 0.75
                offset = 0

            # Extrude PAD unsuccessfully
            pad_mesh = self.pads[pin.PAD_STACK_NAME][0].extrude(height, offset)
            if not pad_mesh:
                continue

            pad_mesh.rotate([0, 0, 1], np.radians(pin.PIN_ROTATION))
            pad_mesh.translate((pin.PIN_X, pin.PIN_Y, 0))
            if self.mesh is None:
                self.mesh = pad_mesh.data
            else:
                self.mesh = np.concatenate([self.mesh, pad_mesh.data])

        combined = mesh.Mesh(self.mesh)
        combined.save(filename)

    def sdf(self, basepath):
        path = os.path.join(basepath, 'models', self.SYM_NAME)
        if not os.path.exists(path):
            os.makedirs(path)

        package_uri = "file://" + os.path.abspath(os.path.join(basepath, 'meshes', 'packages', self.SYM_NAME + '.stl'))
        pad_uri = "file://" + os.path.abspath(os.path.join(basepath, 'meshes', 'pads')) + '/'
        filename = os.path.join(path, 'model.sdf')

        root_node = ET.Element('sdf')
        model_node = ET.SubElement(root_node, 'model')
        model_node.set('name', self.SYM_NAME)

        pose_node = ET.SubElement(model_node, 'pose')
        pose_node.text = "{} {} {} {} {} {}".format(0, 0, 0, 0, 0, 0)
        static_node = ET.SubElement(model_node, 'static')
        static_node.text = 'true'

        link_node = ET.SubElement(model_node, 'link')
        link_node.set('name', self.SYM_NAME + '_link')

        collision_node = ET.SubElement(link_node, 'collision')
        collision_node.set('name', self.SYM_NAME + '_collision')
        geometry_node = ET.SubElement(collision_node, 'geometry')
        mesh_node = ET.SubElement(geometry_node, 'mesh')
        uri_node = ET.SubElement(mesh_node, 'uri')
        uri_node.text = package_uri

        visual_node = ET.SubElement(link_node, 'visual')
        visual_node.set('name', self.SYM_NAME + '_visual')
        geometry_node = ET.SubElement(visual_node, 'geometry')
        mesh_node = ET.SubElement(geometry_node, 'mesh')
        uri_node = ET.SubElement(mesh_node, 'uri')
        uri_node.text = package_uri

        for n in self.pin:
            link_node = ET.SubElement(model_node, 'link')
            link_node.set('name', 'pin_' + n + '_link')
            pose_node = ET.SubElement(link_node, 'pose')
            pose_node.text = "{} {} {} {} {} {}".format(self.pin[n].PIN_X, self.pin[n].PIN_Y, 0, 0, 0, 0)

            collision_node = ET.SubElement(link_node, 'collision')
            collision_node.set('name', 'pin_' + n + '_collision')
            geometry_node = ET.SubElement(collision_node, 'geometry')
            mesh_node = ET.SubElement(geometry_node, 'mesh')
            uri_node = ET.SubElement(mesh_node, 'uri')
            uri_node.text = pad_uri + self.pin[n].PAD_STACK_NAME + '.stl'

            visual_node = ET.SubElement(link_node, 'visual')
            visual_node.set('name', 'pin_' + n + '_visual')
            geometry_node = ET.SubElement(visual_node, 'geometry')
            mesh_node = ET.SubElement(geometry_node, 'mesh')
            uri_node = ET.SubElement(mesh_node, 'uri')
            uri_node.text = pad_uri + self.pin[n].PAD_STACK_NAME + '.stl'

        tree = ET.ElementTree(root_node)
        tree.write(filename, encoding='utf-8', xml_declaration=True)

        self._model_config(path)

    def _model_config(self, path):
        root_node = ET.Element('model')

        name_node = ET.SubElement(root_node, 'name')
        name_node.text = self.SYM_NAME

        version_node = ET.SubElement(root_node, 'version')
        version_node.text = __version__

        sdf_node = ET.SubElement(root_node, 'sdf')
        sdf_node.set('version', '1.6')
        sdf_node.text = 'model.sdf'

        author_node = ET.SubElement(root_node, 'author')
        name_node = ET.SubElement(author_node, 'name')
        name_node.text = __author__

        desc_node = ET.SubElement(root_node, 'description')
        desc_node.text = 'A package model'

        tree= ET.ElementTree(root_node)
        tree.write(os.path.join(path, 'model.config'), encoding='utf-8', xml_declaration=True)

    def translate(self, offset):
        assert isinstance(offset, (list, tuple)), "Parameter should be a list or tuple"

        for geometry in self.geometries:
            geometry.translate(offset)

        for n in self.pin:
            self.pin[n].PIN_X += offset[0]
            self.pin[n].PIN_Y += offset[1]

    def scale(self, rate):
        for geometry in self.geometries:
            geometry.scale(rate)

        for n in self.pin:
            self.pin[n].PIN_X *= rate
            self.pin[n].PIN_Y *= rate

    def mirror(self):
        for geometry in self.geometries:
            geometry.mirror()

        for n in self.pin:
            self.pin[n].PIN_X *= (-1)

    def rotate(self, deg):
        for geometry in self.geometries:
            geometry.rotate(deg)

        theta = np.radians(deg)
        c, s = np.cos(theta), np.sin(theta)
        mat = np.array([[c, -s], [s, c]])

        for n in self.pin:
            point = np.array([self.pin[n].PIN_X, self.pin[n].PIN_Y])
            point = point.dot(mat)

            self.pin[n].PIN_X = point[0]
            self.pin[n].PIN_Y = point[1]

    def ccw(self):
        for geometry in self.geometries:
            points = geometry.points.reshape(-1, 2)
            if len(points) < 3:
                continue

            points = points[:3]
            noraml = np.cross(points[1] - points[0], points[2] - points[0])

            if noraml < 0:
                geometry.reverse()

    def reverse(self):
        for geometry in self.geometries:
            geometry.reverse()

    def center(self):
        if self._center:
            start = self._center[0].start
            end = self._center[0].end

            return (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
        else:
            x_points = []
            y_points = []
            for geometry in self.geometries:
                x_points.extend(geometry.points[::2])
                y_points.extend(geometry.points[1::2])

            min_x = min(x_points)
            min_y = min(y_points)
            max_x = max(x_points)
            max_y = max(y_points)

            return (max_x + min_x) / 2, (max_y + min_y) / 2

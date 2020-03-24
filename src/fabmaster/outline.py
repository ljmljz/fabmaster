import shape
from stl import mesh
from PIL import Image, ImageChops, ImageDraw
import numpy as np
import datetime
import os
import shutil
import pyassimp
from setting import __author__, __version__, __title__
from setting import UV_MAP_SIZE, UV_MAP_OFFSET, UV_MAP_BG_COLOR, UV_MAP_SPACE
from setting import BOARD_HEIGHT, SCALE_RATE


class OutLine(object):
    width = 0
    height = 0

    def __init__(self, data=None):
        self._normalized = False
        self._offset = None
        self.geometry = shape.Polygon()
        if data:
            self.append(data)

    # 8 copper_etch            'CLASS', 'SUBCLASS', 'GRAPHIC_DATA_NAME', 'GRAPHIC_DATA_NUMBER', 'RECORD_TAG',
    #                          'GRAPHIC_DATA_1', 'GRAPHIC_DATA_2', 'GRAPHIC_DATA_3', 'GRAPHIC_DATA_4',
    #                          'GRAPHIC_DATA_5', 'GRAPHIC_DATA_6', 'GRAPHIC_DATA_7', 'GRAPHIC_DATA_8',
    #                          'GRAPHIC_DATA_9', 'NET_NAME'
    def append(self, data):
        """
        Append a raw data to the outline
        :param dict data: the dict includes the outline
        :return:
        """
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

    def _save_to_obj(self, filename, height=10):
        """
        Export the obj file
        :param str filename: the output filename
        :param float height: the height of the board
        :return:
        """
        triangles = self.geometry.triangulate()
        geometry = self.geometry.extrude(height)
        texcoords = np.zeros((3 * len(geometry["faces"]), 2), dtype=np.float32)

        if not self._normalized:
            self.normalize()

        vertices = geometry["vertices"] - np.array([0, 0, height / 2])

        dpi = UV_MAP_OFFSET / self.height if self.width > self.height else UV_MAP_OFFSET / self.width

        # calculate the texcoords
        for k in range(2):
            o = k * len(triangles)
            for i in range(len(triangles)):
                for j in range(3):
                    point = vertices[geometry["faces"][i + o][j]]
                    y = point[0] * dpi / UV_MAP_SIZE
                    x = (point[1] * dpi + k * (UV_MAP_OFFSET + 50)) / UV_MAP_SIZE

                    texcoords[3 * (i + o) + j] = np.array([x, y])

        # calculate the normals
        vectors = np.zeros((len(geometry["faces"]), 3, 3), dtype=np.float32)
        for i, face in enumerate(geometry["faces"]):
            vectors[i] = np.array([vertices[face[0]], vertices[face[1]], vertices[face[2]]])

        # update the normals
        v0 = vectors[:, 0, :3]
        v1 = vectors[:, 1, :3]
        v2 = vectors[:, 2, :3]
        normals = np.cross(v1 - v0, v2 - v0)

        for i in range(len(normals)):
            norm = np.linalg.norm(normals[i])
            if norm != 0:
                normals[i] /= np.linalg.norm(normals[i])

        # write to file
        with open(filename, "wb") as fh:
            fh.write("# {} {}\n".format(__title__, __version__))
            fh.write("# {}\n".format(datetime.datetime.now()))
            fh.write("# {}\n".format(__author__))
            fh.write("\n")
            fh.write("mtllib {}.mtl\n".format(os.path.splitext(os.path.basename(filename))[0]))
            fh.write("\n")
            for v in vertices:
                fh.write("v {} {} {}\n".format(v[0], v[1], v[2]))
            for vn in normals:
                fh.write("vn {} {} {}\n".format(vn[0], vn[1], vn[2]))
            for vt in texcoords:
                fh.write("vt {} {}\n".format(vt[0], vt[1]))
            for i, face in enumerate(geometry["faces"]):
                fh.write("f {}/{}/{} {}/{}/{} {}/{}/{}\n".format(
                    face[0] + 1, 3 * i + 1, i + 1,
                    face[1] + 1, 3 * i + 2, i + 1,
                    face[2] + 1, 3 * i + 3, i + 1,
                ))

        self._save_to_mtl(os.path.splitext(filename)[0] + '.mtl')

    def _save_to_mtl(self, filename):
        """
        Export the material file
        :param str filename: the output filename
        :return:
        """
        basename = os.path.basename(filename)
        name = os.path.splitext(basename)[0]

        with open(filename, 'wb') as fh:
            fh.write("# Fabmaster Exporter\n")
            fh.write("# File Created: {}\n".format(datetime.datetime.now()))
            fh.write("# Author: {}\n".format(__author__))
            fh.write("\n")
            fh.write("newmtl {}\n".format(name))
            fh.write("Ns {}\n".format(10))
            fh.write("Ni {}\n".format(1.0000))
            fh.write("d {}\n".format(1.0000))
            fh.write("Tr {}\n".format(0.0000))
            fh.write("Tf {} {} {}\n".format(1.0000, 1.0000, 1.0000))
            fh.write("illum {}\n".format(2))
            fh.write("Ka {} {} {}\n".format(0.5882, 0.5882, 0.5882))
            fh.write("Kd {} {} {}\n".format(0.5882, 0.5882, 0.5882))
            fh.write("Ks {} {} {}\n".format(0.0000, 0.0000, 0.0000))
            fh.write("Ke {} {} {}\n".format(0.0000, 0.0000, 0.0000))
            fh.write("map_Ka {}.jpg\n".format(name))
            fh.write("map_Kd {}.jpg\n".format(name))

    def save(self, basepath):
        """
        Save the outline to a obj file
        :param str basepath: the base path of output
        :return:
        """
        path = os.path.join(basepath, 'meshes')
        if not os.path.exists(path):
            os.makedirs(path)

        _obj_filename = os.path.join(path, '_outline_.obj')
        self._save_to_obj(_obj_filename, BOARD_HEIGHT)

        # standardize the obj file by pyassimp
        scene = pyassimp.load(_obj_filename)
        pyassimp.export(scene, os.path.join(path, 'outline.obj'), file_type='obj')
        pyassimp.release(scene)

        # compatible with Assimp 3 and 4
        if os.path.isfile(os.path.join(path, 'outline.mtl')):
            shutil.copyfile(os.path.join(path, 'outline.mtl'), os.path.join(path, 'outline.obj.mtl'))

    def scale(self, rate):
        """
        Scale the outline
        :param float rate:
        :return:
        """
        self.geometry.scale(rate)
        self.normalize()

    def normalize(self):
        """
        Calculate the size and offset
        :return:
        """
        min_x = min(self.geometry.points[::2])
        min_y = min(self.geometry.points[1::2])
        max_x = max(self.geometry.points[::2])
        max_y = max(self.geometry.points[1::2])

        self.width = max_x - min_x
        self.height = max_y - min_y
        self._offset = (min_x, min_y)

        self.geometry.translate([-min_x, -min_y])

        self._normalized = True

    def size(self):
        """
        Get the size of the board
        :return tuple size: (width, height)
        """
        if not self._normalized:
            self.normalize()

        return self.width, self.height

    def offset(self):
        """
        Get the offset of origin
        :return tuple offset: (offset_x, offset_y)
        """
        if not self._normalized:
            self.normalize()

        return self._offset

    def uv_map(self, copper_obj, basepath, mode='JPEG'):
        """
        Calculate the UV map of the board
        :param dict copper_obj: the dict includes the Copper objects on top and bottom side
        :param str basepath: output path of the picture
        :param str mode: the format of the picture, the default is JPEG
        :return:
        """
        tx, ty = self.offset()
        tx /= SCALE_RATE
        ty /= SCALE_RATE
        dpi = UV_MAP_OFFSET / self.height if self.width > self.height else UV_MAP_OFFSET / self.width
        img_width = int(dpi * self.width)
        img_height = int(dpi * self.height)

        uv_im = Image.new("RGB", (UV_MAP_SIZE, UV_MAP_SIZE))
        l = 0
        for layer in copper_obj:
            bg_im = Image.new("L", (img_width, img_height))
            # d = ImageDraw.Draw(bg_im)
            #
            # data = np.array(self.outline.geometry.points)
            # data = data.reshape(-1, 2)
            # data = data * DPI
            #
            # d.polygon(list(data.reshape(-1)), fill=UV_MAP_BG_COLOR)
            # del d

            for name in copper_obj[layer]:
                copper = copper_obj[layer][name]

                for polygon in copper['POLYGON']:
                    if polygon.geometry.points is None:
                        continue

                    im = Image.new("L", (img_width, img_height))
                    d = ImageDraw.Draw(im)

                    data = polygon.geometry.points
                    data = data.reshape(-1, 2) - np.array([tx, ty])
                    data = data * (dpi * SCALE_RATE)

                    if len(data):
                        d.polygon(list(data.reshape(-1)), fill="#fff")

                    for hole in polygon.geometry.holes:
                        if hole.points is None:
                            continue

                        data = hole.points
                        data = data.reshape(-1, 2) - np.array([tx, ty])
                        data = data * (dpi * SCALE_RATE)

                        if len(data):
                            d.polygon(list(data.reshape(-1)), fill=UV_MAP_BG_COLOR)

                    bg_im = ImageChops.add(bg_im, im)
                    del d
                    del im
            if self.width > self.height:
                bg_im = bg_im.rotate(90, expand=True)
                uv_im.paste(bg_im, (int(l * img_height) + l * UV_MAP_SPACE, int(UV_MAP_SIZE - img_width)))
            else:
                uv_im.paste(bg_im, (int(l * img_width) + l * UV_MAP_SPACE, int(UV_MAP_SIZE - img_height)))

            l += 1

        im = Image.new('RGB', (UV_MAP_SIZE, UV_MAP_SIZE), color=(40, 80, 255))
        uv_im = ImageChops.subtract(uv_im, im)
        uv_im.save(os.path.join(basepath, 'meshes', '_outline_.jpg'), mode, optimize=True)
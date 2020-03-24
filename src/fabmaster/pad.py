import shape
from stl import mesh
import numpy as np
import os


class Pad(object):
    geometry = None
    mesh = None
    _whitelist = [
        'PAD_NAME',
        'LAYER',
        'PADSHAPE1',
        'PADWIDTH',
        'PADHGHT',
        'PADXOFF',
        'PADYOFF',
    ]

    def __init__(self, data):
        if data:
            for key in data:
                if key in self._whitelist:
                    self.__dict__[key] = data[key]

            self._set_geometry(data)

    def _set_geometry(self, data):
        offset = [float(data['PADXOFF']), float(data['PADYOFF'])]
        width = float(data['PADWIDTH'])
        height = float(data['PADHGHT'])

        if data["PADSHAPE1"] == "CIRCLE":
            self.geometry = shape.Circle(
                [
                    offset[0] - width / 2,
                    offset[1]
                ],
                offset,
                False
            )
        elif data["PADSHAPE1"] == "RECTANGLE" or data["PADSHAPE1"] == "SQUARE":
            self.geometry = shape.Rectangle(
                [
                    offset[0] - width / 2,
                    offset[1] - height / 2
                ],
                [
                    offset[0] + width / 2,
                    offset[1] + height / 2
                ]
            )
        elif data["PADSHAPE1"] == "OBLONG_X":
            self.geometry = shape.OblongX(
                [
                    offset[0] - width / 2,
                    offset[1] - height / 2
                ],
                [
                    offset[0] + width / 2,
                    offset[1] + height / 2
                ]
            )
        elif data["PADSHAPE1"] == "OBLONG_Y":
            self.geometry = shape.OblongY(
                [
                    offset[0] - width / 2,
                    offset[1] - height / 2
                ],
                [
                    offset[0] + width / 2,
                    offset[1] + height / 2
                ]
            )
        else:
            pass

    def scale(self, rate):
        self.geometry.scale(rate)

    def translate(self, offset):
        assert isinstance(offset, (list, tuple)), "Parameter should be a list or tuple"

        self.geometry.translate(offset)

    def extrude(self, height, offset=0):
        if self.geometry is None:
            return None

        geometry = self.geometry.extrude(height)
        vertices = geometry["vertices"] + np.array([0, 0, offset])
        m = mesh.Mesh(np.zeros(geometry["faces"].shape[0], dtype=mesh.Mesh.dtype))
        for i in range(len(geometry["faces"])):
            for j in range(3):
                m.vectors[i][j] = vertices[geometry["faces"][i][j]]

        del geometry

        self.mesh = m

        return m

from pin import ComponentPin
from setting import SCALE_RATE, BOARD_HEIGHT, DEFAULT_COMPONENT_HEIGHT

import os
import svgwrite


class Component(object):
    center = None
    REFDES = ""
    package = None

    def __init__(self, data=None):
        self.pin = dict()
        self._height = 0

        if data:
            for key in data:
                self.__dict__[key] = data[key]

            self.__dict__['SYM_MIRROR'] = True if data['SYM_MIRROR'] == 'YES' else False
            self.__dict__['SYM_ROTATE'] = float(data['SYM_ROTATE'])

        self.height_func = {
            'DEFAULT': self._default_height,
            'RESISTOR': self._resistor_height,
            'CAPACITOR': self._capacitor_height,
            'DIODE': self._diode_height,
            'DISCRETE': self._discrete_height,
            'INDUCTOR': self._inductor_height,
            'ZENER': self._zener_height,
            'FUSE': self._fuse_height,
            'IC': self._ic_height,
            'IO': self._io_height
        }

    def add_pin(self, data):
        """
        Add a component pin to this component
        :param dict data: raw data
        :return:
        """
        pin = ComponentPin(data)

        if data['REFDES'] == self.REFDES:
            pin_number = data["PIN_NUMBER"]
            self.pin[pin_number] = pin

    def bind_pads(self, pads):
        if self.package:
            self.package.bind_pads(pads)

    def export_package(self, path, sim=False):
        """
        Export the package of this component.
        :param str path: the target path to export
        :param bool simulate: the flag of output the model files
        :return:
        """
        cx, cy = self.package.center()

        self.package.scale(SCALE_RATE)
        self.package.translate([-cx * SCALE_RATE, -cy * SCALE_RATE])

        if self.SYM_ROTATE > 0:
            self.package.rotate(self.SYM_ROTATE)

        if self.SYM_MIRROR:
            self.package.mirror()

        self.package.ccw()
        self.package.save(path, self.height)

        if sim:
            self.package.sdf(path)

    def export_svg_model(self, path):
        pads = {}
        svg_model_dir = os.path.join(path, 'svg')

        if not os.path.exists(svg_model_dir):
            os.makedirs(svg_model_dir)

        svg_file = os.path.join(path, 'svg', self.REFDES + '.svg')
        dwg = svgwrite.Drawing(svg_file, debug=False)
        group = dwg.g(id=self.REFDES, footprint=self.SYM_NAME)
        pins = dwg.g(id="component-pins")

        # pin info
        for num in self.package.pin:
            if num not in self.pin:
                continue

            pin = self.package.pin[num]
            pad_name = pin.PAD_STACK_NAME

            if pad_name not in pads:
                pads[pad_name] = self.package.pads[pad_name]

            insert_center = (pin.PIN_X * 3543.307, pin.PIN_Y * 3543.307)
            svg_use = dwg.use(
                href='#' + pad_name,
                insert=insert_center,
                pin_name=pin.PIN_NAME,
                pin_num=num,
                pin_net=self.pin[num].NET_NAME
            )
            svg_use.rotate(pin.PIN_ROTATION, center=insert_center)
            pins.add(svg_use)

        # body info
        body = dwg.g(id="component-body")
        _min_x_arr = []
        _min_y_arr = []
        _max_x_arr = []
        _max_y_arr = []
        for geometry in self.package.geometries:
            if len(geometry.points) > 0:
                _min_x_arr.append(min(geometry.points[::2]))
                _min_y_arr.append(min(geometry.points[1::2]))
                _max_x_arr.append(max(geometry.points[::2]))
                _max_y_arr.append(max(geometry.points[1::2]))

                points = (geometry.points.reshape(-1, 2) * 3543.307).tolist()
                svg_shape = dwg.polygon(points, fill="#000")
                body.add(svg_shape)

        if len(_min_x_arr):
            min_x = min(_min_x_arr) * 3543.307
            max_x = max(_max_x_arr) * 3543.307
            min_y = min(_min_y_arr) * 3543.307
            max_y = max(_max_y_arr) * 3543.307

            body.translate((max_x - min_x) / 2, (max_y - min_y) / 2)
            pins.translate((max_x - min_x) / 2, (max_y - min_y) / 2)
            dwg.viewbox(0, 0, (max_x - min_x), (max_y - min_y))

        for pad_name in pads:
            sym = dwg.symbol(id=pad_name)
            pad = pads[pad_name][0]

            if pad.geometry:
                points = (pad.geometry.points.reshape(-1, 2) * 3543.307).tolist()
                sym.add(dwg.polygon(points, fill="#999999"))

                dwg.defs.add(sym)

        group.add(body)
        group.add(pins)
        dwg.add(group)
        dwg.save()


    @property
    def height(self):
        """
        Get the height of the component
        :return: the height
        :rtype float
        """
        if self._height > 0:
            return self._height

        if self.COMP_HEIGHT:
            return float(self.COMP_HEIGHT) * SCALE_RATE

        if self.type in self.height_func:
            return self.height_func[self.type]()
        else:
            return self._default_height()

    @property
    def type(self):
        """
        Get the type of component
        :return: the type
        :rtype str
        """
        # 'DISCRETE:RESISTOR', 'DISCRETE:CAPACITOR', 'DISCRETE:DIODE', 'DISCRETE',
        # 'DISCRETE:INDUCTOR', 'DISCRETET:HERMISTOR', 'DISCRETE:ZENER', 'DISCRETE:FUSE',
        # 'IC', 'IO',
        if not self.COMP_CLASS:
            return 'DEFAULT'

        if self.COMP_CLASS == 'DISCRETE':
            if self.COMP_DEVICE_LABEL:
                return self.COMP_DEVICE_LABEL
            else:
                return self.COMP_CLASS
        else:
            return self.COMP_CLASS

    def _default_height(self):
        """
        Get the height of the default component height
        :return: the height
        :rtype float
        """
        return DEFAULT_COMPONENT_HEIGHT

    def _resistor_height(self):
        """
        Get the height of Resistor
        :return: the height
        :rtype float
        """
        _height_table = {
            '01005': 0.00013, '0201': 0.00023, '0402': 0.00035, '0603': 0.00045, '0805': 0.0006,
            '1206': 0.0006, '1210': 0.0006, '1812': 0.0006, '2010': 0.0006, '2512': 0.0006
        }

        return self._identify_height(_height_table, default=0.0006)

    def _capacitor_height(self):
        """
        Get the height of Capacitor
        :return: the height
        :rtype float
        """
        _height_table = {
            '01005': 0.00025, '0201': 0.0003, '0402': 0.0004, '0603': 0.0005, '0805': 0.0006,
            '1008': 0.00065, '1206': 0.0007, '1210': 0.0007, '1806': 0.00075, '1812': 0.0008,
            '2010': 0.0008, '2512': 0.0008, '2920': 0.0008, '3216': 0.0016, '3812': 0.00127,
            '3528': 0.0019, '3825': 0.00127, '5012': 0.00127, '5025': 0.00127, '5634': 0.0018,
            '6032': 0.0025, '6738': 0.0028, '7338': 0.0028, '7343': 0.0028,
            'A-Case': 0.0016, 'B-Case': 0.0019, 'C-Case': 0.0025, 'D-Case': 0.0028
        }

        return self._identify_height(_height_table)

    def _diode_height(self):
        """
        Get the height of Diode
        :return: the height
        :rtype float
        """
        return 0.00229

    def _discrete_height(self):
        """
        Get the height of Discrete
        :return: the height
        :rtype float
        """
        return DEFAULT_COMPONENT_HEIGHT

    def _inductor_height(self):
        """
        Get the height of Inductor
        :return: the height
        :rtype float
        """
        _height_table = {
            '01005': 0.00013, '0201': 0.00023, '0402': 0.00035, '0603': 0.00045, '0805': 0.0006,
            '1206': 0.0006, '1210': 0.0006, '1812': 0.0006, '2010': 0.0006, '2512': 0.0006
        }

        return self._identify_height(_height_table, default=0.0006)

    def _hermistor_height(self):
        """
        Get the height of Hermistor
        :return: the height
        :rtype float
        """
        return DEFAULT_COMPONENT_HEIGHT

    def _zener_height(self):
        """
        Get the height of Zener
        :return: the height
        :rtype float
        """
        return 0.00229

    def _fuse_height(self):
        """
        Get the height of Fuse
        :return: the height
        :rtype float
        """
        return 0.00269

    def _ic_height(self):
        """
        Get the height of IC
        :return: the height
        :rtype float
        """
        _height_table = {
            'SOIC': 0.00175, 'SOT': 0.00111, 'TSOP': 0.0012, 'PSOP': 0.00295, 'SSOP': 0.0019,
            'BGA': 0.001, 'DFN': 0.0005, 'QFN': 0.001, 'QFP': 0.0016, 'SON': 0.0008,
            'SO-': 0.00175
        }

        return self._identify_height(_height_table)

    def _io_height(self):
        """
        Get the height of IO
        :return: the height
        :rtype float
        """
        _height_table = {
            'USB': 0.003,
            'COAX': 0.003,
            'HDR': 0.005
        }

        return self._identify_height(_height_table, default=0.015)

    def _identify_height(self, height_table, default=DEFAULT_COMPONENT_HEIGHT):
        """
        Identify the height of the component
        :param dict height_table: the dict includes the height info of this type of component
        :param float default: the default height of this type of component
        :return: the height
        :rtype float
        """
        for key in height_table:
            if self.SYM_NAME.find(key) >= 0:
                return height_table[key]

        return default

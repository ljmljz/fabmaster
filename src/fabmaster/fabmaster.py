from pad import Pad
from componet import Component
from copper import Copper
from package import Package
from via import VIA
from compress import *
from outline import OutLine
from setting import SCALE_RATE
from setting import BOARD_HEIGHT, PAD_HEIGHT
import logging

import json
import numpy as np
from stl import mesh

try:
    import xml.etree.cElementTree as ET
except:
    import xml.etree.ElementTree as ET


class FabMaster(object):
    def __init__(self, filename):
        self._filename = ""
        self.components = dict()
        self.copper = dict()
        self.pads = dict()
        self.packages = dict()
        self.vias = []
        self.outline = OutLine()

        self._package_assembly_id = -1
        self._etch_id = ""
        self._etch_sub_id = ""
        self._meshes = {'TOP': None, 'BOTTOM': None}

        if os.path.isfile(filename):
            self._filename = filename

        self._sections = [
            ['components', self._read_components],
            ['component_pin', self._read_component_pin],
            ['geometry_classes', self._read_geometry_classes],
            ['pad_definition', self._read_pad_definition],
            ['package_geometry', self._read_package_geometry],
            ['package_pins', self._read_package_pins],
            ['vias', self._read_vias],
            ['copper_etch', self._read_copper_etch],
            ['misc_pkg_lines', self._read_misc_pkg_lines],
            ['misc_pkg_lines2', self._read_misc_pkg_lines2],
        ]

    def parse(self):
        """
        Parse the FabMaster file
        :return:
        """
        if not self._filename:
            logging.error("Filename is not existing")

        line_num = 1
        sec_index = 0
        section_name = None
        section_func = None
        section_fields = None

        f = open(self._filename, 'rb')
        for line in f:
            a = line.split('!')
            a.pop()

            if a[0] == 'R' or a[0] == "R\\":
                pass
            elif a[0] == 'J':
                pass
            elif a[0] == 'A':
                if sec_index < len(self._sections):
                    section_name = self._sections[sec_index][0]
                    section_func = self._sections[sec_index][1]
                    section_fields = a[1:]
                    # print "SECTION %2d %s <%s>" % (sec_index+1,section_name,section_fields)
                else:
                    section_name = None
                    section_func = None
                    section_fields = a[1:]
                    print "Unexpected section #%d at line %d" % (sec_index + 1, line_num)
                sec_index += 1
            elif a[0] == 'S':
                if section_func:
                    d = dict(zip(section_fields, a[1:]))
                    section_func(d)
            else:
                logging.error("Unknown record type on line %d" % (line_num))
            line_num += 1

        f.close()

    # 1 components             'REFDES', 'COMP_CLASS', 'COMP_PART_NUMBER', 'COMP_HEIGHT', 'COMP_DEVICE_LABEL',
    #                          'COMP_INSERTION_CODE', 'SYM_TYPE', 'SYM_NAME', 'SYM_MIRROR', 'SYM_ROTATE',
    #                          'SYM_X', 'SYM_Y', 'COMP_VALUE', 'COMP_TOL', 'COMP_VOLTAGE'
    def _read_components(self, data):
        """
        Read a line which includes the component info
        :param dict data:
        :return:
        """
        ref = data['REFDES']
        self.components[ref] = Component(data)

    # 2 component_pin          'NET_NAME', 'REFDES', 'PIN_NUMBER', 'PIN_NAME', 'PIN_GROUND', 'PIN_POWER'
    def _read_component_pin(self, data):
        """
        Read a line which includes the component pin info
        :param dict data: the dict which includes the component pin info
        :return:
        """
        ref = data['REFDES']
        component = self.components[ref]
        component.add_pin(data)

    # 3 geomentry_classes      'CLASS', 'SUBCLASS'
    def _read_geometry_classes(self, data):
        """
        Read the geometry class info
        :param data:
        :return:
        """
        # TODO
        pass

    # 4 pad_definition         'PAD_NAME', 'REC_NUMBER', 'LAYER', 'FIXFLAG', 'VIAFLAG', 'PADSHAPE1', 'PADWIDTH',
    #                          'PADHGHT', 'PADXOFF', 'PADYOFF', 'PADFLASH', 'PADSHAPENAME', 'TRELSHAPE1',
    #                          'TRELWIDTH', 'TRELHGHT', 'TRELXOFF', 'TRELYOFF', 'TRELFLASH', 'TRELSHAPENAME',
    #                          'APADSHAPE1', 'APADWIDTH', 'APADHGHT', 'APADXOFF', 'APADYOFF', 'APADFLASH',
    #                          'APADSHAPENAME'
    def _read_pad_definition(self, data):
        """
        Read the pad info from a line
        :param dict data: the dict which includes the pad info
        :return:
        """
        layers = ['TOP', 'BOTTOM']

        if data['LAYER'] not in layers:
            return

        padname = data['PAD_NAME']

        if self.pads.has_key(padname):
            self.pads[padname].append(Pad(data))
        else:
            self.pads[padname] = [Pad(data)]

    # 5 package_geometry       'GRAPHIC_DATA_NAME', 'GRAPHIC_DATA_NUMBER', 'RECORD_TAG', 'GRAPHIC_DATA_1',
    #                          'GRAPHIC_DATA_2', 'GRAPHIC_DATA_3', 'GRAPHIC_DATA_4', 'GRAPHIC_DATA_5',
    #                          'GRAPHIC_DATA_6', 'GRAPHIC_DATA_7', 'GRAPHIC_DATA_8', 'GRAPHIC_DATA_9',
    #                          'SUBCLASS', 'SYM_NAME', 'REFDES'
    def _read_package_geometry(self, data):
        """
        Read package info from a line
        :param dict data: the dict which includes the package info
        :return:
        """
        if data['GRAPHIC_DATA_NAME'] == 'TEXT':
            return

        if data['SUBCLASS'] not in ['ASSEMBLY_TOP', 'ASSEMBLY_BOTTOM', 'BODY_CENTER']:
            return

        tag_id = data['RECORD_TAG'].split(' ')[0]

        # For some packages which don't have refdes
        if 'REFDES' not in data or not data['REFDES']:
            return

        refdes = data['REFDES']
        component = self.components[refdes]
        # if the component don't have the package info
        if not component.package:
            component.package = Package(data)
            self._package_assembly_id = tag_id
        else:
            # if there is an existing id
            if tag_id == self._package_assembly_id:
                if data['SUBCLASS'] == "BODY_CENTER":
                    component.package.update_body_center(data)
                else:
                    component.package.append_geometry_data(data)
            else:
                if data['SUBCLASS'] == "BODY_CENTER":
                    component.package.update_body_center(data)
                else:
                    component.package.add_geometry()
                    component.package.append_geometry_data(data)
                self._package_assembly_id = tag_id

    # 6  package_pins          'SYM_NAME', 'SYM_MIRROR', 'PIN_NAME', 'PIN_NUMBER', 'PIN_X', 'PIN_Y',
    #                          'PAD_STACK_NAME', 'REFDES', 'PIN_ROTATION', 'TEST_POINT'
    def _read_package_pins(self, data):
        """
        Read the package pin info
        :param dict data: the dict which includes the package info
        :return:
        """
        if data['REFDES'] not in self.components:
            return

        component = self.components[data['REFDES']]
        if component.package:
            component.package.add_pin(data)

    # 7  vias                  'VIA_X', 'VIA_Y', 'PAD_STACK_NAME', 'NET_NAME', 'TEST_POINT', 'VIA_MIRROR',
    #                          'VIA_ROTATION'
    def _read_vias(self, data):
        # self.vias.append(VIA(data))
        # TODO
        pass

    # 8 copper_etch            'CLASS', 'SUBCLASS', 'GRAPHIC_DATA_NAME', 'GRAPHIC_DATA_NUMBER', 'RECORD_TAG',
    #                          'GRAPHIC_DATA_1', 'GRAPHIC_DATA_2', 'GRAPHIC_DATA_3', 'GRAPHIC_DATA_4',
    #                          'GRAPHIC_DATA_5', 'GRAPHIC_DATA_6', 'GRAPHIC_DATA_7', 'GRAPHIC_DATA_8',
    #                          'GRAPHIC_DATA_9', 'NET_NAME'
    def _read_copper_etch(self, data):
        cls = data['CLASS']
        subcls = data['SUBCLASS']

        if '%s!%s' % (cls, subcls) == 'BOARD GEOMETRY!OUTLINE':
            self._parse_outline(data)
        elif '%s!%s' % (cls, subcls) == 'ETCH!TOP' or '%s!%s' % (cls, subcls) == 'ETCH!BOTTOM':
            self._parse_etch(data)
        else:
            pass

    def _parse_outline(self, data):
        """
        Read the outline info
        :param dict data: the dict which includes the outline info
        :return:
        """
        self.outline.append(data)

    def _parse_etch(self, data):
        """
        Read the etch of the board
        :param dict data:
        :return:
        """
        if data['GRAPHIC_DATA_NAME'] == 'TEXT':
            return

        layer = data['SUBCLASS']
        width = 0.0
        if data['GRAPHIC_DATA_NAME'] == 'LINE':
            width = float(data['GRAPHIC_DATA_5'])
        elif data['GRAPHIC_DATA_NAME'] == 'ARC':
            width = float(data['GRAPHIC_DATA_8'])

        if 'NET_NAME' not in data:
            data['NET_NAME'] = '###'

        net_name = data['NET_NAME'] if data['NET_NAME'] else "==="

        splited_record_tag = data['RECORD_TAG'].split()

        sub_id = None
        tag_id = splited_record_tag[0]
        # seq_id = splited_record_tag[1]
        if len(splited_record_tag) == 3:
            sub_id = splited_record_tag[2]

        if layer not in self.copper:
            self.copper[layer] = dict([(net_name, {'POLYGON': [], 'LINE': []})])
        elif net_name not in self.copper[layer]:
            self.copper[layer][net_name] = {'POLYGON': [], 'LINE': []}

        target_object = self.copper[layer][net_name]

        # single line
        if width > 0:
            target_object['LINE'].append(Copper(data))
        # polygon
        else:
            if tag_id == self._etch_id:
                copper = target_object['POLYGON'][-1]
                # sub_id is 0
                if not sub_id or sub_id == "0":
                    copper.append(data)
                else:
                    if sub_id == self._etch_sub_id:
                        copper.append_hole_data(data)
                    else:
                        copper.add_hole()
                        copper.append_hole_data(data)
                        self._etch_sub_id = sub_id
            else:
                target_object['POLYGON'].append(Copper(data))
                self._etch_id = tag_id
                self._etch_sub_id = "0"

    # 9 misc_pkg_lines         'SUBCLASS', 'PAD_SHAPE_NAME', 'GRAPHIC_DATA_NAME', 'GRAPHIC_DATA_NUMBER',
    #                          'RECORD_TAG', 'GRAPHIC_DATA_1', 'GRAPHIC_DATA_2', 'GRAPHIC_DATA_3', 'GRAPHIC_DATA_4',
    #                          'GRAPHIC_DATA_5', 'GRAPHIC_DATA_6', 'GRAPHIC_DATA_7', 'GRAPHIC_DATA_8',
    #                          'GRAPHIC_DATA_9', 'PAD_STACK_NAME', 'REFDES', 'PIN_NUMBER'
    def _read_misc_pkg_lines(self, data):
        pass

    # 10 misc_pkg_lines2       'SUBCLASS', 'PAD_SHAPE_NAME', 'GRAPHIC_DATA_NAME', 'GRAPHIC_DATA_NUMBER',
    #                          'RECORD_TAG', 'GRAPHIC_DATA_1', 'GRAPHIC_DATA_2', 'GRAPHIC_DATA_3', 'GRAPHIC_DATA_4',
    #                          'GRAPHIC_DATA_5', 'GRAPHIC_DATA_6', 'GRAPHIC_DATA_7', 'GRAPHIC_DATA_8', 'GRAPHIC_DATA_9',
    #                          'PAD_STACK_NAME'
    def _read_misc_pkg_lines2(self, data):
        pass

    def export(self, path):
        """
        Export all to the target path
        :param str path: the target path
        :return:
        """
        self.export_outline(path)
        self.export_pads(path)
        self.export_components(path)
        compress(path)

    def main(self):
        pass

    def _combine_component_meshes(self, component):
        if self.packages[component.SYM_NAME].mesh is None:
            return

        _mesh_data = self.packages[component.SYM_NAME].mesh.copy()

        _mesh = mesh.Mesh(_mesh_data)
        if component.SYM_MIRROR:
            _mesh.rotate([0, 1, 0], np.radians(180))

        if component.SYM_ROTATE > 0:
            _mesh.rotate([0, 0, 1], np.radians(-component.SYM_ROTATE))

        z = -BOARD_HEIGHT / 2 if component.SYM_MIRROR else BOARD_HEIGHT / 2
        layer = 'BOTTOM' if component.SYM_MIRROR else 'TOP'
        _mesh.translate((component.center[0], component.center[1], z))

        if self._meshes[layer] is None:
            self._meshes[layer] = _mesh.data
        else:
            self._meshes[layer] = np.concatenate([self._meshes[layer], _mesh.data])

    def _export_component_model(self, path):
        """
        Export the model file of components for simulation
        :param str path: the target path to export model file
        :return:
        """
        layers = ['TOP', 'BOTTOM']

        component_model_path = os.path.join(path, 'models', 'Components')
        if not os.path.exists(component_model_path):
            os.makedirs(component_model_path)

        # For simulation, should export the STL files of top and bottom side.
        mesh_files = {
            'TOP': os.path.abspath(os.path.join(path, 'meshes', 'TOP.stl')),
            'BOTTOM': os.path.abspath(os.path.join(path, 'meshes', 'BOTTOM.stl'))
        }
        mesh.Mesh(self._meshes['TOP']).save(mesh_files['TOP'])
        mesh.Mesh(self._meshes['BOTTOM']).save(mesh_files['BOTTOM'])

        root_node = ET.Element('sdf')
        root_node.set('version', '1.6')
        model_node = ET.SubElement(root_node, 'model')
        model_node.set('name', 'Components')

        for layer in layers:
            link_node = ET.SubElement(model_node, 'link')
            link_node.set('name', layer + '_link')

            collision_node = ET.SubElement(link_node, 'collision')
            collision_node.set('name', layer + '_collision')
            geometry_node = ET.SubElement(collision_node, 'geometry')
            mesh_node = ET.SubElement(geometry_node, 'mesh')
            uri_node = ET.SubElement(mesh_node, 'uri')
            uri_node.text = 'file://' + mesh_files[layer]

            visual_node = ET.SubElement(link_node, 'visual')
            visual_node.set('name', layer + '_visual')
            geometry_node = ET.SubElement(visual_node, 'geometry')
            mesh_node = ET.SubElement(geometry_node, 'mesh')
            uri_node = ET.SubElement(mesh_node, 'uri')
            uri_node.text = 'file://' + mesh_files[layer]

        tree = ET.ElementTree(root_node)
        tree.write(os.path.join(component_model_path, 'model.sdf'), encoding='utf-8', xml_declaration=True)

    def export_components(self, path, sim=False):
        """
        Export the components information
        :param str path: the target path to export
        :param bool sim: whether need to output the files for simulation
        :return:
        """
        tx, ty = self.outline.offset()
        component_configs = {}

        for ref in self.components:
            component = self.components[ref]
            if not component.package:
                continue

            cx, cy = component.package.center()
            component.center = (cx * SCALE_RATE - tx, cy * SCALE_RATE - ty)
            sym = component.SYM_NAME
            component.bind_pads(self.pads)

            # if sym in self.packages:
            #     component.package = self.packages[sym]
            # else:
            component.export_package(path, sim)
            self.packages[sym] = component.package

            if sim:
                self._combine_component_meshes(component)

            component.export_svg_model(path)
            component_configs[component.REFDES] = {
                "c": component.center,
                "r": component.SYM_ROTATE,
                "m": component.SYM_MIRROR,
                "p": component.SYM_NAME
            }

        component_configs_fp = open(os.path.join(path, 'ComponentConfigs.json'), 'w')
        json.dump(component_configs, component_configs_fp)
        component_configs_fp.close()

        if sim:
            self._export_component_model(path)

    def export_outline(self, path):
        """
        Export the board outline information
        :param str path: the target path to export
        :return:
        """

        # Scale the outline
        self.outline.scale(SCALE_RATE)
        # Export the STL file of the outline
        self.outline.save(path)
        # Export the UV Map info of the board
        self.outline.uv_map(self.copper, path)

    def export_pads(self, path):
        """
        Export the pads information of the board
        :param str path: the target path to export
        :return:
        """
        for name in self.pads:
            for pad in self.pads[name]:
                if pad.geometry is not None:
                    pad.scale(SCALE_RATE)


if __name__ == "__main__":
    import datetime

    CAD_FILE_PATH = os.path.join(os.environ['HOME'], '.teleprobe', 'cad', '28-11353-03')
    FILENAME = os.path.join(CAD_FILE_PATH, '28-11353-03_A0_fbm.cad')
    # FILENAME = "../../test/package.cad"

    time1 = datetime.datetime.now()
    print time1

    fab = FabMaster(FILENAME)
    fab.parse()

    print datetime.datetime.now() - time1

    # fab.main()
    # fab.outline._save_to_obj()
    # fab.uv()
    fab.export(os.path.join(CAD_FILE_PATH, 'data'))

    print "Done"
    time2 = datetime.datetime.now()
    print time2
    print time2 - time1
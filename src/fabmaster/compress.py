import os
import zipfile


def compress(path):
    """
    Compress files to a zip file
    :param str path: the path of files which will be compressed.
    """
    orig_work_path = os.getcwd()

    try:
        os.chdir(path)
    except IOError:
        print "%s is not found" % path

    with zipfile.ZipFile('data.zip', 'w') as zf:
        for root, dirs, files, in os.walk(os.path.join('.', 'meshes', 'packages')):
            for f in files:
                zf.write(os.path.join(root, f))

        for root, dirs, files, in os.walk(os.path.join('.', 'meshes', 'pads')):
            for f in files:
                zf.write(os.path.join(root, f))

        zf.write(os.path.join('.', 'meshes', 'outline.obj'))

        if os.path.isfile(os.path.join('.', 'meshes', 'outline.obj.mtl')):
            zf.write(os.path.join('.', 'meshes', 'outline.obj.mtl'))
        else:
            zf.write(os.path.join('.', 'meshes', 'outline.mtl'))

        zf.write(os.path.join('.', 'meshes', '_outline_.jpg'))
        zf.write(os.path.join('.', 'ComponentConfigs.json'))

    os.chdir(orig_work_path)


if __name__ == '__main__':
    compress('./')
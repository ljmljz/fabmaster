try:
    import _geometry as geo
except:
    raise


def triangulate(points):
    """
    Triangulate the polygon
    :param list points: polygon points
    :return: the vertices of the polygon
    :rtype list
    """
    vertices = None
    try:
        geometry = geo.Geometry(points)
        vertices = geometry.triangulate()

        del geometry
    except:
        raise

    return vertices


def extrude(points, height):
    """
    Extrude the polygon
    :param list points: polygon points
    :param float height: the height of the 3d object
    :return: the faces and the vertices
    :rtype dict
    """
    result = None

    try:
        geometry = geo.Geometry(points)
        geometry.triangulate()
        geometry.extrude(height)

        result = {
            "faces": geometry.faces,
            "vertices": geometry.vertices
        }

        del geometry
    except:
        raise

    return result

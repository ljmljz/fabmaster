#include "Python.h"
#include <structmember.h>
#include "earcut.hpp"
#include "numpy/arrayobject.h"

#include <array>
#include <vector>
#include <iostream>

#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION

//using namespace std;

typedef struct _Geometry {
    PyObject_HEAD
    PyObject* mPolygon;         // 2D data, it's a list
    PyObject* mVertices;        // 3D vertices
    PyObject* mFaces;           // 3D faces
} Geometry;

using Point = std::array<float, 2>;
using Points = std::vector<Point>;
using Polygon = std::vector<std::vector<Point>>;
using N = uint32_t;

static PyMemberDef Geometry_DataMembers[] = {
    {"mPolygon", T_OBJECT, offsetof(Geometry, mPolygon), 0, "The 2D polygon of the geometry"},
    {"mVertices", T_OBJECT, offsetof(Geometry, mVertices), 0, "The vertices of the geometry"},
    {"mFaces", T_OBJECT, offsetof(Geometry, mFaces), 0, "The faces of the geometry"},

    {NULL} /* Sentinel */
};

static void Geometry_SetPolygon(Geometry* self, PyObject* pArgs) {
    PyObject* polygon = NULL;

    if (! PyArg_ParseTuple(pArgs, "O!", &PyList_Type, &polygon)) {
        self->mPolygon = NULL;
    } else {
        self->mPolygon = polygon;
        Py_INCREF(self->mPolygon);
    }
}

static PyObject* Geometry_GetPolygon(Geometry* self) {
    Py_INCREF(self->mPolygon);
    return self->mPolygon;
}

static PyObject* Geometry_GetFaces(Geometry* self) {
    Py_INCREF(self->mFaces);
    return self->mFaces;
}

static PyObject* Geometry_GetVertices(Geometry* self) {
    double* valPtr = NULL;

    if (self->mPolygon == NULL) {
        return NULL;
    } else if (self->mVertices == NULL) {
        npy_intp totalSize = 0;
        PyObject* pyPointsObj = NULL;
        N size = 0;
        N index = 0;
        N pointsObjSize = 0;
        N i, j;

        size = PyList_Size(self->mPolygon);
        for(i=0; i<size; i++) {
            pyPointsObj = PyList_GetItem(self->mPolygon, i);
            pointsObjSize = PyList_Size(pyPointsObj);

            for(j=0; j<pointsObjSize; j+=2) {
                totalSize++;
            }
        }

        npy_intp dims[2] = {totalSize, 3};
        self->mVertices = PyArray_SimpleNew(2, dims, NPY_DOUBLE);
        Py_INCREF(self->mVertices);

        for(i=0; i<size; i++) {
            pyPointsObj = PyList_GetItem(self->mPolygon, i);
            pointsObjSize = PyList_Size(pyPointsObj);

            for(j=0; j<pointsObjSize; j+=2) {
                valPtr = (double *)PyArray_GETPTR2(self->mVertices, index, 0);
                *valPtr = PyFloat_AsDouble(PyList_GetItem(pyPointsObj, j));

                valPtr = (double *)PyArray_GETPTR2(self->mVertices, index, 1);
                *valPtr = PyFloat_AsDouble(PyList_GetItem(pyPointsObj, j + 1));

                valPtr = (double *)PyArray_GETPTR2(self->mVertices, index, 2);
                *valPtr = 0.0;

                index++;
            }
        }

        Py_INCREF(self->mVertices);
        return self->mVertices;
    } else {
        Py_INCREF(self->mVertices);
        return self->mVertices;
    }
}

static PyObject* Geometry_Triangulate(Geometry* self) {
    PyObject* pyPointsObj = NULL;
    N size = 0;
    N pointsObjSize = 0;

    Polygon polygon;
    Points points;
    Point point;

    N i,j;

    if (!self->mPolygon) return NULL;

    size = PyList_Size(self->mPolygon);

    for(N i=0; i<size; i++) {
        pyPointsObj = PyList_GetItem(self->mPolygon, i);
        pointsObjSize = PyList_Size(pyPointsObj);

        for(N j=0; j<pointsObjSize; j+=2) {
            point[0] = PyFloat_AsDouble(PyList_GetItem(pyPointsObj, j));
            point[1] = PyFloat_AsDouble(PyList_GetItem(pyPointsObj, j + 1));

            points.push_back(point);
        }

        polygon.push_back(points);
        points.clear();
    }

    if (polygon.empty()) return NULL;

    std::vector<N> indices = mapbox::earcut<N>(polygon);
    polygon.clear();

    npy_intp indicesSize = indices.size();
    npy_intp dims[2] = {indicesSize / 3, 3};
    //std::cout<<indices.size()<<"\n";
    /*
    for(N i=0; i<indicesSize; i++) {
        std::cout << *((&indices[0])+i) << ",";
    }
    */
    self->mFaces = PyArray_SimpleNew(2, dims, NPY_UINT32);
    Py_INCREF(self->mFaces);

    //memcpy(PyArray_DATA(self->mFaces), indices.data(), indicesSize);
    uint32_t* data = (uint32_t*)PyArray_DATA(self->mFaces);
    for (N i=0; i<indicesSize; i++) {
        data[i] = indices.at(i);
    }

    Py_INCREF(self->mFaces);
    return self->mFaces;
}

static PyObject* Geometry_Extrude(Geometry* self, PyObject* pArgs) {
    PyObject* tmp = NULL;
    N i;

    if (self->mVertices == NULL) {
        if(Geometry_GetVertices(self) == NULL) {
            return NULL;
        }
    }

    double val;
    if (! PyArg_ParseTuple(pArgs, "d", &val)) {
        return NULL;
    }

    if (self->mFaces == NULL) {
        if(Geometry_Triangulate(self) == NULL) {
            return NULL;
        }
    }

    // number of vertices
    uint32_t num = PyArray_Size(self->mVertices) / 3;

    // extend vertices
    PyArray_Descr* vertexDescr = PyArray_DescrFromType(NPY_DOUBLE);
    PyObject* newVertices = PyArray_FromArray((PyArrayObject *)self->mVertices, vertexDescr, NPY_ARRAY_ENSURECOPY);

    double* ptr = (double*)PyArray_DATA(newVertices);
    for(i=0; i<PyArray_Size(newVertices); i+=3) {
        ptr[i + 2] += val;
    }

    PyObject* vertxOpSeq = PyList_New(2);

    if(val > 0) {
        PyList_SET_ITEM(vertxOpSeq, 0, newVertices);
        PyList_SET_ITEM(vertxOpSeq, 1, self->mVertices);
    } else {
        PyList_SET_ITEM(vertxOpSeq, 0, self->mVertices);
        PyList_SET_ITEM(vertxOpSeq, 1, newVertices);
    }
    PyObject* totalVertices = PyArray_Concatenate(vertxOpSeq, 0);

    // extend faces
    PyArray_Descr* faceDescr = PyArray_DescrFromType(NPY_UINT32);
    PyObject* newFaces = PyArray_FromArray((PyArrayObject *)self->mFaces, faceDescr, NPY_ARRAY_ENSURECOPY);
    uint32_t* newValPtr = (uint32_t*)PyArray_DATA(newFaces);
    uint32_t* valPtr = (uint32_t*)PyArray_DATA(self->mFaces);

    for(i=0; i<PyArray_Size(newFaces); i+=3) {
        //valPtr[i] += num;
        newValPtr[i] = valPtr[i + 2] + num;
        newValPtr[i + 1] = valPtr[i + 1] + num;
        newValPtr[i + 2] = valPtr[i] + num;
    }

    // connect surface
    npy_intp dims[2] = {num * 2, 3};
    PyObject* connFaces = PyArray_SimpleNew(2, dims, NPY_UINT32);
    valPtr = (uint32_t*)PyArray_DATA(connFaces);
    uint32_t vertexIndex = 0;

    for(N i=0; i<PyList_Size(self->mPolygon); i++) {
        PyObject* pyPointsObj = PyList_GetItem(self->mPolygon, i);

        for(N j=0; j<PyList_Size(pyPointsObj) / 2; j++) {
            uint32_t next = j + 1;
            if (next >= PyList_Size(pyPointsObj) / 2) {
                next = vertexIndex - j;
            } else {
                next = vertexIndex + 1;
            }
            /*
            valPtr[vertexIndex * 6] = vertexIndex + num;
            valPtr[vertexIndex * 6 + 1] = vertexIndex;
            valPtr[vertexIndex * 6 + 2] = next;

            valPtr[vertexIndex * 6 + 3] = next;
            valPtr[vertexIndex * 6 + 4] = next + num;
            valPtr[vertexIndex * 6 + 5] = vertexIndex + num;
            */
            valPtr[vertexIndex * 6] = next;
            valPtr[vertexIndex * 6 + 1] = vertexIndex;
            valPtr[vertexIndex * 6 + 2] = vertexIndex + num;

            valPtr[vertexIndex * 6 + 3] = vertexIndex + num;
            valPtr[vertexIndex * 6 + 4] = next + num;
            valPtr[vertexIndex * 6 + 5] = next;

            vertexIndex++;
        }
    }

    PyObject* faceOpSeq = PyList_New(3);
    PyList_SET_ITEM(faceOpSeq, 0, self->mFaces);
    PyList_SET_ITEM(faceOpSeq, 1, newFaces);
    PyList_SET_ITEM(faceOpSeq, 2, connFaces);
    PyObject* totalFaces = PyArray_Concatenate(faceOpSeq, 0);

    tmp = self->mVertices;
    self->mVertices = totalVertices;
    Py_INCREF(self->mVertices);
    Py_DECREF(tmp);

    tmp = self->mFaces;
    self->mFaces = totalFaces;
    Py_INCREF(self->mFaces);
    Py_DECREF(tmp);

    Py_INCREF(self->mFaces);
    return self->mFaces;
}

static int Geometry_init(Geometry* self, PyObject* pArgs) {
    //self->mVertices = NULL;
    //self->mFaces = NULL;

    Geometry_SetPolygon(self, pArgs);

    return 0;
}

static void Geometry_Destruct(Geometry* self) {
    if (self->mPolygon) Py_XDECREF(self->mPolygon);
    if (self->mVertices) Py_XDECREF(self->mVertices);
    if (self->mFaces) Py_XDECREF(self->mFaces);

    Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject* Geometry_new(PyTypeObject *type, PyObject *args, PyObject *kwds)
{
    Geometry *self;

    self = (Geometry *)type->tp_alloc(type, 0);
    if (self != NULL) {
        self->mPolygon = NULL;
        self->mVertices = NULL;
        self->mFaces = NULL;
    }

    return (PyObject *)self;
}

static PyObject* Geometry_Str(Geometry* self) {
    const char str[] = "C++ Geometry";

    return Py_BuildValue("s", str);
}

static PyObject* Geometry_Repr(Geometry* self) {
    return Geometry_Str(self);
}

/*
    methods in the class.
 */
static PyMethodDef Geometry_MethodMembers[] =      
{
    {"triangulate",    (PyCFunction)Geometry_Triangulate, METH_NOARGS, "Triangulate the polygon"},
    {"extrude",    (PyCFunction)Geometry_Extrude, METH_VARARGS, "Extrude the geometry"},

    {NULL}
};

static PyGetSetDef Geometry_GetSeters[] = {
    {"polygon", (getter)Geometry_GetPolygon, (setter)Geometry_SetPolygon, "Polygon", NULL},
    {"faces", (getter)Geometry_GetFaces, NULL, "Faces", NULL},
    {"vertices", (getter)Geometry_GetVertices, NULL, "Vertices", NULL},

    {NULL}  /* Sentinel */
};

static PyTypeObject Geometry_ClassInfo =
{
    PyVarObject_HEAD_INIT(NULL, 0)
    "geometry.Geometry",                                    // tp_name
    sizeof(Geometry),                                       // tp_basicsize
    0,                                                      // tp_itemsize
    (destructor)Geometry_Destruct,                          // tp_dealloc
    0,                                                      // tp_print
    0,                                                      // tp_getattr
    0,                                                      // tp_setatter
    0,                                                      // tp_compare
    (reprfunc)Geometry_Repr,                                // tp_repr
    0,                                                      // tp_as_number
    0,                                                      // tp_as_sequence
    0,                                                      // tp_as_mapping
    0,                                                      // tp_hash
    0,                                                      // tp_call
    (reprfunc)Geometry_Str,                                 // tp_str
    0,                                                      // tp_getattro
    0,                                                      // tp_setattro
    0,                                                      // tp_as_buffer
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,               // tp_flags
    "Geometry Objects---Extensioned by C++!",               // tp_doc
    0,                                                      // tp_traverse
    0,                                                      // tp_clear
    0,                                                      // tp_richcompare
    0,                                                      // tp_weaklistoffset
    0,                                                      // tp_iter
    0,                                                      // tp_iternext
    Geometry_MethodMembers,                                 // tp_methods
    Geometry_DataMembers,                                   // tp_members
    Geometry_GetSeters,                                     // tp_getset
    0,                                                      // tp_base
    0,                                                      // tp_dict
    0,                                                      // tp_descr_get
    0,                                                      // tp_descr_set
    0,                                                      // tp_dictoffset
    (initproc)Geometry_init,                                // tp_init
    0,                                                      // tp_alloc
    Geometry_new,                                           // tp_new
};

PyMODINIT_FUNC init_geometry() {
    PyObject* pReturn = 0;
    Geometry_ClassInfo.tp_new = PyType_GenericNew;       //此类的new内置函数—建立对象.

    if(PyType_Ready(&Geometry_ClassInfo) < 0)
        return;

    pReturn = Py_InitModule3("_geometry", Geometry_MethodMembers, "extension for geometry methods");
    Py_INCREF(&Geometry_ClassInfo);
    PyModule_AddObject(pReturn, "Geometry", (PyObject*)&Geometry_ClassInfo); //将这个类加入到模块的Dictionary中.

    import_array();
}

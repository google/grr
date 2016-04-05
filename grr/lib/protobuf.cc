// A python module to parse/serialize from internal representation to protobuf
// wire format.

#include <Python.h>


static PyMethodDef ProtobufMethods[] = {
  {NULL, NULL, 0, NULL}        /* Sentinel */
};

PyMODINIT_FUNC
initprotobuf(void) {
  PyObject *m;
  m = Py_InitModule("protobuf", ProtobufMethods);
  if (m == NULL)
    return;
}

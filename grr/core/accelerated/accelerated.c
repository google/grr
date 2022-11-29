// Semantic Protobufs acceleration library.
//
// This file implementats some hot functions in c to accelerate python semantic
// protobufs.
//
// author: Michael Cohen <scudette@gmail.com>

// See https://docs.python.org/3/c-api/intro.html#include-files
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <limits.h>

// Number of bits used to hold type info in a proto tag.
#define TAG_TYPE_BITS 3
#define TAG_TYPE_MASK ((1 << TAG_TYPE_BITS) - 1)  // 0x7

// These numbers identify the wire type of a protocol buffer value.
// We use the least-significant TAG_TYPE_BITS bits of the varint-encoded
// tag-and-type to store one of these WIRETYPE_* constants.
// These values must match WireType enum in google/protobuf/wire_format.h.
#define WIRETYPE_VARINT 0
#define WIRETYPE_FIXED64 1
#define WIRETYPE_LENGTH_DELIMITED 2

// We do not support these deprecated wire types any more. Nested protobufs are
// stored using the normal WIRETYPE_LENGTH_DELIMITED tag.
#define WIRETYPE_START_GROUP 3
#define WIRETYPE_END_GROUP 4

#define WIRETYPE_FIXED32 5
#define _WIRETYPE_MAX 5


// Encode the value into the buffer as a Varint.  length contains the size of
// the buffer, we set it to the total length of the written Varint.  Returns 1
// on success and 0 if an error occurs. The only possible error is that value
// can not be encoded into the buffer because it is too short.
int varint_encode(unsigned PY_LONG_LONG value,
                  unsigned char *buffer, Py_ssize_t *length) {
  Py_ssize_t index = 0;
  unsigned char bits = value & 0x7f;
  value >>= 7;
  while (value) {
    buffer[index] = bits | 0x80;
    index++;

    // Buffer is too short.
    if (index >= *length)
      return 0;

    bits = value & 0x7f;
    value >>= 7;
  }

  buffer[index] = bits;
  index++;

  *length = index;
  return 1;
}


PyObject *py_varint_encode(PyObject *self, PyObject *args) {
  unsigned char buffer[100];
  Py_ssize_t index = sizeof(buffer);
  unsigned PY_LONG_LONG value;
  const char *fmt = "y#";

  if (!PyArg_ParseTuple(args, "K", &value))
    return NULL;

  // Can't really happen but just in case.
  if (!varint_encode(value, buffer, &index)) {
    PyErr_SetString(
        PyExc_RuntimeError, "Internal Error");
    return NULL;
  }


  return Py_BuildValue(fmt, buffer, index);
}


int varint_decode(unsigned PY_LONG_LONG *result,
                  const char *buffer, Py_ssize_t length,
                  Py_ssize_t *decoded_length) {
  Py_ssize_t pos = 0;
  unsigned int shift = 0;

  *result = 0;

  while (shift < (sizeof(*result) * 8) && pos < length) {
    unsigned char b = buffer[pos];
    *result |= ((unsigned PY_LONG_LONG)(b) & 0x7F) << shift;
    pos++;

    if ( (b & 0x80) == 0 ) {
      if (decoded_length) {
        *decoded_length = pos;
      }
      return 1;
    }

    shift += 7;
  }

  // Error decoding varint - buffer too short.
  return 0;
}


PyObject *py_varint_decode(PyObject *self, PyObject *args) {
  const char *buffer;
  Py_ssize_t pos = 0;
  Py_ssize_t length = 0;
  unsigned PY_LONG_LONG result = 0;
  const char *fmt = "y#n";

  if (!PyArg_ParseTuple(args, fmt, &buffer, &length, &pos))
    return NULL;

  if (varint_decode(&result, buffer+pos, length, &length)) {
    return Py_BuildValue("Kn", result, pos + length);
  }

  PyErr_SetString(PyExc_ValueError, "Too many bytes when decoding varint.");
  return NULL;
}


PyObject *py_split_buffer(PyObject *self, PyObject *args, PyObject *kwargs) {
  char *buffer;
  Py_ssize_t buffer_len = 0;
  Py_ssize_t length = 0;
  Py_ssize_t index = 0;
  static const char *kwlist[] = {"buffer", "index", "length", NULL};
  PyObject *encoded_tag = NULL;
  PyObject *result = NULL;

  if (!PyArg_ParseTupleAndKeywords(args, kwargs, "s#|nn", (char **)kwlist,
                                   &buffer, &buffer_len, &index, &length)) {
    goto error;
  }

  if (index < 0 || length < 0 || index > buffer_len) {
    PyErr_SetString(
        PyExc_ValueError, "Invalid parameters.");
    goto error;
  }

  // Advance the buffer to the required start index.
  buffer += index;

  // Determine the length we will be splitting.
  if (length == 0 || length > buffer_len - index) {
    length = buffer_len - index;
  }

  result = PyList_New(0);
  if (!result) {
    goto error;
  }

  // We advance the buffer and decrement the length until there is no more
  // buffer space left.
  while (length > 0) {
    Py_ssize_t decoded_length = 0;
    unsigned PY_LONG_LONG tag;
    int tag_type;

    // Read the tag off the buffer.
    if (!varint_decode(&tag, buffer, length, &decoded_length)) {
      PyErr_SetString(
          PyExc_ValueError, "Broken tag encountered.");
      goto error;
    }

    if (decoded_length == 0) {
      // NOTE: this code is unreachable - decoded length should never be 0,
      // as the current implementation of varint_decode always sets
      // decoded_length to non-zero on success.
      //
      // Keeping the check here, just in case (i.e. in case varint_decode
      // implementation changes).
      PyErr_SetString(
          PyExc_ValueError, "Zero-length tag encountered.");
      goto error;
    }

    // Prepare to pass the encoded tag into the result tuple.
    encoded_tag = PyBytes_FromStringAndSize(buffer, decoded_length);
    buffer += decoded_length;
    length -= decoded_length;

    // Handle the tag depending on its type.
    tag_type = tag & TAG_TYPE_MASK;
    switch (tag_type) {
      case WIRETYPE_VARINT: {
        // Decode the varint and position ourselves at the next tag.
        Py_ssize_t tag_length = 0;
        PyObject *entry = NULL;

        if (!varint_decode(&tag, buffer, length, &tag_length)) {
          PyErr_SetString(
              PyExc_ValueError, "Broken varint tag encountered.");
          goto error;
        }

        // Create an entry to add to the result set. Note: We use
        // PyTuple_SetItem which steals the references here instead of
        // PyTuple_Pack which does not (meaning its more involved to use).
        entry = PyTuple_New(3);
        PyTuple_SET_ITEM(
            entry, 0, encoded_tag);
        encoded_tag = NULL; // Ensure it doesn't get accidentally dereferenced.

        // Empty string "".
        PyTuple_SET_ITEM(
            entry, 1,
            PyBytes_FromStringAndSize(buffer, 0));

        PyTuple_SET_ITEM(
            entry, 2,
            PyBytes_FromStringAndSize(buffer, tag_length));

        PyList_Append(result, entry);
        Py_DECREF(entry);

        buffer += tag_length;
        length -= tag_length;

        break;
      }

      case WIRETYPE_FIXED64: {
        // Fixed size data.
        Py_ssize_t tag_length = 8;

        if (length < tag_length) {
          PyErr_SetString(
              PyExc_ValueError, "Fixed64 tag exceeds available buffer.");
          goto error;
        }

        PyObject *entry = PyTuple_New(3);
        PyTuple_SET_ITEM(
            entry, 0, encoded_tag);
        encoded_tag = NULL; // Ensure it doesn't get accidentally dereferenced.

        // Empty string "".
        PyTuple_SET_ITEM(
            entry, 1,
            PyBytes_FromStringAndSize(buffer, 0));

        PyTuple_SET_ITEM(
            entry, 2,
            PyBytes_FromStringAndSize(buffer, tag_length));

        PyList_Append(result, entry);
        Py_DECREF(entry);

        buffer += tag_length;
        length -= tag_length;

        break;
      }

      case WIRETYPE_FIXED32: {
        // Fixed size data.
        Py_ssize_t tag_length = 4;

        if (length < tag_length) {
          PyErr_SetString(
              PyExc_ValueError, "Fixed32 tag exceeds available buffer.");
          goto error;
        }

        PyObject *entry = PyTuple_New(3);
        PyTuple_SET_ITEM(
            entry, 0, encoded_tag);
        encoded_tag = NULL; // Ensure it doesn't get accidentally dereferenced.

        // Empty string "".
        PyTuple_SET_ITEM(
            entry, 1,
            PyBytes_FromStringAndSize(buffer, 0));

        PyTuple_SET_ITEM(
            entry, 2,
            PyBytes_FromStringAndSize(buffer, tag_length));

        PyList_Append(result, entry);
        Py_DECREF(entry);

        buffer += tag_length;
        length -= tag_length;

        break;
      }

      case WIRETYPE_LENGTH_DELIMITED: {
        // Decode the length varint and position ourselves at the start of the
        // data.
        Py_ssize_t decoded_length = 0;
        unsigned PY_LONG_LONG data_size;
        PyObject *entry = NULL;

        if (!varint_decode(&data_size, buffer, length, &decoded_length)) {
          PyErr_SetString(
              PyExc_ValueError, "Broken length_delimited tag encountered.");
          goto error;
        }

        if (data_size > INT_MAX) {
          PyErr_SetString(
              PyExc_ValueError, "Length delimited exceeds limits.");
          goto error;
        }

        // Check that we do not exceed the available buffer here.
        if (data_size + decoded_length > (unsigned int)length) {
          PyErr_SetString(
              PyExc_ValueError, "Length tag exceeds available buffer.");
          goto error;
        }

        entry = PyTuple_New(3);
        PyTuple_SET_ITEM(
            entry, 0, encoded_tag);
        encoded_tag = NULL; // Ensure it doesn't get accidentally dereferenced.

        // Empty string "".
        PyTuple_SET_ITEM(
            entry, 1,
            PyBytes_FromStringAndSize(buffer, decoded_length));

        PyTuple_SET_ITEM(
            entry, 2,
            PyBytes_FromStringAndSize(buffer + decoded_length, data_size));

        PyList_Append(result, entry);
        Py_DECREF(entry);

        buffer += decoded_length + data_size;
        length -= decoded_length + data_size;

        break;
      }

      default:
        PyErr_SetString(
            PyExc_ValueError, "Unexpected Tag");
        goto error;
    }
  }

  return result;

error:
  Py_XDECREF(result);
  Py_XDECREF(encoded_tag);

  return NULL;
}

/* Retrieves the semantic protobuf version
 * Returns a Python object if successful or NULL on error
 */
PyObject *py_semantic_get_version(PyObject *self, PyObject *arguments) {
    const char *errors = NULL;
    return(PyUnicode_DecodeUTF8("20150518", (Py_ssize_t) 8, errors));
}

static PyMethodDef _semantic_methods[] = {
    {"get_version",
     (PyCFunction)py_semantic_get_version,
     METH_NOARGS,
     "get_version() -> String\n"
     "\n"
     "Retrieves the version."},

    {"varint_encode",
     (PyCFunction)py_varint_encode,
     METH_VARARGS,
     "Encode an integer into a varint."},

    {"varint_decode",
     (PyCFunction)py_varint_decode,
     METH_VARARGS,
     "Decode a varint from a buffer."},

    {"split_buffer",
     (PyCFunction)py_split_buffer,
     METH_VARARGS | METH_KEYWORDS,
     "Split a buffer into tags and wire format data."},

    {NULL}  /* Sentinel */
};


static struct PyModuleDef cSemanticMod =
{
    PyModuleDef_HEAD_INIT,
    "_semantic", /* name of module */
    "",          /* module documentation, may be NULL */
    -1,          /* size of per-interpreter state of the module, or -1 if the module keeps state in global variables. */
    _semantic_methods
};

PyMODINIT_FUNC PyInit__semantic(void) {
  return PyModule_Create(&cSemanticMod);
}


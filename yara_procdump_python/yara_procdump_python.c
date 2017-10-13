/*

Python bindings for the Yara process memory dumping functionality.

Some of this code is based on yara-python.c from
https://github.com/VirusTotal/yara-python

*/

#include <Python.h>
#include <structmember.h>

#if PY_VERSION_HEX >= 0x02060000
#include <bytesobject.h>
#elif PY_VERSION_HEX < 0x02060000
#define PyBytes_AsString PyString_AsString
#define PyBytes_Check PyString_Check
#define PyBytes_FromStringAndSize PyString_FromStringAndSize
#endif

#include <time.h>
#include <yara.h>
#include <yara/proc.h>

#ifndef PyVarObject_HEAD_INIT
#define PyVarObject_HEAD_INIT(type, size) PyObject_HEAD_INIT(type) size,
#endif

/* Module globals */

static PyObject* YaraError = NULL;
static PyObject* YaraTimeoutError = NULL;


#define YARA_DOC "\
This module allows you to use the Yara process memory dumping functionality.\n"


PyObject* handle_error(
    int error,
    char* extra)
{
  switch(error)
  {
    case ERROR_COULD_NOT_ATTACH_TO_PROCESS:
      return PyErr_Format(
          YaraError,
          "access denied");
    case ERROR_INSUFFICIENT_MEMORY:
      return PyErr_NoMemory();
    case ERROR_COULD_NOT_OPEN_FILE:
      return PyErr_Format(
          YaraError,
          "could not open file \"%s\"",
          extra);
    case ERROR_COULD_NOT_MAP_FILE:
      return PyErr_Format(
          YaraError,
          "could not map file \"%s\" into memory",
          extra);
    case ERROR_INVALID_FILE:
      return PyErr_Format(
          YaraError,
          "invalid rules file \"%s\"",
          extra);
    case ERROR_CORRUPT_FILE:
      return PyErr_Format(
          YaraError,
          "corrupt rules file \"%s\"",
          extra);
    case ERROR_SCAN_TIMEOUT:
      return PyErr_Format(
          YaraTimeoutError,
          "scanning timed out");
    case ERROR_INVALID_EXTERNAL_VARIABLE_TYPE:
      return PyErr_Format(
          YaraError,
          "external variable \"%s\" was already defined with a different type",
          extra);
    case ERROR_UNSUPPORTED_FILE_VERSION:
      return PyErr_Format(
          YaraError,
          "rules file \"%s\" is incompatible with this version of YARA",
          extra);
    default:
      return PyErr_Format(
          YaraError,
          "internal error: %d",
          error);
  }
}

typedef struct
{
  PyObject_HEAD
  YR_MEMORY_BLOCK_ITERATOR* block_iterator;
  YR_MEMORY_BLOCK* block;
} ProcessMemoryIterator;

static PyObject* ProcessMemoryIterator_getattro(
    PyObject* self,
    PyObject* name)
{
  return PyObject_GenericGetAttr(self, name);
}

static void ProcessMemoryIterator_dealloc(PyObject* self);

static PyObject* ProcessMemoryIterator_next(PyObject* self);

static PyTypeObject ProcessMemoryIterator_Type = {
  PyVarObject_HEAD_INIT(NULL, 0)
  "yara.ProcessMemoryIterator",  /*tp_name*/
  sizeof(ProcessMemoryIterator), /*tp_basicsize*/
  0,                          /*tp_itemsize*/
  (destructor) ProcessMemoryIterator_dealloc, /*tp_dealloc*/
  0,                          /*tp_print*/
  0,                          /*tp_getattr*/
  0,                          /*tp_setattr*/
  0,                          /*tp_compare*/
  0,                          /*tp_repr*/
  0,                          /*tp_as_number*/
  0,                          /*tp_as_sequence*/
  0,                          /*tp_as_mapping*/
  0,                          /*tp_hash */
  0,                          /*tp_call*/
  0,                          /*tp_str*/
  ProcessMemoryIterator_getattro, /*tp_getattro*/
  0,                          /*tp_setattro*/
  0,                          /*tp_as_buffer*/
  Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/
  "ProcessMemoryIterator",    /* tp_doc */
  0,                          /* tp_traverse */
  0,                          /* tp_clear */
  0,                          /* tp_richcompare */
  0,                          /* tp_weaklistoffset */
  PyObject_SelfIter,          /* tp_iter */
  (iternextfunc) ProcessMemoryIterator_next,  /* tp_iternext */
  0,                          /* tp_methods */
  0,                          /* tp_members */
  0,                          /* tp_getset */
  0,                          /* tp_base */
  0,                          /* tp_dict */
  0,                          /* tp_descr_get */
  0,                          /* tp_descr_set */
  0,                          /* tp_dictoffset */
  0,                          /* tp_init */
  0,                          /* tp_alloc */
  0,                          /* tp_new */
};

static ProcessMemoryIterator* ProcessMemoryIterator_NEW(void)
{
  ProcessMemoryIterator* it = PyObject_NEW(ProcessMemoryIterator, &ProcessMemoryIterator_Type);
  if (it == NULL)
    return NULL;

  it->block_iterator = NULL;
  it->block = NULL;

  return it;
}

static void ProcessMemoryIterator_dealloc(
    PyObject* self)
{
  ProcessMemoryIterator* it = (ProcessMemoryIterator*) self;

  if (it->block_iterator != NULL)
  {
    yr_process_close_iterator(it->block_iterator);
    PyMem_Free(it->block_iterator);
    it->block_iterator = NULL;
  }
  PyObject_Del(self);
}

typedef struct
{
  PyObject_HEAD
  uint8_t* raw_data;
  size_t size;
  size_t base;
} MemoryBlock;

static void MemoryBlock_dealloc(PyObject* self);

static PyObject * MemoryBlock_data(
    PyObject* self,
    PyObject* args)
{
  MemoryBlock* block = (MemoryBlock*) self;
  return PyBytes_FromStringAndSize(
      (const char *) block->raw_data,
      block->size);
}

static PyMethodDef MemoryBlock_methods[] =
{
  {
    "data",
    (PyCFunction) MemoryBlock_data,
    METH_NOARGS
  },
  {
    NULL,
    NULL
  }
};

static PyMemberDef MemoryBlock_members[] = {
    {"size", T_ULONG, offsetof(MemoryBlock, size), 0,
     "size"},
    {"base", T_ULONG, offsetof(MemoryBlock, base), 0,
     "base"},
    {NULL}
};

static PyObject* MemoryBlock_getattro(
    PyObject* self,
    PyObject* name)
{
  return PyObject_GenericGetAttr(self, name);
}

static int MemoryBlock_getbuffer(
    PyObject *obj,
    Py_buffer *view,
    int flags)
{
  MemoryBlock* self = (MemoryBlock*) obj;
  return PyBuffer_FillInfo(view, obj, self->raw_data, self->size, 1, flags);
}

static PyBufferProcs MemoryBlock_as_buffer = {
#if PY_MAJOR_VERSION < 3
  (readbufferproc) 0,
  (writebufferproc) 0,
  (segcountproc) 0,
  (charbufferproc) 0,
#endif
  (getbufferproc) MemoryBlock_getbuffer,
  (releasebufferproc) 0,
};

static PyTypeObject MemoryBlock_Type = {
  PyVarObject_HEAD_INIT(NULL, 0)
  "yara.MemoryBlock",         /*tp_name*/
  sizeof(MemoryBlock),        /*tp_basicsize*/
  0,                          /*tp_itemsize*/
  (destructor) MemoryBlock_dealloc, /*tp_dealloc*/
  0,                          /*tp_print*/
  0,                          /*tp_getattr*/
  0,                          /*tp_setattr*/
  0,                          /*tp_compare*/
  0,                          /*tp_repr*/
  0,                          /*tp_as_number*/
  0,                          /*tp_as_sequence*/
  0,                          /*tp_as_mapping*/
  0,                          /*tp_hash */
  0,                          /*tp_call*/
  0,                          /*tp_str*/
  MemoryBlock_getattro,       /*tp_getattro*/
  0,                          /*tp_setattro*/
  & MemoryBlock_as_buffer,    /*tp_as_buffer*/
#if PY_MAJOR_VERSION < 3
  Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_NEWBUFFER, /*tp_flags*/
#else
  Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/
#endif
  "MemoryBlock",              /* tp_doc */
  0,                          /* tp_traverse */
  0,                          /* tp_clear */
  0,                          /* tp_richcompare */
  0,                          /* tp_weaklistoffset */
  0,                          /* tp_iter */
  0,                          /* tp_iternext */
  MemoryBlock_methods,        /* tp_methods */
  MemoryBlock_members,        /* tp_members */
  0,                          /* tp_getset */
  0,                          /* tp_base */
  0,                          /* tp_dict */
  0,                          /* tp_descr_get */
  0,                          /* tp_descr_set */
  0,                          /* tp_dictoffset */
  0,                          /* tp_init */
  0,                          /* tp_alloc */
  0,                          /* tp_new */
};

static PyObject* MemoryBlock_NEW(void)
{
  MemoryBlock* block = PyObject_NEW(MemoryBlock, &MemoryBlock_Type);
  if (block == NULL)
    return NULL;

  block->raw_data = NULL;
  block->size = 0;
  block->base = 0;

  return (PyObject*) block;
}

static void MemoryBlock_dealloc(PyObject* self)
{
  MemoryBlock* block = (MemoryBlock*) self;

  block->raw_data = NULL;

  PyObject_Del(self);
}



static PyObject* ProcessMemoryIterator_next(
    PyObject* self)
{
  ProcessMemoryIterator* it = (ProcessMemoryIterator*) self;
  int err;

  // This indicates that the iterator has been used up.
  if (it->block_iterator == NULL)
  {
    PyErr_SetNone(PyExc_StopIteration);
    return NULL;
  }

  // During the first invocation, we need to use get_first_memory_block.
  if (it->block == NULL)
    it->block = yr_process_get_first_memory_block(it->block_iterator);
  else
    it->block = yr_process_get_next_memory_block(it->block_iterator);

  if (it->block == NULL)
  {
    PyErr_SetNone(PyExc_StopIteration);
    return NULL;
  }

  uint8_t* data_ptr = yr_process_fetch_memory_block_data(it->block);
  if (data_ptr == NULL)
  {
    // This is how we are notified that the process is done.
    it->block = NULL;
    err = yr_process_close_iterator(it->block_iterator);
    PyMem_Free(it->block_iterator);
    it->block_iterator = NULL;
    if (err != 0)
    {
      return handle_error(err, NULL);
    }

    PyErr_SetNone(PyExc_StopIteration);
    return NULL;
  }

  MemoryBlock *memory_block = (MemoryBlock *) MemoryBlock_NEW();
  memory_block->size = it->block->size;
  memory_block->base = it->block->base;
  memory_block->raw_data = data_ptr;
  return (PyObject *) memory_block;
}

static PyObject* yara_process_memory_iterator(
    PyObject* self,
    PyObject* args,
    PyObject* keywords)
{
  static char *kwlist[] = {
    "pid", NULL};

  unsigned int pid = UINT_MAX;
  int err;

  ProcessMemoryIterator *result;

  if (!PyArg_ParseTupleAndKeywords(
        args,
        keywords,
        "|I",
        kwlist,
        &pid))
  {
    return PyErr_Format(
        PyExc_TypeError,
        "Error parsing arguments.");
  }

  result = ProcessMemoryIterator_NEW();

  result->block_iterator = PyMem_Malloc(sizeof(YR_MEMORY_BLOCK_ITERATOR));
  if (result->block_iterator == NULL)
    return PyErr_NoMemory();

  // Fail early if we can't access the process with the given pid.
  err = yr_process_open_iterator(pid, result->block_iterator);
  if (err != 0)
  {
    PyMem_Free(result->block_iterator);
    return handle_error(err, NULL);
  }

  result->block = yr_process_get_first_memory_block(result->block_iterator);
  if (result->block == NULL)
  {
    PyMem_Free(result->block_iterator);
    result->block_iterator = NULL;
    return PyErr_NoMemory();
  }
  return (PyObject *) result;
}

void finalize(void)
{
  yr_finalize();
}


static PyMethodDef yara_methods[] = {
  {
    "process_memory_iterator",
    (PyCFunction) yara_process_memory_iterator,
    METH_VARARGS | METH_KEYWORDS,
    "Returns an iterator over blocks of memory of a process.\n"
    "Signature: process_memory_iterator(pid=None)"
  },
  { NULL, NULL }
};

#if PY_MAJOR_VERSION >= 3
#define MOD_ERROR_VAL NULL
#define MOD_SUCCESS_VAL(val) val
#define MOD_INIT(name) PyMODINIT_FUNC PyInit_##name(void)
#define MOD_DEF(ob, name, doc, methods) \
      static struct PyModuleDef moduledef = { \
        PyModuleDef_HEAD_INIT, name, doc, -1, methods, }; \
      ob = PyModule_Create(&moduledef);
#else
#define MOD_ERROR_VAL
#define MOD_SUCCESS_VAL(val)
#define MOD_INIT(name) void init##name(void)
#define MOD_DEF(ob, name, doc, methods) \
      ob = Py_InitModule3(name, methods, doc);
#endif


MOD_INIT(_yara_procdump_python)
{
  PyObject* m;

  MOD_DEF(m, "_yara_procdump_python", YARA_DOC, yara_methods)

  if (m == NULL)
    return MOD_ERROR_VAL;

  /* initialize module variables/constants */

  PyModule_AddStringConstant(m, "__version__", YR_VERSION);
  PyModule_AddStringConstant(m, "YARA_VERSION", YR_VERSION);
  PyModule_AddIntConstant(m, "YARA_VERSION_HEX", YR_VERSION_HEX);

#if PYTHON_API_VERSION >= 1007
  YaraError = PyErr_NewException("yara.Error", PyExc_Exception, NULL);
  YaraTimeoutError = PyErr_NewException("yara.TimeoutError", YaraError, NULL);
#else
  YaraError = Py_BuildValue("s", "yara.Error");
  YaraTimeoutError = Py_BuildValue("s", "yara.TimeoutError");
#endif

  PyModule_AddObject(m, "Error", YaraError);
  PyModule_AddObject(m, "TimeoutError", YaraTimeoutError);

  if (yr_initialize() != ERROR_SUCCESS)
  {
    PyErr_SetString(YaraError, "initialization error");
    return MOD_ERROR_VAL;
  }

  Py_AtExit(finalize);

  return MOD_SUCCESS_VAL(m);
}

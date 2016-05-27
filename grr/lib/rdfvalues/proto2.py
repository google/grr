#!/usr/bin/env python
"""Semantic protocol buffers can be created from proto2 .proto files.

For maintaining inter-operatibility with primitive protocol buffer
implementations, we can parse the field descriptors created by the standard
Google proto implementation, and generate Semantic proto descriptors.

This file contains interoperability code with the Google protocol buffer
library.
"""
import logging

from grr.lib import rdfvalue
from grr.lib import type_info
from grr.proto import semantic_pb2

# Field types present in the proto2 field descriptors.
TYPE_DOUBLE = 1
TYPE_FLOAT = 2
TYPE_INT64 = 3
TYPE_UINT64 = 4
TYPE_INT32 = 5
TYPE_FIXED64 = 6
TYPE_FIXED32 = 7
TYPE_BOOL = 8
TYPE_STRING = 9
TYPE_GROUP = 10
TYPE_MESSAGE = 11
TYPE_BYTES = 12
TYPE_UINT32 = 13
TYPE_ENUM = 14
TYPE_SFIXED32 = 15
TYPE_SFIXED64 = 16
TYPE_SINT32 = 17
TYPE_SINT64 = 18
MAX_TYPE = 18

# These are labels in the descriptor. Semantic protobufs only distinguish
# between optional and repeated labels. Required is not enforced by the library
# - it should be done by the user in their Validate() method.
LABEL_OPTIONAL = 1
LABEL_REQUIRED = 2
LABEL_REPEATED = 3
MAX_LABEL = 3

# Semantic Value data store type specifies how they prefer to be encoded. This
# maps to a proto2 primitive field type. When parsing the .proto file we must
# ensure that the semantic value is getting encoded into the correct primitive
# field type.
_SEMANTIC_PRIMITIVE_TO_FIELD_TYPE = dict(bytes=TYPE_BYTES,
                                         string=TYPE_STRING,
                                         integer=TYPE_INT64,
                                         unsigned_integer=TYPE_UINT64,)


def DefineFromProtobuf(cls, protobuf):
  """Add type info definitions from an existing protobuf.

  We support building this class by copying definitions from an annotated
  protobuf using the semantic protobuf. This is ideal for interoperability
  with other languages and non-semantic protobuf implementations. In that case
  it might be easier to simply annotate the .proto file with the relevant
  semantic information.

  Args:
    cls: The class to add fields descriptors to (i.e. the new semantic class).
    protobuf: A generated proto2 protocol buffer class as produced by the
      standard Google protobuf compiler.
  """
  # Parse message level options.
  message_options = protobuf.DESCRIPTOR.GetOptions()
  semantic_options = message_options.Extensions[semantic_pb2.semantic]

  # Support message descriptions
  if semantic_options.description and not cls.__doc__:
    cls.__doc__ = semantic_options.description

  cls.union_field = semantic_options.union_field or None

  # We search through all the field descriptors and build type info
  # descriptors from them.
  for field in protobuf.DESCRIPTOR.fields:
    type_descriptor = None

    # Does this field have semantic options?
    options = field.GetOptions().Extensions[semantic_pb2.sem_type]
    kwargs = dict(description=options.description,
                  name=field.name,
                  friendly_name=options.friendly_name,
                  field_number=field.number,
                  labels=list(options.label))

    if field.has_default_value:
      kwargs["default"] = field.default_value

    # This field is a non-protobuf semantic value.
    if options.type and field.type != TYPE_MESSAGE:

      rdf_type = getattr(rdfvalue, options.type, None)
      if rdf_type:
        # Make sure that the field type is the same as what is required by the
        # semantic type.
        required_field_type = _SEMANTIC_PRIMITIVE_TO_FIELD_TYPE[
            rdf_type.data_store_type]

        if required_field_type != field.type:
          raise rdfvalue.InitializeError((
              "%s: .proto file uses incorrect field to store Semantic Value "
              "%s: Should be %s") % (cls.__name__, field.name,
                                     rdf_type.data_store_type))

      type_descriptor = type_info.ProtoRDFValue(rdf_type=options.type, **kwargs)

    # A semantic protobuf is already a semantic value so it is an error to
    # specify it in two places.
    elif options.type and field.type == TYPE_MESSAGE:
      raise rdfvalue.InitializeError((
          "%s: .proto file specified both Semantic Value type %s and "
          "Semantic protobuf %s") % (cls.__name__, options.type,
                                     field.message_type.name))

    # Try to figure out what this field actually is from the descriptor.
    elif field.type == TYPE_DOUBLE:
      type_descriptor = type_info.ProtoDouble(**kwargs)

    elif field.type == TYPE_FLOAT:
      type_descriptor = type_info.ProtoFloat(**kwargs)

    elif field.type == TYPE_BOOL:
      type_descriptor = type_info.ProtoBoolean(**kwargs)

    elif field.type == TYPE_STRING:
      type_descriptor = type_info.ProtoString(**kwargs)

    elif field.type == TYPE_BYTES:
      type_descriptor = type_info.ProtoBinary(**kwargs)
      if options.dynamic_type:
        # This may be a dynamic type. In this case the dynamic_type option
        # names a method (which must exist) which should return the class of
        # the embedded semantic value.
        dynamic_cb = getattr(cls, options.dynamic_type, None)
        if dynamic_cb is not None:
          type_descriptor = type_info.ProtoDynamicEmbedded(
              dynamic_cb=dynamic_cb, **kwargs)
        else:
          logging.warning("Dynamic type specifies a non existant callback %s",
                          options.dynamic_type)

    elif (field.type == TYPE_MESSAGE and options.dynamic_type and
          field.message_type.name == "AnyValue"):
      dynamic_cb = getattr(cls, options.dynamic_type, None)
      if dynamic_cb is not None:
        type_descriptor = type_info.ProtoDynamicAnyValueEmbedded(
            dynamic_cb=dynamic_cb, **kwargs)
      else:
        logging.warning("Dynamic type specifies a non existant AnyValue "
                        "callback %s", options.dynamic_type)

    elif field.type == TYPE_INT64 or field.type == TYPE_INT32:
      type_descriptor = type_info.ProtoSignedInteger(**kwargs)

    elif field.type == TYPE_UINT32 or field.type == TYPE_UINT64:
      type_descriptor = type_info.ProtoUnsignedInteger(**kwargs)

    # An embedded protocol buffer.
    elif field.type == TYPE_MESSAGE and field.message_type:
      # Refer to another protobuf. Note that the target does not need to be
      # known at this time. It will be resolved using the late binding algorithm
      # when it is known. Therefore this can actually also refer to this current
      # protobuf (i.e. nested proto).
      type_descriptor = type_info.ProtoEmbedded(nested=field.message_type.name,
                                                **kwargs)

      # TODO(user): support late binding here.
      if type_descriptor.type:
        # This traps the following problem:
        # class Certificate(rdf_protodict.RDFValueArray):
        #    protobuf = jobs_pb2.BlobArray
        #

        # A primitive Protobuf definition like:
        # message Certificate {
        #   ....
        # };

        # And a field like:
        # optional Certificate csr = 1 [(sem_type) = {
        #   description: "A Certificate RDFValue with the CSR in it.",
        # }];

        # If we blindly allowed the Certificate RDFValue to be used, the
        # semantic library will end up embedding a BlobArray protobuf, but the
        # primitive library will still use Certificate.

        # The name of the primitive protobuf the semantic type implements.
        semantic_protobuf_primitive = type_descriptor.type.protobuf.__name__

        # This is an error because the primitive library will use the protobuf
        # named in the field, but the semantic library will implement a
        # different protobuf.
        if semantic_protobuf_primitive != field.message_type.name:
          raise rdfvalue.InitializeError(
              ("%s.%s: Conflicting primitive (%s) and semantic protobuf %s "
               "which implements primitive protobuf (%s)") %
              (cls.__name__, field.name, field.message_type.name,
               type_descriptor.type.__name__, semantic_protobuf_primitive))

    elif field.enum_type:  # It is an enum.
      enum_desc = field.enum_type
      enum_dict = {}
      enum_descriptions = {}
      enum_labels = {}

      for enum_value in enum_desc.values:
        enum_dict[enum_value.name] = enum_value.number
        description = enum_value.GetOptions().Extensions[
            semantic_pb2.description]
        enum_descriptions[enum_value.name] = description
        labels = [
            label
            for label in enum_value.GetOptions().Extensions[semantic_pb2.label]
        ]
        enum_labels[enum_value.name] = labels

      enum_dict = dict((x.name, x.number) for x in enum_desc.values)

      type_descriptor = type_info.ProtoEnum(enum_name=enum_desc.name,
                                            enum=enum_dict,
                                            enum_descriptions=enum_descriptions,
                                            enum_labels=enum_labels,
                                            **kwargs)

      # Attach the enum container to the class for easy reference:
      setattr(cls, enum_desc.name, type_descriptor.enum_container)

    # If we do not recognize the type descriptor we ignore this field.
    if type_descriptor is not None:
      # If the field is repeated, wrap it in a ProtoList.
      if field.label == LABEL_REPEATED:
        options = field.GetOptions().Extensions[semantic_pb2.sem_type]
        type_descriptor = type_info.ProtoList(type_descriptor,
                                              labels=list(options.label))

      try:
        cls.AddDescriptor(type_descriptor)
      except Exception:
        logging.error("Failed to parse protobuf %s", cls)
        raise

    else:
      logging.error("Unknown field type for %s - Ignoring.", field.name)

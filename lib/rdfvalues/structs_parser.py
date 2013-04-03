#!/usr/bin/env python
"""This is a parser which allows RDFStructs to be created from proto files."""




import re

from grr.lib import lexer
from grr.lib import rdfvalue
from grr.lib import type_info


class ProtoParser(lexer.Lexer):
  """A Parser for .proto files.

  Automatically creates and registers the classes found in the proto file.
  """
  tokens = [
      # Parse new message definition.
      lexer.Token("INITIAL",
                  r"message\s+([a-zA-Z0-9]+)\s+\{",
                  "DefineMessage,PushState",
                  "MESSAGE"),
      lexer.Token("MESSAGE", r"//\s*([^\n]+\n)", "AddComment", None),

      # Parse a field in the message.
      lexer.Token("MESSAGE", r"""
(?P<directive>required|repeated|optional)# directive for this field.
\s+
(?P<type>[a-zA-Z0-9]+)                   # The type of this field (e.g. uint64).
\s+
(?P<name>[a-zA-Z0-9]+)                   # The name of this field.
\s*=\s*
(?P<field>\d+)                           # The field number.
""", "AddField", "MESSAGE_OPTION", flags=re.VERBOSE | re.I),

      # No option specified - field complete.
      lexer.Token("MESSAGE_OPTION", ";", None, "MESSAGE"),

      # Parse field options (e.g. default value).
      lexer.Token("MESSAGE_OPTION", r"""
\[\s*
(?P<option>default)           # Option - currently only default supported.
\s*=\s*
(?P<data>[^\]]+)              # Data - this needs to be made more robust but
                              # simple for now
\]""", "AddFieldOption", None, flags=re.VERBOSE | re.I),

      # Message is complete.
      lexer.Token("MESSAGE", "}", "CompleteMessage,PopState", None),

      # Parsing ENUM definitions inside a message (enum definitions outside a
      # message are not supported).:
      lexer.Token("MESSAGE", r"""
enum\s+
(?P<enum_name>[a-zA-Z0-9]+)   # Name of the enum.
\s+
{""", "StartEnum,PushState", "ENUM", flags=re.VERBOSE | re.I),

      lexer.Token("ENUM", r"""
\s*
(?P<value_name>[a-zA-Z0-9]+)    # The name of the value.
\s*=\s*
(?P<value_int>[0-9]+)    # The integer value.
\s*;""", "EnumAddValue", None, flags=re.VERBOSE | re.I),
      lexer.Token("ENUM", "}", "PopState", None),

      # Ignore comments and whitespace.
      lexer.Token(None, r"//[^\n]+", None, None),
      lexer.Token(None, r"\s+", None, None),
      lexer.Token(None, r";", None, None),
      ]

  def __init__(self, data, parse_class=None):
    """Create a proto file parser.

    Args:
      data: The data of the proto file.

      parse_class: If specified, we only parse the proto message definition for
        this class. The parse_class parameter may be an actual class. In this
        case we only process the message matching the class's __name__
        attribute. If the parameter is a string, we only parse the message with
        that name, while ignoring all other messages in this file. If
        parse_class is not specified, we parse all message definitions, and
        create their respective classes.
    """
    super(ProtoParser, self).__init__(data)
    self.parse_class = parse_class

    # Hold a mapping between enums and their names.
    self._enum_map = {}
    self.type_infos = []
    self.field_comment = ""
    self.messages = []
    self._proto_type_map = {
        "string": type_info.ProtoString,
        "bytes": type_info.ProtoBinary,
        "uint64": type_info.ProtoUnsignedInteger,
        "uint32": type_info.ProtoUnsignedInteger,
        "int64": type_info.ProtoSignedInteger,
        "int32": type_info.ProtoSignedInteger,
        }

  def DefineMessage(self, match=None, **_):
    """Create a new message class."""
    name = match.group(1)

    # Create a new class for this message:
    if self.parse_class is None or self.parse_class == name:
      self.current_message_cls = type(name, (rdfvalue.RDFProtoStruct,), {})

    # The class is already provided, just use it.
    elif self.parse_class.__name__ == name:
      self.current_message_cls = self.parse_class

    # We need to skip this message.
    else:
      self.current_message_cls = None

  def AddComment(self, match=None, **_):
    self.field_comment += match.group(1)

  def AddField(self, match=None, **_):
    """Create the type info for the new added field."""
    # This message is ignored - ignore all its fields too.
    if self.current_message_cls is None:
      self.field_comment = ""
      return

    directive = match.group("directive")
    proto_type = match.group("type")
    field_args = dict(name=match.group("name"),
                      description=self.field_comment,
                      field_number=int(match.group("field")))

    if directive == "required":
      field_args["required"] = True

    field_type = self._proto_type_map.get(proto_type)
    if field_type is None:
      # It is either an enum or a nested group.
      if proto_type in self._enum_map:
        field_type = type_info.ProtoEnum
        field_args["enum_name"] = proto_type
        field_args["enum"] = self._enum_map[proto_type]
      else:
        # Assume its a nested group:
        field_type = type_info.ProtoNested
        field_args["nested"] = getattr(rdfvalue, proto_type)

    field = field_type(**field_args)

    if directive == "repeated":
      field = type_info.ProtoList(delegate=field)

    # Add the new field.
    self.type_infos.append(field)
    self.field_comment = ""

  def AddFieldOption(self, match=None, **_):
    """Adds a field option (like default)."""
    if self.current_message_cls is None:
      return

    option = match.group("option")
    if option != "default":
      return self.Error("Only default field options currently supported.")

    value = match.group("data")
    type_info_obj = self.type_infos[-1]
    if isinstance(type_info_obj, (type_info.ProtoUnsignedInteger,
                                  type_info.ProtoSignedInteger)):
      value = int(value)

    elif isinstance(type_info_obj, type_info.ProtoString):
      if not value[0] == "\"" or not value[-1] == "\"":
        return self.Error("String default must be quoted.")
      value = value[1:-1]
    else:
      return self.Error("Unable to set a default on field %s" %
                        type_info_obj.name)

    self.type_infos[-1].default = value

  def CompleteMessage(self, **_):
    # Complete the class by adding all the fields into it.
    if self.current_message_cls is not None:
      for type_info_obj in self.type_infos:
        self.current_message_cls.AddDescriptor(type_info_obj)

      # Keep track of the new messages we defined.
      self.messages.append(self.current_message_cls)

    self.type_infos = []
    self._enum_map = {}

  def StartEnum(self, match=None, **_):
    self.current_enum = match.group("enum_name")
    self._enum_map[self.current_enum] = {}

  def EnumAddValue(self, match=None, **_):
    enum_dict = self._enum_map[self.current_enum]
    enum_dict[match.group("value_name")] = int(match.group("value_int"))

  def Error(self, message=None, **_):
    """Parse errors are fatal."""
    raise lexer.ParseError(message)


def ParseFromProto(data, parse_class=None):
  """A factory for RDFProtoStruct classes from the .proto file."""
  parser = ProtoParser(data, parse_class=parse_class)
  parser.Close()

  return parser.messages

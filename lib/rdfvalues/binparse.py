from grr.lib import rdfvalue
from grr.lib import config_lib
from grr.proto import jobs_pb2
import pefile
import string
import magic
import re

class PEFunction(rdfvalue.RDFProtoStruct):
  """Represent a PE function for import/export"""
  protobuf = jobs_pb2.PEFunction

class PELibrary(rdfvalue.RDFProtoStruct):
  """Represent a PE library for import/export"""
  protobuf = jobs_pb2.PELibrary

class PEVersionInfo(rdfvalue.RDFProtoStruct):
  """Represent PE version info strings"""
  protobuf = jobs_pb2.PEVersionInfo

class PESection(rdfvalue.RDFProtoStruct):
  """Represent a PE Section entry"""
  protobuf = jobs_pb2.PESection

class PEResource(rdfvalue.RDFProtoStruct):
  """Represent a PE Resource entry"""
  protobuf = jobs_pb2.PEResource

class PEHeader(rdfvalue.RDFProtoStruct):
  """Represent a PE file header"""
  protobuf = jobs_pb2.PEHeader

  def ParseFromFile(self, path):
    try:
      pe = pefile.PE(path, fast_load=True)
      pe.parse_data_directories(directories=[
          pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT'],
          pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXPORT'],
          pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_TLS'],
          pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_RESOURCE']])
      self.ParseHeader(pe)
      pe.close()
    except (IOError, pefile.PEFormatError) as e:
      logging.info("Failed to parse PE %s. Err: %s", path, e)

  def ParseType(self, pe):
    #PE Type
    if pe.is_exe():
      pe_type = "EXE"
    elif pe.is_dll():
      pe_type = "DLL"
    elif pe.is_driver():
      pe_type = "Driver"
    else:
      pe_type = None
    self.type = pe_type

  def ParseSig(self, pe):
    #PE Signature
    address = pe.OPTIONAL_HEADER.DATA_DIRECTORY[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_SECURITY']].VirtualAddress
    size = pe.OPTIONAL_HEADER.DATA_DIRECTORY[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_SECURITY']].Size
    if address != 0:
      self.signature = pe.write()[address+8:address+size]

  def ParseExports(self, pe):
    #PE Exports
    if hasattr(pe, 'DIRECTORY_ENTRY_EXPORT'):
      if pe.DIRECTORY_ENTRY_EXPORT.struct.Name:
        self.exports.dll_name = pe.get_string_at_rva(pe.DIRECTORY_ENTRY_EXPORT.struct.Name)
        self.exports.count = len(pe.DIRECTORY_ENTRY_EXPORT.symbols)
      for export in pe.DIRECTORY_ENTRY_EXPORT.symbols:
        if export.address is not None:
          export_function = PEFunction()
          export_function.ordinal = export.ordinal
          export_function.name = export.name
          export_function.forwarder = str(export.forwarder)
          self.exports.functions.append(export_function)

  def ParseImports(self, pe):
    #PE Imports
    if hasattr(pe, 'DIRECTORY_ENTRY_IMPORT'):
      for library in pe.DIRECTORY_ENTRY_IMPORT:
        import_lib = PELibrary()
        import_lib.dll_name = library.dll
        import_lib.count = len(library.imports)
        for function in library.imports:
          import_function = PEFunction()
          import_function.ordinal = function.ordinal
          import_function.name = function.name
          import_lib.functions.append(import_function)
        self.imports.append(import_lib)

  def ParseVersionInfo(self, pe):
    #PE Version Info
    if hasattr(pe, 'FileInfo'):
      for entry in pe.FileInfo:
        if hasattr(entry, 'StringTable'):
          for st_entry in entry.StringTable:
            for str_entry in st_entry.entries.items():
              try:
                setattr(self.version_info, str_entry[0], str_entry[1])
              except AttributeError:
                pass

  def ParseResources(self, pe):
    #PE Resources
    if hasattr(pe, 'DIRECTORY_ENTRY_RESOURCE'):
      magic_file = config_lib.CONFIG.Get("Client.install_path") + "magic.mgc"
      mgc = magic.Magic(magic_file=magic_file)
      for entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        resource_type = entry.name
        if resource_type is None:
          resource_type = pefile.RESOURCE_TYPE.get(entry.struct.Id)
        if resource_type is None:
          resource_type = entry.struct.Id
        if hasattr(entry, 'directory'):
          for directory in entry.directory.entries:
            if hasattr(directory, 'directory'):
              for resource in directory.directory.entries:
                resource_entry = PEResource()
                resource_entry.name = str(resource_type)
                resource_entry.size = resource.data.struct.Size
                magic_type = mgc.from_buffer(pe.get_data(resource.data.struct.OffsetToData, resource.data.struct.Size))
                resource_entry.type = magic_type
                self.resources.append(resource_entry)

  def ParseSections(self, pe):
    #PE Sections
    for section in pe.sections:
      section_entry = PESection()
      section_entry.name = ''.join([c for c in section.Name if c in string.printable])
      section_entry.virt_addr = section.VirtualAddress
      section_entry.virt_size = section.Misc_VirtualSize
      section_entry.size = section.SizeOfRawData
      section_entry.entropy = section.get_entropy()
      self.sections.append(section_entry)

  def ParseAnomalies(self, pe):
    #Detected Anomalies
    if pe.OPTIONAL_HEADER.CheckSum == 0:
          self.anomalies.append("CHECKSUM_IS_ZERO")
    if pe.get_overlay_data_start_offset():
      self.anomalies.append("CONTAINS_EOF_DATA")
    for i in range(0, len(pe.sections) - 1):
      section_end = pe.sections[i].SizeOfRawData + pe.sections[i].PointerToRawData
      start_next_section = pe.sections[i+1].PointerToRawData
      if section_end != start_next_section:
        self.anomalies.append("BAD_SECTION_SIZE")
        break;
    for section in pe.sections:
      if not re.match("^[.A-Za-z][a-zA-Z]+", section.Name):
        self.anomalies.append("BAD_SECTION_NAME")
        break;

  def ParseHeader(self, pe):
      self.subsystem = pe.OPTIONAL_HEADER.Subsystem
      self.compile_time = pe.FILE_HEADER.TimeDateStamp
      self.ep = pe.OPTIONAL_HEADER.AddressOfEntryPoint
      if hasattr(pe, 'DIRECTORY_ENTRY_TLS'):
        self.tls = pe.DIRECTORY_ENTRY_TLS.struct.AddressOfCallBacks
      self.ParseType(pe)
      self.ParseSig(pe)
      self.ParseExports(pe)
      self.ParseImports(pe)
      self.ParseVersionInfo(pe)
      self.ParseResources(pe)
      self.ParseSections(pe)
      self.ParseAnomalies(pe)
      
      

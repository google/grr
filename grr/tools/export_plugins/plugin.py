#!/usr/bin/env python
"""Definition of grr_export plugin."""



import threading

import logging

from grr.lib import data_store
from grr.lib import export
from grr.lib import output_plugin as output_plugin_lib
from grr.lib import registry
from grr.lib import threadpool
from grr.lib import utils


class ExportPlugin(object):
  """Base class for grr_export.py plugins."""
  __metaclass__ = registry.MetaclassRegistry

  name = None

  def ConfigureArgParser(self, parser):
    pass

  def Run(self, args):
    raise NotImplementedError()


class OutputPluginBatchConverter(threadpool.BatchConverter):
  """BatchConverter that applies OutputPlugin to values.

  This class applies specific OutputPlugin to the given set of values
  using it in either multi-threaded or a single-threaded fashion. See
  BatchConverter implementation for details.

  Args:
      output_plugin: OutputPlugin that will be applied to the values.
      kwargs: Arguments that will be passed to threadpool.BatchConverter()
              constructor.
  """

  def __init__(self, output_plugin=None, **kwargs):
    """Constructor."""

    if not output_plugin:
      raise ValueError("output_plugin can't be None")
    self.output_plugin = output_plugin

    self.batches_count = 0
    self.lock = threading.RLock()

    super(OutputPluginBatchConverter, self).__init__(**kwargs)

  @utils.Synchronized
  def UpdateBatchCount(self):
    """Updates batches counter and prints a message."""

    self.batches_count += 1
    logging.info("Batch %d converted.", self.batches_count)

  def ConvertBatch(self, batch):
    """Converts batch of values using passed HuntOutputPlugin."""
    try:
      self.output_plugin.ProcessResponses(batch)
    except Exception as e:  # pylint: disable=broad-except
      logging.exception(e)

    self.UpdateBatchCount()


class OutputPluginBasedExportPlugin(ExportPlugin):
  """Base class for ExportPlugins that use OutputPlugins."""

  def _ConfigureArgParserForRdfValue(self, parser, value_class):
    """Configures arguments parser with fields of the rdf value class.

    This method scans given rdf value class and adds optional arguments to
    the given parser. Arguments names are equal to corresponding fields in
    the rdf value class. Arguments are only added if corresponding fields
    have simple underlying type. Fields that have other protobufs as
    underlying types are not added as arguments.

    Args:
      parser: argparse.ArgumentParser-compatible object.
      value_class: Class that inherits from RDFValue.
    """
    for type_descriptor in value_class.type_infos:
      if (not type_descriptor.hidden and type_descriptor.proto_type_name in
          ["string", "bool", "uint64", "float"]):
        kwargs = dict(help=type_descriptor.description,
                      default=type_descriptor.default,
                      required=type_descriptor.required)

        if type_descriptor.proto_type_name == "bool":
          kwargs["action"] = "store_true"
        else:
          kwargs["type"] = type_descriptor.type

        parser.add_argument("--" + type_descriptor.name, **kwargs)

  def _InitRdfValueFromParsedArgs(self, value_class, parsed_args):
    """Builds RDFValue of the given class from given arguments.

    This method is the reverse of the _ConfigureArgParserForRdfValue(). It
    constructs RDFValue instance and passes parsed arguments that correspond
    to the attributes of RDFValue that have corresponding primitive underlying
    primitive protobuf types.

    Args:
      value_class: Class of value to build. Should be inherited from RDFValue.
      parsed_args: argparser.Namespace-compatible object.

    Returns:
      RDFValue instance.
    """
    args = dict()
    for type_descriptor in value_class.type_infos:
      if (not type_descriptor.hidden and type_descriptor.name in parsed_args and
          type_descriptor.proto_type_name in ["string", "bool", "uint64",
                                              "float"]):
        args[type_descriptor.name] = getattr(parsed_args, type_descriptor.name)
    return value_class(**args)

  def _FindOutputPluginByName(self, plugin_name):
    """Finds output plugin with a given name."""
    for cls in output_plugin_lib.OutputPlugin.classes.itervalues():
      if cls.name == plugin_name:
        return cls

    raise KeyError(plugin_name)

  def _CreateOutputPluginFromArgs(self, collection_urn, args):
    """Creates OutputPlugin using given args as constructor arguments.

    If OutputPlugin args has "export_options" attribute, we add
    arguments corresponding to rdfvalue.ExportOptions.

    Args:
      collection_urn: Urn of the collection with the values to process.
      args: argparse.Namespace-compatible object with parsed command
            line arguments.
    Returns:
      OutputPlugin instance.
    """

    output_plugin_class = self._FindOutputPluginByName(args.plugin)
    if output_plugin_class.args_type:
      output_plugin_args = self._InitRdfValueFromParsedArgs(
          output_plugin_class.args_type, args)
      if hasattr(output_plugin_args, "export_options"):
        export_options = self._InitRdfValueFromParsedArgs(export.ExportOptions,
                                                          args)
        output_plugin_args.export_options = export_options
    else:
      output_plugin_args = None

    return output_plugin_class(source_urn=collection_urn,
                               args=output_plugin_args,
                               token=data_store.default_token)

  def _ProcessValuesWithOutputPlugin(self, values, output_plugin, args):
    """Processes given values with given output plugin."""

    checkpoints = utils.Grouper(values, args.checkpoint_every)
    for index, checkpoint in enumerate(checkpoints):
      logging.info("Starting checkpoint %d.", index)
      batch_converter = OutputPluginBatchConverter(batch_size=args.batch,
                                                   threadpool_size=args.threads,
                                                   output_plugin=output_plugin)
      batch_converter.Convert(checkpoint)

      logging.info("Checkpointing (checkpoint %d)...", index)
      output_plugin.Flush()
      logging.info("Checkpoint %d done.", index)

  def GetValuesSourceURN(self, args):
    """Returns URN describing where exported values are coming from."""
    _ = args
    raise NotImplementedError()

  def GetValuesForExport(self, args):
    """Returns values that should be processed with the OutputPlugin."""
    _ = args
    raise NotImplementedError()

  def ConfigureArgParser(self, parser):
    """Configures args parser based on plugin's args RDFValue."""

    self._ConfigureArgParserForRdfValue(parser, export.ExportOptions)

    subparsers = parser.add_subparsers(title="Output plugins")
    for cls in output_plugin_lib.OutputPlugin.classes.itervalues():
      if not cls.name:
        continue

      subparser = subparsers.add_parser(cls.name, help=cls.description)
      subparser.set_defaults(plugin=cls.name)

      if cls.args_type:
        self._ConfigureArgParserForRdfValue(subparser, cls.args_type)

  def Run(self, args):
    """Applies output plugin to the given collection."""

    output_plugin = self._CreateOutputPluginFromArgs(
        self.GetValuesSourceURN(args), args)
    logging.info("Initialized plugin '%s' with the state:", output_plugin.name)
    logging.info(utils.SmartUnicode(output_plugin.state))

    collection = self.GetValuesForExport(args)
    self._ProcessValuesWithOutputPlugin(collection, output_plugin, args)

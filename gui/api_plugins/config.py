#!/usr/bin/env python
"""API renderers for accessing config."""

from grr.gui import api_object_renderers
from grr.gui import api_renderers

from grr.lib import config_lib
from grr.lib import rdfvalue
from grr.lib import type_info
from grr.lib import utils


class ApiConfigRenderer(api_renderers.ApiRenderer):
  """Renders the configuration listing."""

  method = "GET"
  route = "/api/config"

  redacted_options = ["AdminUI.django_secret_key", "Mysql.database_password",
                      "Worker.smtp_password"]
  redacted_sections = ["PrivateKeys", "Users"]

  def _IsBadSection(self, section):
    for bad_section in self.redacted_sections:
      if section.lower().startswith(bad_section.lower()):
        return True

  def _ListParametersInSection(self, section):
    for descriptor in sorted(config_lib.CONFIG.type_infos,
                             key=lambda x: x.name):
      if descriptor.section == section:
        yield descriptor.name

  def Render(self, request):
    """Build the data structure representing the config."""

    sections = {}
    for descriptor in config_lib.CONFIG.type_infos:
      if descriptor.section in sections:
        continue

      is_bad_section = self._IsBadSection(descriptor.section)

      section_data = {}

      for parameter in self._ListParametersInSection(descriptor.section):
        try:
          if parameter in self.redacted_options or is_bad_section:
            is_default = False

            parameter_data = {"type": "redacted"}
          else:
            option_value = config_lib.CONFIG.Get(parameter, default=None)
            raw_value = config_lib.CONFIG.GetRaw(parameter, default=None)

            is_default = option_value is None or raw_value is None

            if is_default:
              option_value = config_lib.CONFIG.Get(parameter)
              raw_value = config_lib.CONFIG.GetRaw(parameter)

            value_type = "plain"

            if isinstance(option_value, rdfvalue.RDFValue):
              render_options = {"with_type_info": True,
                                "with_descriptors": True}
              option_value = api_object_renderers.RenderObject(option_value,
                                                               render_options)
            else:
              option_value = utils.SmartStr(option_value)

              # TODO(user): config_lib.CONFIG shouldn't return untyped
              # ByteStrings. It should wrap them into RDFBytes.
              # Problematic directive is:
              # %(%(ClientBuilder.source)/grr/gui/static/images/grr.ico|file)

              try:
                option_value = option_value.encode("utf8")
              except UnicodeError:
                raw_value = option_value = None
                value_type = "binary"

            parameter_data = {"raw_value": raw_value,
                              "option_value": option_value,
                              "is_default": is_default,
                              "type": value_type}

        except (config_lib.Error, type_info.TypeValueError) as e:
          parameter_data = {"type": "error",
                            "error_message": str(e)}

        section_data[parameter] = parameter_data

      sections[descriptor.section] = section_data

    return sections

#!/usr/bin/env python
"""This file sets up the django environment."""

import os


import django
from django.conf import settings

import logging
from grr.lib import config_lib
from grr.lib import registry


class DjangoInit(registry.InitHook):
  """Initialize the Django environment."""

  def RunOnce(self):
    """Configure the Django environment."""
    if django.VERSION[0] == 1 and django.VERSION[1] < 5:
      msg = ("The installed Django version is too old. We need 1.5+. You can "
             "install a new version with 'sudo easy_install Django'.")
      logging.error(msg)
      raise RuntimeError(msg)

    base_app_path = os.path.normpath(os.path.dirname(__file__))
    # Note that Django settings are immutable once set.
    django_settings = {
        "DEBUG": config_lib.CONFIG["AdminUI.django_debug"],
        "TEMPLATE_DEBUG": config_lib.CONFIG["AdminUI.django_debug"],
        "SECRET_KEY": config_lib.CONFIG["AdminUI.django_secret_key"],

        # Set to default as we don't supply an HTTPS server.
        # "CSRF_COOKIE_SECURE": not FLAGS.django_debug,  # Only send over HTTPS.
        # Where to find url mappings.
        "ROOT_URLCONF": "grr.gui.urls",
        "TEMPLATE_DIRS": ("%s/templates" % base_app_path,),
        # Don't use the database for sessions, use a file.
        "SESSION_ENGINE": "django.contrib.sessions.backends.file",
        "ALLOWED_HOSTS": config_lib.CONFIG["AdminUI.django_allowed_hosts"],
        "USE_I18N": False,
    }

    # The below will use conf/global_settings/py from Django, we need to
    # override every variable we need to set.
    settings.configure(**django_settings)

    try:
      # This is necessary for Django >= 1.7 but fails for 1.6 and below.
      django.setup()
    except AttributeError:
      pass

    if settings.SECRET_KEY == "CHANGE_ME":
      msg = "Please change the secret key in the settings module."
      logging.error(msg)


class GuiPluginsInit(registry.InitHook):
  """Initialize the GUI plugins once Django is initialized."""

  pre = ["DjangoInit"]

  def RunOnce(self):
    """Import the plugins once only."""
    # pylint: disable=unused-variable,g-import-not-at-top
    from grr.gui import gui_plugins
    # pylint: enable=unused-variable,g-import-not-at-top


def GetWSGIHandler():
  from django.core.handlers import wsgi  # pylint: disable=g-import-not-at-top
  return wsgi.WSGIHandler()

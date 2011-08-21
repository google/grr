#!/usr/bin/env python
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

try:
  from setuptools import setup
except ImportError:
  from distutils.core import setup

grr_files = ['__init__.py',
             'client/*.py',
             'client/version.txt',
             'client/client_actions/*.py',
             'client/client_actions/osx/*.py',
             'client/client_actions/windows/*.py',
             'client/vfs_handlers/*.py',
             'gui/*.py',
             'gui/plugins/*.py',
             'gui/static/css/*.css',
             'gui/static/css/smoothness/*.css',
             'gui/static/css/smoothness/images/*.png',
             'gui/static/images/*.gif',
             'gui/static/images/*.jpg',
             'gui/static/images/*.png',
             'gui/static/javascript/*.js',
             'gui/static/javascript/datatable/js/*.js',
             'gui/static/javascript/jquery/*.js',
             'gui/static/javascript/jquery_splitter/*.css',
             'gui/static/javascript/jquery_splitter/*.js',
             'gui/static/javascript/jquery_template/*.js',
             'gui/static/javascript/jquery_ui/*.js',
             'gui/static/javascript/jstree/*.js',
             'gui/static/javascript/jstree/themes/default/*.css',
             'gui/static/javascript/jstree/themes/default/*.js',
             'gui/static/javascript/jstree/themes/default/*.gif',
             'gui/static/javascript/jstree/themes/default/*.png',
             'gui/static/javascript/mbExtruder/elements/*.css',
             'gui/static/javascript/mbExtruder/elements/*.js',
             'gui/static/javascript/mbExtruder/elements/*.gif',
             'gui/static/javascript/mbExtruder/elements/*.MF',
             'gui/static/javascript/mbExtruder/elements/*.png',
             'gui/static/javascript/tooltip/*.js',
             'gui/templates/*.html',
             'lib/*.py',
             'lib/aff4_objects/*.py',
             'lib/flows/*.py',
             'lib/flows/caenroll/*.py',
             'lib/flows/console/*.py',
             'lib/flows/general/*.py',
             'parsers/*.py',
             'proto/*.py',
             'proto/*.proto',
             'tools/*.py',
             'worker/*.py',
            ]

setup(name='grr',
      version='0.1',
      description='GRR Rapid Response Framework',
      license='Apache License, Version 2.0',
      url='http://code.google.com/p/grr',
      install_requires=[],
      packages=['grr'],
      package_dir={'grr': '../grr'},
      package_data={'grr': grr_files},
     )

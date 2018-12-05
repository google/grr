#!/usr/bin/env python
"""Update the artifacts directory from upstream."""
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import fnmatch
import glob
import io
import os
import zipfile


from future.moves.urllib import request as urlrequest


def main():
  # We pin the artifact repo to a release to insulate us from breakage in HEAD.
  # The future direction is to depend on code in the artifact repo to replace
  # the artifact registry and validation inside GRR. We will then move to
  # depending on pypi releases rather than just importing the yaml as we do now.
  url = "https://github.com/ForensicArtifacts/artifacts/archive/20170814.zip"
  data = urlrequest.urlopen(url).read()

  zip_obj = zipfile.ZipFile(io.BytesIO(data))
  # Remove all existing yaml files.
  for filename in glob.glob("*.yaml"):
    os.unlink(filename)

  for name in zip_obj.namelist():
    if fnmatch.fnmatch(name, "*/data/*.yaml"):
      print("Extracting %s" % name)
      with open(os.path.basename(name), "wb") as fd:
        fd.write(zip_obj.open(name).read())


if __name__ == "__main__":
  main()

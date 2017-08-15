#!/usr/bin/env python
"""Update the artifacts directory from upstream."""
import fnmatch
import glob
import os
import StringIO
import urllib2
import zipfile


def main():
  # We pin the artifact repo to a release to insulate us from breakage in HEAD.
  # The future direction is to depend on code in the artifact repo to replace
  # the artifact registry and validation inside GRR. We will then move to
  # depending on pypi releases rather than just importing the yaml as we do now.
  url = "https://github.com/ForensicArtifacts/artifacts/archive/20170814.zip"
  data = urllib2.urlopen(url).read()

  zip_obj = zipfile.ZipFile(StringIO.StringIO(data))
  # Remove all existing yaml files.
  for filename in glob.glob("*.yaml"):
    os.unlink(filename)

  for name in zip_obj.namelist():
    if fnmatch.fnmatch(name, "*/data/*.yaml"):
      print "Extracting %s" % name
      with open(os.path.basename(name), "wb") as fd:
        fd.write(zip_obj.open(name).read())


if __name__ == "__main__":
  main()

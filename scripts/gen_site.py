#!/usr/bin/python2

"""
Generate the site.
"""
import argparse
import pdb
import os
import BaseHTTPServer
import SimpleHTTPServer
import traceback
import utils
import layout

PARSER = argparse.ArgumentParser()
PARSER.add_argument("path", default=".",
                    help="The path to the file to convert")

PARSER.add_argument("--serve", default=False, action="store_true",
                    help="When specified we serve the current directory.")

PARSER.add_argument("--port", default=8000, type=int,
                    help="HTTP Server port.")


def RenderPage(filename):
    metadata = utils.ParsePage(filename)
    if metadata is None:
        print "%s not valid template" % filename
        return

    renderer = getattr(layout, metadata.get("layout", "default"))
    result = renderer(metadata)

    with open("%s.html" % metadata["base_name"], "wb") as fd:
        fd.write(result.encode("utf8"))


def main(path="."):
    if os.path.isfile(path):
        print "Converting %s" % path
        return RenderPage(path)

    if not os.path.isdir(path):
        raise RuntimeError("Unknown path %s" % path)

    for root, dirs, files in os.walk(path, topdown=True):
        # Prune dirs with _
        excluded = utils.EXCLUDED_DIRECTORIES
        dirs[:] = [x for x in dirs
                   if not x.startswith("_") and x not in excluded]

        for name in files:
            path = os.path.join(root, name)
            extension = os.path.splitext(name)[1]
            if extension in utils.VALID_EXTENSIONS:
                print "Converting %s" % path
                RenderPage(path)


def Serve(port):
    server_address = ("127.0.0.1", port)
    httpd = BaseHTTPServer.HTTPServer(
        server_address, SimpleHTTPServer.SimpleHTTPRequestHandler)

    sa = httpd.socket.getsockname()
    print "Serving HTTP on", sa[0], "port", sa[1], "..."
    httpd.serve_forever()


if __name__ == "__main__":
    FLAGS = PARSER.parse_args()
    if FLAGS.serve:
        Serve(FLAGS.port)

    try:
        main(path=FLAGS.path)
    except Exception:
        traceback.print_exc()

        pdb.post_mortem()

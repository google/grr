import collections
import functools
import logging
import markdown
import os
import re
import subprocess
import yaml

def dict_constructor(loader, node):
    return collections.OrderedDict(loader.construct_pairs(node))

yaml.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
                     dict_constructor)

SEPERATOR = "\n---\n"
MARKDOWN_EXTENSIONS = [".md", ".markdown"]
MD_EXTENSIONS = [
    'fenced_code',
    'codehilite(css_class=highlight)',
    'smarty',
    'tables',
    'sane_lists',
    'wikilinks(end_url=.html)',
    ]

ASCIIDOC_EXTENSIONS = [".txt", ".adoc"]
ASCIIDOC_CMD = ("asciidoc -a icons -a linkcss "
                "-a stylesdir=/css -a data-uri "
                "".split())

VALID_EXTENSIONS = ASCIIDOC_EXTENSIONS + MARKDOWN_EXTENSIONS
EXCLUDED_DIRECTORIES = ["img", "blogg_posts"]


class Page(dict):
    def __getattr__(self, attr):
        return self.get(attr, "")

    def __setattr__(self, attr, value):
        if hasattr(self.__class__, attr) or attr in self.__dict__:
            super(Page, self).__setattr__(attr, value)
        else:
            self[attr] = value

    def CheckContentCache(self):
        cache_path = os.path.abspath("./_cache/%s" % self.filename.replace(
            "/", "_"))

        try:
            # Only return the cache it is it newer than the original file.
            if os.stat(cache_path).st_mtime > os.stat(self.filename).st_mtime:
                return open(cache_path).read().decode("utf8", "ignore")
        except (OSError, IOError):
            pass

        # Recalculate the cache.
        content = self._parse_content()
        with open(cache_path, "wb") as fd:
            fd.write(content.encode("utf8"))

        return content

    def _parse_content(self):
        content = self.raw_content

        if self.extension in MARKDOWN_EXTENSIONS:
            return ConvertFromMD(content)

        elif self.extension in ASCIIDOC_EXTENSIONS:
            return ConvertFromAsciiDoc(content)

        else:
            return content

    @property
    def content(self):
        if self.parsed_content:
            return self.parsed_content

        self.parsed_content = self.CheckContentCache()

        return self.parsed_content

    @content.setter
    def content(self, value):
        self.parsed_content = value


def GetInclude(filename):
    return open(filename).read()

def ConvertFromMD(text):
    """Convert the data from markdown to html."""
    return markdown.markdown(text, extensions=MD_EXTENSIONS)


def ConvertFromAsciiDoc(text):
    cmd = ASCIIDOC_CMD[:] + [
        "-a", "iconsdir=%s/img/icons" % os.getcwd(),
        "-a", "imagesdir=%s" % os.getcwd(),
        "-"]
    print cmd
    pipe = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE)

    stdoutdata, _ = pipe.communicate(text.encode("utf8"))

    m = re.search("<body[^>]*>(.+)</body", stdoutdata, re.S|re.M)
    result = m.group(1).decode("utf8", "ignore")
    result += '<script src="/js/asciidoc.js"></script>'
    return result


def GetUrlFromFilename(filename):
    return os.path.abspath(filename)[len(os.getcwd()):]


def ParsePage(filename):
    """Read a page and return its metadata blob."""
    filename = os.path.abspath(filename)
    base_name, extension = os.path.splitext(filename)
    if extension not in VALID_EXTENSIONS:
        return None

    try:
        text = open(filename).read().decode("utf8", "ignore").lstrip()
    except (OSError, IOError):
        return None

    match = re.match("^---(.*?)\n---\n(.*)", text, re.S | re.M)
    if match:
        try:
            metadata = Page(yaml.load(match.group(1)) or {})
        except ValueError:
            logging.warning("Invalid page %s" % filename)
            return None

        metadata.raw_content = match.group(2)
    else:
        metadata = Page({})
        metadata.raw_content = text

    metadata.extension = extension
    metadata.filename = filename
    metadata.base_name = base_name
    metadata.url = GetUrlFromFilename(base_name) + ".html"
    metadata.type = "file"

    return metadata


def ListPages(path):
    """A generator for page metadata from path."""
    # The path can be provided as an absolute, or relative to the document root.
    if not path.startswith(os.getcwd()):
        path = os.path.abspath("%s/%s" % (os.getcwd(), path))

    for filename in sorted(os.listdir(path)):
        full_path = os.path.abspath("%s/%s" % (path, filename))

        if os.path.isdir(full_path):
            yield Page(filename=full_path, type="directory",
                       url=GetUrlFromFilename(filename))

        else:
            page = ParsePage(full_path)
            if page is not None:
                yield page


def memoize(obj):
    cache = obj.cache = {}

    @functools.wraps(obj)
    def memoizer(*args, **kwargs):
        key = str(args) + str(kwargs)
        if key not in cache:
            cache[key] = obj(*args, **kwargs)
        return cache[key]
    return memoizer

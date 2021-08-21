#!/usr/bin/env python3
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: WTFPL
# SPDX-FileCopyrightText: 2021 Anna <cyber@sysrq.in>
# No warranty.

import mimetypes
import os
import random
import sys
import tarfile
import urllib.parse

from collections import OrderedDict
from datetime import date
from fnmatch import fnmatch
from functools import cached_property
from pathlib import Path


class Redirect(Exception):
    def __init__(self, url: str):
        super().__init__()
        self.url: str = url


class Failure(RuntimeError):
    pass


class CGIError(RuntimeError):
    pass


class PermanentFailure(RuntimeError):
    pass


class NotFound(RuntimeError):
    pass


def is_enabled(directory: Path) -> bool:
    registry = directory.parent / "registry"
    for line in registry.open():
        line = line.strip()
        if line.startswith("#") or not line:
            continue
        if directory.name == line.split()[-1]:
            return True

    return False


def display_file(path: Path, format_str="{0}", fallback=None) -> None:
    if not path.is_file() or not os.access(path, os.R_OK):
        if fallback is not None:
            print(format_str.format(fallback), end="\n\n")
        return

    print(format_str.format(path.read_text().rstrip()), end="\n\n")


def display_lang(dirname: str) -> None:
    lang_glob = tuple(dirname.glob("lang_*"))
    if not lang_glob:
        return

    lang_short = lang_glob[0].name.split("lang_", maxsplit=1)[-1]
    lang_desc = app.lang_desc.get(lang_short, lang_short)
    print("> Written in", lang_desc, end="\n\n")


def display_features(dirname: str) -> None:
    features = (file.name.split("feature_")[-1]
                for file in dirname.glob("feature_*"))

    did_header = False
    # iterate over app.features_desc to keep desired order
    for feature_short, feature_desc in app.features_desc.items():
        if feature_short in features:
            if not did_header:
                print("Features:")
            print("*", feature_desc)
            did_header = True

    if did_header:
        print()


def display_server_page(directory: Path) -> None:
    if not is_enabled(directory):
        raise Failure("Server info came from a non-authorized source")

    print("20 text/gemini\r")
    print("# Gemini Server of the Day is ...")

    display_file(directory / "logo", format_str="```ASCII Art\n{0}\n```")
    display_file(directory / "name", format_str="## {0}",
                 fallback=directory.name)
    display_lang(directory)
    display_file(directory / "description")
    display_file(directory / "homepage", format_str="🏠 Homepage:\n=> {0}")
    display_features(directory)
    display_file(directory / "repology",
                 format_str="=> {0} 📦 Repology: packaging status")

    print("--", end="\n\n")
    print("=> random 🔀 Random server")
    print("=> info/README.gmi ℹ️ About this thing")


class CGIHandler:
    """ Syntax sugar """
    def __init__(self):
        self.routes = OrderedDict()

    @cached_property
    def path(self) -> str:
        path_info = os.getenv("PATH_INFO", default="/")
        return urllib.parse.unquote(path_info) or "/"

    @cached_property
    def script_name(self) -> str:
        return os.getenv("SCRIPT_NAME", default="")

    @cached_property
    def dataroot(self) -> Path:
        dataroot_env = os.getenv("SOTD_DATAROOT")
        if dataroot_env:
            dataroot = Path(dataroot).expanduser()
        else:
            dataroot = Path.cwd().parent / "info"

        if not dataroot.is_dir():
            raise CGIError("Invalid SOTD_DATAROOT")

        return dataroot

    @cached_property
    def features_desc(self) -> OrderedDict[str, str]:
        return self._parse_keyvals("features.desc")

    @cached_property
    def lang_desc(self) -> OrderedDict[str, str]:
        return self._parse_keyvals("lang.desc")

    def route(self, glob: str):
        def decorator(f):
            self.routes[glob] = f
            return f

        return decorator

    def exec(self) -> None:
        for glob, view_function in self.routes.items():
            if fnmatch(self.path, glob):
                return view_function()

        raise NotFound("UFO landed and left these words here")

    def _parse_keyvals(self, filename: str) -> OrderedDict[str, str]:
        d = OrderedDict()
        path = self.dataroot / filename
        for line in path.open():
            line = line.strip()
            if line.startswith("#") or not line:
                continue

            key, *val = line.split(maxsplit=1)
            if not val:
                val = [key.capitalize()]
            d[key] = val[0]

        return d


app = CGIHandler()

@app.route("/server_info.tar.gz")
def sotd_dump() -> None:
    """ Generate a tarball from all info directories (excluding registry) """
    def info_filter(tarinfo: tarfile.TarInfo):
        if tarinfo.name == "registry":
            return None

        if tarinfo.isfile():
            tarinfo.mode = 0o0644
        elif tarinfo.isdir():
            tarinfo.mode = 0o0755

        tarinfo.uid = tarinfo.gid = 0
        tarinfo.uname = tarinfo.gname = "gemini"
        return tarinfo

    print("20 application/x-gtar\r")
    sys.stdout.flush()
    with tarfile.open(fileobj=sys.stdout.buffer, mode="w|gz") as tar:
        tar.add(app.dataroot, arcname="", filter=info_filter)

@app.route("/random")
def sotd_random() -> None:
    """ Page that changes on every requst """
    directory = random.choice([x for x in app.dataroot.iterdir() if x.is_dir()])
    display_server_page(directory)

@app.route("/")
def sotd() -> None:
    """ Page that changes once a day """
    # a bit of personalization C:
    favorite_number = float(os.getenv("FAVORITE_NUMBER", default="0"))
    random.seed(date.today().toordinal() + favorite_number)
    sotd_random()

@app.route("/robots.txt")
def sotd_robots() -> None:
    print("20 text/plain\r")
    print("User-agent: indexer")
    print(f"Disallow: {app.script_name}/info")
    print(f"Disallow: {app.script_name}/server_info.tar.gz")

@app.route("/info/registry")
def sotd_registry() -> None:
    """ Should be kept private (contains email addresses) """
    raise PermanentFailure("Access denied")

@app.route("/info")
@app.route("/info/*")
def sotd_info() -> None:
    """ Serve info files """
    path = app.dataroot / Path(app.path).relative_to("/info")
    if not path.exists():
        raise NotFound("No such file or directory")
    if not path.is_relative_to(app.dataroot):
        raise PermanentFailure("Access denied")

    if path.is_file():
        mimetypes.add_type("text/gemini", ".gmi")
        mimetypes.add_type("text/gemini", ".gemini")
        print("20", mimetypes.guess_type(path, strict=False)[0] or "text/plain",
              end="\r\n")
        print(path.read_text())
    elif path.is_dir():
        if not app.path.endswith("/"):
            raise Redirect(app.path + "/")

        print("20 text/gemini\r")
        print("# Index of", app.path, end="\n\n")
        print("=> ..")
        for item in path.iterdir():
            print("=>", item.name, end="/\n" if item.is_dir() else "\n")
    else:
        raise Failure("Cannot display a file")

if __name__ == "__main__":
    try:
        app.exec()
    except Redirect as redirect:
        print(31, app.script_name + redirect.url, end="\r\n")
    except Failure as err:
        print(40, *err.args, end="\r\n")
    except CGIError as err:
        print(42, *err.args, end="\r\n")
    except PermanentFailure as err:
        print(50, *err.args, end="\r\n")
    except NotFound as err:
        print(51, *err.args, "\r\n")
    except (OSError, RuntimeError, SystemError) as err:
        raise CGIError("Internal server error") from err

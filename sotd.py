#!/usr/bin/env python3
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: WTFPL
# SPDX-FileCopyrightText: 2021 Anna <cyber@sysrq.in>
# No warranty.

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
from typing import NoReturn


def notfound(msg="Not found!") -> NoReturn:
    print(f"51 {msg}\r")
    sys.exit(0)


def cgi_error(msg="CGI Error") -> NoReturn:
    print(f"42 {msg}\r")
    sys.exit(0)


def failure(msg="Temporary failure!") -> NoReturn:
    print(f"40 {msg}\r")
    sys.exit(0)


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

    print(format_str.format(path.read_text().strip()), end="\n\n")


def display_server_page(directory: Path) -> None:
    if not is_enabled(directory):
        failure("Untrusted server info")

    print("20 text/gemini\r")
    print("# Gemini Server of the Day is ...")

    display_file(directory / "logo", format_str="```ASCII Art\n{0}\n```")
    display_file(directory / "name", format_str="## {0}",
                 fallback=directory.name)
    display_file(directory / "description")
    display_file(directory / "homepage", format_str="🏠 Homepage:\n=> {0}")
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
    def dataroot(self) -> Path:
        dataroot_env = os.getenv("SOTD_DATAROOT")
        if dataroot_env:
            dataroot = Path(dataroot).expanduser()
        else:
            dataroot = Path.cwd().parent / "info"

        if not dataroot.is_dir():
            cgi_error("Invalid SOTD_DATAROOT")

        return dataroot

    def route(self, glob: str):
        def decorator(f):
            self.routes[glob] = f
            return f

        return decorator

    def exec(self) -> None:
        for glob, view_function in self.routes.items():
            if fnmatch(self.path, glob):
                return view_function()

        notfound("Here be aliens...")


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

if __name__ == "__main__":
    app.exec()

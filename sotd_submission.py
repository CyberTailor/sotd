#!/usr/bin/env python3
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: WTFPL
# SPDX-FileCopyrightText: 2021 Anna <cyber@sysrq.in>
# No warranty.

import os
import sys
import time

from dataclasses import dataclass, field
from pathlib import Path


class AuthorizationFailed(RuntimeError):
    pass


class BadInput(RuntimeError):
    pass


@dataclass(frozen=True)
class RegistryEntry:
    email_glob: str
    name: str
    enabled: bool = field(compare=False, default=False)

    def __str__(self) -> str:
        pre = "" if self.enabled else "#"
        return f"{pre}{self.email_glob}\t{self.name}"


class GmiLogger:
    """ text/gemini public log writer """

    def __init__(self, path: Path):
        self.log: list[str] = ["### " + time.asctime(time.gmtime())]
        self.path: Path = path
        self.path.touch()

        self._finished: bool = False

    def print(self, *args: object) -> None:
        """ Log a text line """
        self.log.append(" ".join(map(str, args)))

    def finish(self, *log_msg: object) -> None:
        """
        Prepend new entry to the log file.
        Final log message will be displayed as a quote line.
        """
        if self._finished:
            raise RuntimeError("GmiLogger.finish() called twice")

        self.print(">", *log_msg, "\n")
        with open(self.path) as log_file:
            self.log.extend(list(map(str.strip, log_file.readlines())))
        with open(self.path, "w") as log_file:
            for line in self.log:
                print(line, file=log_file)

        self._finished = True


dataroot = Path(os.getenv("SOTD_DATAROOT", default="/var/gemini/sotd/info"))
if len(sys.argv) > 1:
    dataroot = Path(sys.argv[1])

logger = GmiLogger(dataroot / "log.gmi")

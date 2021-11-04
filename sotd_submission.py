#!/usr/bin/env python3
# SPDX-FileType: SOURCE
# SPDX-License-Identifier: WTFPL
# SPDX-FileCopyrightText: 2021 Anna <cyber@sysrq.in>
# No warranty.

from dataclasses import dataclass, field


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

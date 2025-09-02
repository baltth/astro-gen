#!/usr/bin/env python3

from dataclasses import dataclass, field
from typing import List


@dataclass
class FetchedData:
    name: str = ''
    ra: str = ''
    decl: str = ''
    constellation: str = ''
    type: str = ''
    subtype: str = ''
    spectral_class: str = ''
    alias: List[str] = field(default_factory=list)

#!/usr/bin/env python3

from dataclasses import dataclass, field, fields
from typing import Any, Dict, List, Type


@dataclass
class SketchData:
    full: str = ''
    scan: str = ''
    sub: List[str] = field(default_factory=list)
    notes: str = ''


@dataclass
class ObsData:
    names: List[str] = field(default_factory=list)
    img: str = ''
    date: str = ''
    loc: str = ''
    nelm: float = 0
    seeing: int = 0
    ap: int = 0
    mag: int = 0
    fov: str = ''
    text: str = ''
    data: Dict[str, str] = field(default_factory=dict)


@dataclass
class ObjectBase:
    name: str = ''
    ra: str = ''
    decl: str = ''
    constellation: str = ''
    type: str = ''


@dataclass
class ObjectData(ObjectBase):
    desc: str = ''
    aka: List[str] = field(default_factory=list)
    data: Dict[str, str] = field(default_factory=dict)


@dataclass
class FetchedData(ObjectBase):
    subtype: str = ''
    spectral_class: str = ''
    alias: List[str] = field(default_factory=list)


def create(cls: Type, d: Dict) -> Any:
    KEYS = [f.name for f in fields(cls)]
    filt = {k: v for k, v in d.items() if k in KEYS}
    return cls(**filt)


DATA_NOTE = '\u2020'    # 'dagger': †

#!/usr/bin/env python3

from copy import deepcopy
from dataclasses import dataclass, field, fields, asdict
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
    constellation: str = ''
    type: str = ''


@dataclass
class FetchedData(ObjectBase):
    subtype: str = ''
    ra: str = ''
    dec: str = ''
    spectral_class: str = ''
    alias: List[str] = field(default_factory=list)
    data: Dict[str, str] = field(default_factory=dict)


@dataclass
class ObjectData(ObjectBase):
    desc: str = ''
    aka: List[str] = field(default_factory=list)
    data: Dict[str, str] = field(default_factory=dict)
    components: Dict[str, FetchedData] = field(default_factory=dict)
    fetched: Dict[str, FetchedData] = field(default_factory=dict)


def create(cls: Type, d: Dict) -> Any:
    KEYS = [f.name for f in fields(cls)]
    filt = {k: v for k, v in d.items() if k in KEYS}
    return cls(**filt)


DATA_NOTE = '\u2020'    # 'dagger': †


def get_all_data_of(obj: ObjectData) -> Dict[str, Dict[str, str]]:

    def flat_data(o: ObjectData) -> Dict:
        d = asdict(o)
        if 'data' in d.keys():
            if isinstance(d['data'], dict):
                d.update(d['data'])
                del d['data']
            else:
                assert False
        return d

    added_fetched = set()
    components = deepcopy(obj.components)
    res: Dict[str, Dict[str, str]] = {}
    for c_key, c in components.items():

        c_dict = {k: str(v) for k, v in flat_data(c).items()}
        c_dict['fetched_keys'] = []
        if c.name in obj.fetched.keys():
            added_fetched.add(c.name)
            f_dict = flat_data(obj.fetched[c.name])
            for k, v in f_dict.items():
                if v and not c_dict.get(k, ''):
                    c_dict[k] = str(v)
                    c_dict['fetched_keys'].append(k)
        res[c_key] = c_dict

    for f_key, f in obj.fetched.items():
        if f_key not in added_fetched:
            res[f_key] = {k: str(v) for k, v in flat_data(f).items()}
            res[f_key]['fetched_keys'] = list(flat_data(f).keys())

    for d in res.values():
        if 'alias' in d.keys():
            del d['alias']
        if 'alias' in d['fetched_keys']:
            d['fetched_keys'].remove('alias')

    if obj.data:
        res['_'] = deepcopy(obj.data)

    return res

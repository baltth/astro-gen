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
class ObjectData:
    name: str = ''
    constellation: str = ''
    type: str = ''
    subtype: str = ''
    desc: str = ''
    ra: str = ''
    dec: str = ''
    mag: str = ''
    spectral_class: str = ''
    aka: List[str] = field(default_factory=list)
    data: Dict[str, str] = field(default_factory=dict)


@dataclass
class Object(ObjectData):
    components: Dict[str, ObjectData] = field(default_factory=dict)
    fetched: Dict[str, ObjectData] = field(default_factory=dict)


def create(cls: Type, d: Dict) -> Any:
    KEYS = [f.name for f in fields(cls)]
    filt = {k: v for k, v in d.items() if k in KEYS}
    return cls(**filt)


def get_all_data_of(obj: Object) -> Dict[str, Dict[str, str]]:
    """
    Create a collection of the component data and fetched data
    with combining associated data sets.    
    """

    def flat_data(o: ObjectData) -> Dict:
        """
        ObjectData as dictionary with
        - 'data' moved to root
        - 'aka' list removed
        - all fields as string
        """
        d = asdict(o)
        if 'data' in d.keys():
            d.update(d['data'])
            del d['data']
        if 'aka' in d.keys():
            del d['aka']
        return {k: str(v) for k, v in d.items()}

    added_fetched = set()
    components = deepcopy(obj.components)

    res: Dict[str, Dict[str, str]] = {}

    # Collect data from the main object
    OD_FIELDS = [f.name for f in fields(ObjectData)]
    OBJ_FIELDS = [f.name for f in fields(Object)]
    main_obj = {k: v for k, v in flat_data(obj).items() if k in OD_FIELDS or k not in OBJ_FIELDS}

    # For all components: collect with associated fetched data merged
    for c_key, c in components.items():

        # create data set
        c_dict = flat_data(c)
        c_dict['fetched_keys'] = []

        # merge associated fetched data on demand
        if c.name in obj.fetched.keys():

            added_fetched.add(c.name)
            f_dict = flat_data(obj.fetched[c.name])

            # merge fetched to component
            for k, v in f_dict.items():
                if v and not c_dict.get(k, ''):
                    c_dict[k] = v
                    # register new keys from fetched
                    c_dict['fetched_keys'].append(k)

        # Store the component data
        res[c_key] = c_dict

    # For the remaining unused fetched data:
    for f_key, f in obj.fetched.items():
        if f_key not in added_fetched:
            # Store fetched data
            f_dict = flat_data(f)

            # register keys fof fetched
            f_dict['fetched_keys'] = list(f_dict.keys())
            res[f_key] = f_dict

    if main_obj:
        res['_'] = main_obj

    return res

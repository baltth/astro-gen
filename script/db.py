#!/usr/bin/env python3

import common
import project
from datatypes import ObsData, Object, ObjectData, SketchData, create

from copy import deepcopy
from dataclasses import asdict
from natsort import natsorted
from pathlib import Path
from ruamel.yaml import YAML, comments
from typing import Callable, Dict, List

# As db files are also edited manually, we're using
# ruamel.yaml to be able to round-trip edit
# files to preserve comments, empty lines etc.

YamlDict = comments.CommentedMap
YamlList = comments.CommentedSeq


def load(db: str) -> YamlDict:

    print(f'Loading {db} ...')

    yaml = YAML()
    data = yaml.load(Path(db))
    assert isinstance(data, YamlDict)
    return data


def sketches_raw(root: str) -> List[Dict]:

    sketch_db = load(project.sketch_db(root))
    return list(sketch_db['sketches'])


def sketches(root: str) -> List[SketchData]:

    raw = sketches_raw(root)
    return [create(SketchData, d) for d in raw]


def observations_raw(root: str) -> List[Dict]:

    obs_db = load(project.obs_db(root))
    return list(obs_db['observations'])


def observations(root: str) -> List[ObsData]:

    raw = observations_raw(root)
    for r in raw:
        if isinstance(r['name'], str):
            r['names'] = [r['name']]
        else:
            r['names'] = r['name']
        del r['name']
        if 'fov' in r.keys():
            r['fov'] = str(r['fov'])
    return [create(ObsData, d) for d in raw]


def objects_raw(root: str) -> Dict[str, Dict]:

    obj_db = load(project.object_db(root))
    return dict(obj_db['objects'])


def objects(root: str) -> Dict[str, Object]:

    def _map_of_obj_data(src: Dict[str, Dict]) -> Dict[str, ObjectData]:
        res = {}
        for k, v in src.items():
            d: ObjectData = create(ObjectData, v)
            if not d.name:
                d.name = k
            res[k] = d
        return res

    raw = objects_raw(root)
    for k, v in raw.items():
        v['name'] = k
        if 'components' in v.keys():
            v['components'] = _map_of_obj_data(v['components'])
        if 'fetched' in v.keys():
            v['fetched'] = _map_of_obj_data(v['fetched'])

    return {k: create(Object, v) for k, v in raw.items()}


def save(db: str, data: Dict):

    print(f'Saving {db} ...')

    yaml = YAML()
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 160
    yaml.dump(data=data,
              stream=Path(db))


def update_in_list(l: YamlList, entry: Dict, key_match: Callable) -> bool:
    for e in l:
        if key_match(e, entry):
            e.update(**entry)
            return True
    return False


def add_to_list(l: YamlList, entry: Dict):
    l.append(entry)
    l.yaml_set_comment_before_after_key(len(l) - 1, before='')


def add_sketch(root: str,
               full: str,
               scan: str = '',
               sub: List[str] = [],
               cmd: List[str] = []):

    entry = {}
    entry['full'] = full
    if scan:
        entry['scan'] = scan
    if sub:
        entry['sub'] = sub
    if cmd:
        entry['_cmd'] = cmd

    sdb = load(project.sketch_db(root))
    sk_list: YamlList[YamlDict] = sdb['sketches']

    updated = update_in_list(sk_list, entry, lambda x, y: x['full'] == y['full'])
    if not updated:
        add_to_list(sk_list, entry)

    save(project.sketch_db(root), sdb)


def add_obs(root: str,
            name: str,
            date: str):

    names = common.names_to_list(name)
    entry_name = names if len(names) > 1 else name

    date_in_file = date.replace('-', '')
    img = common.sketch_name(entry_name, date_in_file)

    odb = load(project.obs_db(root))
    obs_list: YamlList[YamlDict] = odb['observations']

    if any(o['name'] == entry_name and o['img'] == img for o in obs_list):
        print(f'Skipping {entry_name} / {img}, already present')
        return

    entry = {
        'name': entry_name,
        'img': common.sketch_name(entry_name, date_in_file),
        'date': date,
        'loc': '',
        'nelm': 0,
        'seeing': 0,
        'ap': 0,
        'mag': 0,
        'fov': 0,
        'text': ''
    }

    add_to_list(obs_list, entry)
    save(project.obs_db(root), odb)


def _refresh_with_fetched(entry: Dict, fetched: ObjectData) -> Dict:

    e = deepcopy(entry)
    if not e['constellation']:
        e['constellation'] = fetched.constellation
    if not e['type']:
        e['type'] = fetched.type.lower()

    f_dict = asdict(fetched)
    keys_to_del = ['constellation', 'data']
    if not fetched.desc:
        keys_to_del.append('decs')
    if not fetched.spectral_class:
        keys_to_del.append('spectral_class')
    if not fetched.mag:
        keys_to_del.append('mag')

    f_dict = {k: v for k, v in f_dict.items() if k not in keys_to_del}
    if 'fetched' not in e.keys():
        e['fetched'] = {}
    e['fetched'][fetched.name] = f_dict

    return e


def add_object(obj_dict: YamlDict,
               name: str,
               fetched: ObjectData,
               refresh: bool = False) -> bool:

    def new_entry() -> Dict:
        return {
            'constellation': common.get_constellation(name),
            'type': ''
        }

    print(f'Adding {name} ...')

    db_names = list(obj_dict.keys())
    if name in db_names:
        if refresh:
            entry = obj_dict[name]
            del obj_dict[name]
            db_names.remove(name)
        else:
            print(f'Skipping {name}, already present')
            return False
    else:
        entry = new_entry()

    db_names.append(name)
    db_names = natsorted(db_names)
    pos = db_names.index(name)

    fetched_valid = bool(fetched.name)
    if fetched_valid:
        entry = _refresh_with_fetched(entry, fetched)

    obj_dict.insert(pos, name, entry)
    if pos < (len(obj_dict) - 1):
        obj_dict.yaml_set_comment_before_after_key(db_names[pos + 1], before='')

    return True


def add_objects(root: str,
                name: str,
                fetched: Dict[str, ObjectData] = {},
                refresh: bool = False):

    odb = load(project.object_db(root))
    obj_dict: YamlDict = odb['objects']

    names = name.replace(', ', ',').split(',')
    added = False
    for n in names:
        f = fetched.get(n, ObjectData())
        added = add_object(obj_dict, n, f, refresh=refresh) or added

    if added:
        save(project.object_db(root), odb)

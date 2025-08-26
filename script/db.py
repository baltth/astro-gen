#!/usr/bin/env python3

import common
import project

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


def sketches(root: str) -> List:

    sketch_db = load(project.sketch_db(root))
    return list(sketch_db['sketches'])


def observations(root: str) -> List:

    obs_db = load(project.obs_db(root))
    return list(obs_db['observations'])


def objects(root: str) -> Dict:

    obj_db = load(project.object_db(root))
    return dict(obj_db['objects'])


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

    names = name.replace(', ', ',').split(',')
    entry_name = names if len(names) > 1 else name

    date_in_file = date.replace('-', '')

    entry = {
        'name': entry_name,
        'date': date,
        'img': common.sketch_name(entry_name, date_in_file)
    }

    odb = load(project.obs_db(root))
    obs_list: YamlList[YamlDict] = odb['observations']

    updated = update_in_list(obs_list,
                             entry,
                             lambda x, y: x['name'] == y['name'] and x['img'] == y['img'])
    if not updated:
        entry.update({
            'loc': '',
            'nelm': 0,
            'seeing': 0,
            'ap': 0,
            'mag': 0,
            'fov': 0,
            'text': ''
        })
        add_to_list(obs_list, entry)

    save(project.obs_db(root), odb)


def add_object(obj_dict: YamlDict, name: str):

    db_names = list(obj_dict.keys())
    if name in db_names:
        print(f'Skipping {name}, already present')
        return

    db_names.append(name)
    db_names = natsorted(db_names)
    pos = db_names.index(name)

    entry = {
        'name': name,
        'constellation': common.get_constellation(name),
        'type': ''
    }

    obj_dict.insert(pos, name, entry)
    if pos < (len(obj_dict) - 1):
        obj_dict.yaml_set_comment_before_after_key(db_names[pos + 1], before='')


def add_objects(root: str,
                name: str):

    odb = load(project.object_db(root))
    obj_dict: YamlDict = odb['objects']

    names = name.replace(', ', ',').split(',')
    for n in names:
        add_object(obj_dict, n)

    save(project.object_db(root), odb)

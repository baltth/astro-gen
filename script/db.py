#!/usr/bin/env python3

import project

from pathlib import Path
from ruamel.yaml import YAML, comments
from typing import Dict, List

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
    sk: YamlList[YamlDict] = sdb['sketches']

    def overwrite_or_add():
        for e in sk:
            if e['full'] == entry['full']:
                e.update(**entry)
                return
        sk.append(entry)
        sk.yaml_set_comment_before_after_key(len(sk) - 1, before='')

    overwrite_or_add()

    save(project.sketch_db(root), sdb)

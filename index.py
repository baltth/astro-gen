#!/usr/bin/env python3

import constellations
import pages

from collections import OrderedDict
from natsort import natsorted
from operator import itemgetter
from typing import Callable, Dict, List


def raw_data(obs_db: List, object_db: Dict) -> List:

    data = {}

    sorted_obs = natsorted(obs_db, key=itemgetter('date'))
    for obs in sorted_obs:
        names = obs['name'] if isinstance(obs['name'], list) else [obs['name']]
        for n in names:
            obj = object_db[n]
            data[n] = {
                'name': n,
                'obj': obj,
                'row': pages.index_row(n, names, obs['date'], obj)
            }

    return natsorted(data.values(), key=itemgetter('name'))


def collect(data: List[Dict], key: Callable) -> OrderedDict[str, List[Dict]]:

    res = {}
    for d in data:
        k = key(d['obj'])
        if k in res.keys():
            res[k].append(d['row'])
        else:
            res[k] = [d['row']]

    for v in res.values():
        v = natsorted(v)

    res = OrderedDict(natsorted(res.items()))
    if 'Other' in res.keys():
        res.move_to_end('Other')
    return res


def subpage(title: str, content: List[str]) -> List[str]:

    return [pages.subtitle(title), ''] + content + ['']


def index_content(obs_db: Dict, object_db: Dict) -> List[str]:

    raw = raw_data(obs_db, object_db)

    def by_type(obj: Dict) -> str:
        # todo
        if 'star' in obj['type']:
            return 'Stars'
        if 'planet' in obj['type'].split():
            return 'Other'
        return 'Deep space'

    def by_constellation(obj: Dict) -> str:
        if constellations.is_constellation(obj['constellation']):
            return constellations.name(obj['constellation'])
        return 'Other'

    index_by_cat = pages.index_data(collect(raw, key=by_type))
    index_by_const = pages.index_data(collect(raw, key=by_constellation))

    return subpage('Categories', index_by_cat) + subpage('Constellations', index_by_const)

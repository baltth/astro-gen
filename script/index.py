#!/usr/bin/env python3

import common
from datatypes import ObsData, Object
import constellations
import pages

from collections import OrderedDict
from natsort import natsorted
from operator import itemgetter
from typing import Callable, Dict, List, Iterable


def raw_data(obs_db: List[ObsData], object_db: Dict[str, Object]) -> List:

    data = {}

    sorted_obs = natsorted(obs_db, key=lambda x: x.date)
    for obs in sorted_obs:
        for n in obs.names:
            data[n] = {
                'name': n,
                'obj': object_db[n],
                'row': pages.index_row(n, obs.names, common.obs_day(obs.date), object_db[n])
            }

    return natsorted(data.values(), key=itemgetter('name'))


def get_type(obj: Object) -> str:
    type_split = obj.type.split()

    if 'star' in type_split:
        return 'Stars'
    if obj.constellation == 'Moon' \
        or 'crater' in type_split:  # Yes, a 'crater' is assumed to be on Moon...
        return 'Moon'
    if 'planet' in type_split \
        or 'comet' in type_split \
        or 'asterism' in type_split:
        return 'Other'
    return 'Deep space'


def sort_categories(data: Iterable) -> OrderedDict:
    res = OrderedDict(natsorted(data))
    if 'Moon' in res.keys():
        res.move_to_end('Moon')
    if 'Other' in res.keys():
        res.move_to_end('Other')
    return res


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

    return sort_categories(res.items())


def subpage(title: str, content: List[str]) -> List[str]:

    return [pages.subtitle(title), ''] + content + ['']



def index_content(obs_db: Dict, object_db: Dict[str, Object]) -> List[str]:

    raw = raw_data(obs_db, object_db)


    def by_constellation(obj: Object) -> str:
        if constellations.is_constellation(obj.constellation):
            return constellations.name(obj.constellation)
        return 'Other'

    index_by_cat = pages.index_data(collect(raw, key=get_type))
    index_by_const = pages.index_data(collect(raw, key=by_constellation))

    return subpage('Categories', index_by_cat) + subpage('By constellation', index_by_const)

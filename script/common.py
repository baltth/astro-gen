#!/usr/bin/env python3

import constellations
from datatypes import Object

from datetime import datetime, timedelta
import re
from slugify import slugify
from typing import List, Dict, Union
import unicodedata


def to_greek(val: str) -> str:

    try:
        key = f'GREEK SMALL LETTER {val.upper()}'
        return unicodedata.lookup(key)
    except Exception:
        return val


def greek_name(name: Union[str, List[str]]) -> Union[str, List[str]]:

    if isinstance(name, list):
        return [greek_name(n) for n in name]

    split_name = name.split()
    if len(split_name) != 2:
        return name
    maybe_greek = to_greek(split_name[0])
    name_end = ' '.join(split_name[1:])
    return f'{maybe_greek} {name_end}'


def pretty_name(name: Union[str, List[str]]) -> Union[str, List[str]]:

    if isinstance(name, list):
        return [pretty_name(n) for n in name]

    split_name = name.split()
    if constellations.is_constellation(split_name[-1]):
        name_start = ' '.join(split_name[0:-1])
        return f'{name_start} {constellations.genitive(split_name[-1])}'

    messier_match = re.match(r'^M(\d{1,3})$', name)
    if messier_match:
        return f'Messier {messier_match.group(1)}'

    return name


def names_to_list(names: str) -> List[str]:
    return names.replace(', ', ',').split(',')


def traditional_name(name: Union[str, List[str]]) -> Union[str, List[str]]:

    if isinstance(name, list):
        return [traditional_name(n) for n in name]

    maybe_greek = greek_name(name)
    if maybe_greek != name:
        return maybe_greek

    # By designation table in https://en.wikipedia.org/wiki/Double_star
    struve_match = re.match(r'^(ST[A-Z]{1,2}) ?(\d+( [A-B,]+)?)$', name.upper())
    if struve_match:
        if struve_match.group(1) == 'STF':
            return f'Σ {struve_match.group(2)}'
        if struve_match.group(1) == 'STFA':
            return f'Σ I {struve_match.group(2)}'
        if struve_match.group(1) == 'STFB':
            return f'Σ II {struve_match.group(2)}'
        if struve_match.group(1) == 'STT':
            return f'OΣ {struve_match.group(2)}'
        if struve_match.group(1) == 'STTA':
            return f'OΣΣ {struve_match.group(2)}'

    return name


def pretty_name_str(name: Union[str, List[str]]) -> str:

    pn = pretty_name(name)
    if isinstance(pn, list):
        return ', '.join(pn)
    return pn


def short_desc(obj_data: Object) -> str:
    if not obj_data:
        return ''

    if constellations.is_constellation(obj_data.constellation):
        return f'{obj_data.type} in {constellations.name(obj_data.constellation)}'

    return f'{obj_data.type} in {obj_data.constellation}'


def md_link(text: str, url: str, desc: str = '') -> str:
    l = f'[{text}]({url}'
    if desc:
        l += f' "{desc}")'
    else:
        l += ')'
    return l


def md_image(text: str, url: str, desc: str = '') -> str:
    return f'!{md_link(text, url, desc)}'


def name_slug(obj: Union[str, List[str]]) -> str:
    if isinstance(obj, list):
        name = ','.join(obj)
    else:
        name = obj

    return slugify(name)


def file_basename(obj: Union[str, List[str]], date: str) -> str:
    return slugify(f'{name_slug(obj)}-{date}')


def sketch_name(obj: Union[str, List[str]], date: str) -> str:
    return f'{file_basename(obj, date)}.jpg'


def obs_page_name(obj: Union[str, List[str]], date: str) -> str:
    return f'{file_basename(obj, date)}.md'


def obs_day(date: str) -> str:

    if ':' not in date:
        # No time, just date, return the original
        return date

    d = datetime.fromisoformat(date)
    if d.hour < 12:
        # Observation after midnight, return the previous day
        prev = d.date() - timedelta(days=1)
        return prev.isoformat()

    # Observation before midnight, return the same day
    return d.date().isoformat()


def get_constellation(name: str) -> str:

    split_name = name.split()
    if len(split_name) > 1 and constellations.is_constellation(split_name[-1]):
        return split_name[-1]
    return ''

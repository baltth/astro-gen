#!/usr/bin/env python3

import common
from datatypes import Object, ObsData, get_all_data_of
import project

from copy import copy
import re
from typing import Any, Callable, Dict, List, Union


DATA_NOTE = '\u2020'    # 'dagger': †
DATA_NOTE_POSTFIX = f' {DATA_NOTE}'


def emph(s: str) -> str:
    return f'_{s}_'


def md_table(data: List, make_col: Callable, row_headers: List[str]) -> List[str]:

    def empty_data(r: List[str]) -> bool:
        return not any(r[1:])

    obj_data = [make_col(d) for d in data]

    cols = [row_headers] + [d for d in obj_data if not empty_data(d)]  # drop empty columns
    if len(cols) == 1:
        # Only the row header remains
        return []

    rows = [list(r) for r in zip(*cols)]

    table_data = [r for r in rows if not empty_data(r)]  # drop empty rows

    assert table_data
    if len(table_data) == 1:
        # Only the col header remains
        return []

    table = [' | '.join(row) for row in table_data]
    headline = '|'.join(['-'] * len(cols))
    return [table[0], headline] + table[1:] + ['']


def obs_table(data: ObsData) -> List[str]:

    rows = [
        'Objects' if len(data.names) > 1 else 'Object',
        'Observed at',
        'NELM',
        'Seeing',
        'Aperture',
        'Magnification',
        'FOV'
    ]

    custom_rows = list(data.data.keys())
    if custom_rows:
        rows += ['**Other data**'] + custom_rows

    def col(d: ObsData) -> List[str]:
        if len(d.fov) > 0 and re.search(r'\d+\s*$', d.fov.rstrip()):
            fov = d.fov.rstrip() + '\u00b0'
        else:
            fov = d.fov
        col_data = [
            ', '.join(common.pretty_name(d.names)),
            f'{d.loc}, {d.date}',
            f'~ {d.nelm}' if d.nelm else '',
            str(d.seeing) if d.seeing else '',
            f'{d.ap} mm' if d.ap else '',
            f'{d.mag}x' if d.mag else '',
            fov
        ]
        custom_data = [str(v) for v in d.data.values()]
        if custom_data:
            col_data += [' '] + custom_data
        return col_data

    return md_table([data], make_col=col, row_headers=rows)


def mark_fetched(data: str) -> str:
    if data:
        return data + DATA_NOTE_POSTFIX
    return ''


def get_annotated_data(obj: Object) -> Dict[str, Dict[str, Any]]:
    """
    Get a collection of component data with fetched fields marked with 
    """
    obj_data = get_all_data_of(obj)
    for od in obj_data.values():
        for k, v in od.items():
            if k in od.get('fetched_keys', []):
                od[k] = mark_fetched(v)
    return obj_data


def merge_general_data(data: Dict[str, Dict[str, Any]], name: str) -> Dict[str, Dict[str, Any]]:

    res = copy(data)

    if '_' in res.keys():
        if len(res) > 1:
            if name in res.keys():
                merge_to = name
            else:
                merge_to = list(res.keys())[0]
            for k, v in data['_'].items():
                if v and not res[merge_to].get(k, ''):
                    res[merge_to][k] = v
        else:
            res[name] = res['_']
        del res['_']

    return res


def make_desc_from_types(data: Dict[str, str]) -> str:

    if data.get('subtype') or data.get('type'):
        desc: str = data.get('subtype', '').lower()
        typ: str = data.get('type', '').lower()
        if desc != typ:
            # Add type as the 'qualified' item except in case of clusters.
            # 'cluster' word would be redundant in these cases, e.g.
            # 'Medium disperation, medium sized cluster with medium star density open cluster'
            if 'cluster' not in desc or 'cluster' not in typ:
                desc += ' ' + typ
        return desc.lstrip().capitalize()
    return ''


def preprocess_data(obj: Object) -> Dict[str, Dict[str, Any]]:

    data = merge_general_data(get_annotated_data(obj), obj.name)

    def del_if_exists(d: Dict, key: str):
        if key in d.keys():
            del d[key]

    for k, v in data.items():
        v['pretty_name'] = common.pretty_name(k)

        # Auto-add description
        if not v.get('desc', ''):
            desc = make_desc_from_types(v)
            if DATA_NOTE_POSTFIX in desc:
                desc = mark_fetched(desc.replace(DATA_NOTE_POSTFIX, ''))
            v['desc'] = desc

        # Set 'fetched name' if differs from the user-defined
        if 'name' in v.keys():
            name = v['name'].removesuffix(DATA_NOTE_POSTFIX)
            if name != k:
                v['fetched_name'] = name
            del v['name']

        del_if_exists(v, 'type')       # type and subtype combined to desc
        del_if_exists(v, 'subtype')
        del_if_exists(v, 'constellation')   # del a it's redundant
        del_if_exists(v, 'fetched_keys')    # del administrative data

    return data


def obj_table(objects: List[Object]) -> List[str]:

    data = {}
    for d in objects:
        data.update(preprocess_data(d))

    if not data:
        return []

    all_keys = dict.fromkeys(k for d in data.values() for k in d.keys())
    all_keys = list(all_keys.keys())

    PRIO_ROWS = [
        'pretty_name',
        'fetched_name',
        'desc',
        'ra',
        'dec',
        'mag'
    ]
    rows = PRIO_ROWS + [k for k in all_keys if k not in PRIO_ROWS]

    FANCY_PRIO_ROWS = [
        'Objects' if len(data) > 1 else 'Object',
        'Fetched as',
        'Desc.',
        'RA',
        'Dec',
        'Magnitude'
    ]
    rendered_rows = [r.replace('_', ' ').capitalize() for r in rows]
    rendered_rows = FANCY_PRIO_ROWS + rendered_rows[len(FANCY_PRIO_ROWS):]

    def col(data: Dict) -> List[str]:
        return [str(data.get(k, '')) for k in rows]

    tab = md_table(data=list(data.values()), make_col=col, row_headers=rendered_rows)

    if len(tab) > 0:
        assert len(tab) >= 4
        assert tab[-1] == ''

        # Skip table when there's only name + desc
        if len(tab) == 4:
            return []

    if any(DATA_NOTE_POSTFIX in row for row in tab):
        tab += [
            f'{DATA_NOTE} fetched from [astronomyapi.com](http://astronomyapi.com)',
            ''
        ]

    return tab


def tag_line(name: str,
             object_data: Object) -> str:

    def name_tags(n: str) -> List[str]:
        tags: List[str] = []

        # as pretty name is present as title,
        # we add the original name here on demand
        pretty = common.pretty_name(n)
        if pretty != n:
            tags.append(n)

        trad = common.traditional_name(n)
        if trad != n:
            tags.append(trad)
        return tags

    tags = [emph(t) for t in name_tags(name)]
    tags += [emph(a) for a in object_data.aka]

    sd = common.short_desc(object_data)
    if sd:
        if not tags:        # At least a name should be present before the desc
            tags += [emph(name)]

        sd = emph(sd[0].upper() + sd[1:])
        tags.append(sd)

    return ' - '.join(tags)


def subtitle(title: str, level: int = 2) -> str:
    assert level >= 2
    return '#'*level + ' ' + title


def header(title: str) -> List[str]:

    links = common.md_link('Main page', '../index.md') + ' - ' + common.md_link('Index', '../pages/obj_index.md')

    return [
        f'# {title}',
        '',
        links,
        ''
    ]


def note_block(text: str) -> List[str]:
    return [f'> {n}' for n in text.splitlines()] + ['']


def footer(notes: str = '', links: Dict[str, str] = {}) -> List[str]:

    md: List[str] = []

    if notes:
        md += note_block(notes)

    if links:
        md += [subtitle('Links'), ''] + [f'- {common.md_link(k, v)}' for k, v in links.items()]

    return md


def join(content: List[str]) -> str:

    return '\n'.join(content) + '\n'


def page(title: str,
         content: List[str],
         notes: str = '',
         links: Dict[str, str] = {}) -> str:

    md = header(title)
    md += content
    md += footer(notes=notes, links=links)

    return join(md)


def obs_body(title: str,
             names: List[str],
             img: str,
             obs_tab: List[str],
             text: str,
             object_data: Dict[str, Object],
             sketch_notes: str) -> List[str]:

    md = [tag_line(n, object_data.get(n, Object())) + '  ' for n in names]
    md += [
        '',
        common.md_image(title, f'{img}'),
        ''
    ]

    if text:
        md += text.splitlines() + ['']

    md += obs_tab + ['']

    if sketch_notes:
        md += note_block(sketch_notes)

    obj_tab = obj_table(list(object_data.values()))
    if obj_tab:
        md += [
            subtitle('Object data', level=4),
            ''
        ] + obj_tab

    if len(md[-1]) > 0:
        md.append('')

    return md


def log_row(names: Union[str, List[str]], date: str, from_main: bool = False) -> List[str]:

    pretty_name = common.pretty_name_str(names)
    date_prefix = date + ':'
    url = project.obs_page_url(names, date, from_main=from_main)
    return [date_prefix, pretty_name, url, '']


def index_row(obj_name: str,
              all_names: Union[str, List[str]],
              date: str,
              obj_data: Object) -> List[str]:

    pretty_name: str = common.pretty_name(obj_name)
    url = project.obs_page_url(all_names, date)
    desc = common.short_desc(obj_data)
    return ['', pretty_name, url, f'- {desc}']


def index_data(data: Union[List, Dict]) -> List[str]:

    def list_line(d: List) -> str:
        assert d
        assert isinstance(d[0], str)
        if len(d) > 1:
            assert len(d) == 4
            link_text = d[1]
            url = d[2]
            l = [d[0], common.md_link(link_text, url), d[3]]
            text = ' '.join([t for t in l if t])
        else:
            text = d[0]
        return f'- {text}'

    if isinstance(data, list):
        assert isinstance(data[0], list)
        return [list_line(d) for d in data]

    assert isinstance(data, dict)
    md: List[str] = []
    for k, v in data.items():
        assert isinstance(k, str)
        md += [subtitle(k, level=4), ''] + index_data(v) + ['']

    return md


def observation_page(obs_data: ObsData,
                     img: str,
                     notes: str = '',
                     links: Dict[str, str] = {},
                     object_data: Dict[str, Object] = {}) -> str:

    title = common.pretty_name_str(obs_data.names)

    o_table = obs_table(obs_data)

    md = obs_body(title=title,
                  names=obs_data.names,
                  img=img,
                  obs_tab=o_table,
                  text=obs_data.text,
                  object_data=object_data,
                  sketch_notes=notes)
    return page(title=title,
                content=md,
                links=links)


def index_page(title: str,
               data: Union[List, Dict],
               notes: str = '',
               links: Dict[str, str] = {}) -> str:

    return page(title=title,
                content=index_data(data),
                notes=notes,
                links=links)

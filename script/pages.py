#!/usr/bin/env python3

import common
from datatypes import ObjectData, ObsData
import project

from typing import Callable, Dict, List, Union


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

    ROWS = [
        'Objects' if len(data.names) > 1 else 'Object',
        'Observed at',
        'NELM',
        'Seeing',
        'Aperture',
        'Magnification',
        'FOV'
    ]

    def col(d: ObsData) -> List[str]:
        return [
            ', '.join(common.pretty_name(d.names)),
            f'{d.loc}, {d.date}',
            f'~ {d.nelm}' if d.nelm else '',
            str(d.seeing) if d.seeing else '',
            f'{d.ap} mm' if d.ap else '',
            f'{d.mag}x' if d.mag else '',
            f'{d.fov} \u00b0' if d.fov else ''
        ]

    return md_table([data], make_col=col, row_headers=ROWS)


def obj_table(data: List[ObjectData]) -> List[str]:

    ROWS = [
        'Objects' if len(data) > 1 else 'Object',
        'RightAscension',
        'Declination'
    ]

    def col(obj: ObjectData) -> List[str]:
        return [
            common.pretty_name(obj.name),
            obj.ra,
            obj.decl
        ]

    return md_table(data=data, make_col=col, row_headers=ROWS)


def tag_line(name: str,
             object_data: ObjectData) -> str:

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
             object_data: Dict[str, ObjectData],
             sketch_notes: str) -> List[str]:

    md = [tag_line(n, object_data.get(n, ObjectData())) + '  ' for n in names]
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
              obj_data: ObjectData) -> List[str]:

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
                     object_data: Dict[str, ObjectData] = {}) -> str:

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

#!/usr/bin/env python3

import common
from datatypes import ObsData, Object, SketchData
import db
import index
import pages
import project

import argparse
from copy import copy
from operator import itemgetter
from pathlib import Path
from typing import Dict, List, Tuple, Union
import yaml


DEFAULT_LOCATION = 'Dunaharaszti, HU'

project_root: str = ''


def write_file(cat: str, name: str, content: str):

    doc_root = Path(project.site_root(project_root))
    out_path = doc_root / cat / name
    out_path.write_text(content, encoding='utf8')


def sketch_of_obs(db: List[SketchData], obs: ObsData) -> SketchData:

    res = [s for s in db if obs.img in s.sub]

    assert len(res) == 1
    return res[0]


def object_data(object_db: Dict[str, Object], names: Union[str, List[str]]) -> Dict[str, Object]:

    if isinstance(names, str):
        return object_data(object_db, [names])

    return {n: object_db[n] for n in names if n in object_db.keys()}


def get_links_notes(sketch_db: List[SketchData], obs: ObsData) -> Tuple[Dict, str]:

    sketch = sketch_of_obs(sketch_db, obs)
    links = {
        'Full sketch': project.image_url(sketch.full)
    }

    if sketch.scan:
        links['Original sketch'] = project.scan_url(sketch.scan)

    return (links, sketch.notes)


def obs_page_name(obs: ObsData) -> str:
    return common.obs_page_name(obs.names, common.obs_day(obs.date))


def generate_obs(obs: ObsData, sketch_db: List[SketchData], object_db: Dict[str, Object]):

    img = project.image_url(obs.img)

    links, notes = get_links_notes(sketch_db=sketch_db, obs=obs)

    data = copy(obs)
    data.loc = obs.loc if obs.loc else DEFAULT_LOCATION

    content = pages.observation_page(obs_data=data,
                                     img=img,
                                     notes=notes,
                                     links=links,
                                     object_data=object_data(object_db, data.names))

    write_file('obs', obs_page_name(data), content)


def obs_log_data(obs_db: List[ObsData], from_main: bool) -> List:

    def row(obs: ObsData) -> List[str]:
        obs_day = common.obs_day(obs.date)
        return pages.log_row(obs.names, obs_day, from_main)

    data = [row(o) for o in obs_db]
    return sorted(data, key=itemgetter(0), reverse=True)


def generate_obs_log(obs_db: List[ObsData]):

    content = pages.index_page(title='All observations',
                               data=obs_log_data(obs_db, from_main=False))
    write_file('pages', 'log.md', content)


def generate_index(obs_db: List[ObsData], object_db: Dict[str, Object]):

    content = pages.page(title='Index',
                         content=index.index_content(obs_db=obs_db, object_db=object_db))
    write_file('pages', 'obj_index.md', content)


def load_md(file: str) -> List[str]:

    print(f'Loading {file} ...')

    try:
        text = Path(file).read_text()
        return text.splitlines()
    except Exception:
        print(f'Unable to read {file}, skipping content')
        return []


def generate_main(obs_db: List[ObsData]):

    latest_obs = obs_log_data(obs_db, from_main=True)[:10]

    main_pre = load_md(project.main_pre_file(project_root))
    main_post = load_md(project.main_post_file(project_root))

    SEPARATOR = [
        '',
        '---',
        ''
    ]

    content = main_pre + SEPARATOR

    content += [
        pages.subtitle('Latest'),
        ''
    ] + pages.index_data(latest_obs) + SEPARATOR

    content += [
        f'## {common.md_link('All observations', 'pages/log.md')}',
        '',
        f'## {common.md_link('Index', 'pages/obj_index.md')}',
        ''
    ] + SEPARATOR

    content += main_post

    write_file('', 'index.md', pages.join(content))


def regen(obs_db: List[ObsData], sketch_db: List[SketchData], object_db: Dict[str, Object]):

    print('Generating ...')

    for obs in obs_db:
        generate_obs(obs=obs, sketch_db=sketch_db, object_db=object_db)

    generate_obs_log(obs_db)
    generate_index(obs_db=obs_db, object_db=object_db)
    generate_main(obs_db)


def load(db: str) -> Union[Dict, List]:

    print(f'Loading {db} ...')

    with open(db) as f:
        data = yaml.safe_load(f)
        assert isinstance(data, dict) or isinstance(data, list)
        return data


def main():

    parser = argparse.ArgumentParser()
    parser.description = 'Regenerate pages'
    parser.add_argument('project_root', help='Root folder of project to generate')
    args = parser.parse_args()

    print(f'Project path: {args.project_root}')

    sketches = db.sketches(args.project_root)
    observations = db.observations(args.project_root)
    objects = db.objects(args.project_root)

    global project_root
    project_root = args.project_root

    regen(obs_db=observations,
          sketch_db=sketches,
          object_db=objects)

    print('Done')


if __name__ == "__main__":
    main()

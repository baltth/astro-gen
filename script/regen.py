#!/usr/bin/env python3

import common
import index
import main_page
import pages

import argparse
from operator import itemgetter
from typing import Dict, List, Tuple, Union
import yaml


DEFAULT_LOCATION = 'Dunaharaszti, HU'


def sketch_of_obs(db: List, obs: Dict) -> Dict:

    res = [s for s in db if obs['img'] in s['sub']]

    assert len(res) == 1
    return res[0]


def object_data(object_db: Dict, names: Union[str, List[str]]) -> Dict:

    if isinstance(names, str):
        return object_data(object_db, [names])

    return {n: object_db.get(n, {}) for n in names}


def get_links_notes(sketch_db: List, obs: Dict) -> Tuple[Dict, str]:

    sketch = sketch_of_obs(sketch_db, obs)
    links = {
        'Full sketch': common.image_url(sketch['full'])
    }

    notes = sketch.get('notes', '')

    scan = sketch.get('scan', '')
    if scan:
        links['Original sketch'] = common.scan_url(scan)

    return (links, notes)


def write_file(cat: str, name: str, content: str):

    out_path = common.PROJECT_ROOT / cat / name
    out_path.write_text(content, encoding='utf8')


def obs_page_name(obs: Dict) -> str:
    return common.obs_page_name(obs['name'], common.obs_day(obs['date']))


def generate_obs(obs: Dict, sketch_db: List, object_db: Dict):

    img = common.image_url(obs['img'])

    names = obs['name']
    links, notes = get_links_notes(sketch_db=sketch_db, obs=obs)

    content = pages.observation_page(names=names,
                                     img=img,
                                     date=obs['date'],
                                     nelm=obs['nelm'],
                                     ap=obs['ap'],
                                     mag=obs['mag'],
                                     fov=obs['fov'],
                                     loc=obs.get('loc', DEFAULT_LOCATION),
                                     text=obs.get('text', ''),
                                     notes=notes,
                                     links=links,
                                     object_data=object_data(object_db, names))

    write_file('obs', obs_page_name(obs), content)


def obs_log_data(obs_db: List, from_main: bool) -> List:

    def row(obs: Dict) -> List[str]:
        obs_day = common.obs_day(obs['date'])
        return pages.log_row(obs['name'], obs_day, from_main)

    data = [row(o) for o in obs_db]
    return sorted(data, key=itemgetter(0), reverse=True)


def generate_obs_log(obs_db: List):

    content = pages.index_page(title='All observations',
                               data=obs_log_data(obs_db, from_main=False))
    write_file('pages', 'log.md', content)


def generate_index(obs_db: List, object_db: Dict):

    content = pages.page(title='Index',
                         content=index.index_content(obs_db=obs_db, object_db=object_db))
    write_file('pages', 'obj_index.md', content)


def generate_main(obs_db: List):

    latest_obs = obs_log_data(obs_db, from_main=True)[:10]

    content = main_page.BEGIN + [
        '',
        pages.subtitle('Latest'),
        ''
    ]
    content += pages.index_data(latest_obs)
    content += [
        '',
        '---',
        '',
        f'### {common.md_link('All observations', 'pages/log.md')}',
        '',
        f'### {common.md_link('Index', 'pages/obj_index.md')}',
    ] + main_page.END

    write_file('', 'index.md', pages.join(content))


def regen(obs_db: List, sketch_db: Dict, object_db: Dict):

    for obs in obs_db:
        generate_obs(obs=obs, sketch_db=sketch_db, object_db=object_db)

    generate_obs_log(obs_db)
    generate_index(obs_db=obs_db, object_db=object_db)
    generate_main(obs_db)


def load(db: str) -> Union[Dict, List]:

    with open(db) as f:
        data = yaml.safe_load(f)
        assert isinstance(data, dict) or isinstance(data, list)
        return data


def main():

    parser = argparse.ArgumentParser()
    parser.description = 'Regenerate pages'
    parser.add_argument('observation_db')
    parser.add_argument('sketch_db')
    parser.add_argument('object_db')
    parser.add_argument('-l', '--last', type=int, default=0)
    args = parser.parse_args()

    sketch_db = load(args.sketch_db)
    assert isinstance(sketch_db, dict)

    obs_db = load(args.observation_db)
    assert isinstance(obs_db, dict)

    obj_db = load(args.object_db)
    assert isinstance(obj_db, dict)

    if args.last > 0:
        obs_db['observations'] = obs_db['observations'][-args.last:]

    regen(obs_db=obs_db['observations'],
          sketch_db=sketch_db['sketches'],
          object_db=obj_db['objects'])


if __name__ == "__main__":
    main()

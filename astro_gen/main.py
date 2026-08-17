#!/usr/bin/env python3

from . import common
from .datatypes import ObjectData
from . import db
from . import fetch
from . import proc_image
from . import project
from . import regen

import argparse
from datetime import datetime
from pathlib import Path
from shutil import copy as cp
from shlex import join as shjoin, split as shsplit
import sys
from typing import Dict


def _add_images(project_root: str,
                img: str,
                scan: str = '',
                x_offset: int = 0,
                y_offset: int = 0,
                scale: float = 1.0,
                first_object: str = '',
                second_object: str = '',
                full_page: bool = False,
                simple: bool = False) -> Dict:

    print('Processing images ...')

    meta_file = project.meta_file(project_root)
    has_meta = Path(meta_file).is_file()

    db_data = proc_image.split_cmd(source_image=img,
                                   dest=project.site_images(project_root),
                                   x_offset=x_offset,
                                   y_offset=y_offset,
                                   scale=scale,
                                   first_object=first_object,
                                   second_object=second_object,
                                   full_page=full_page,
                                   simple=simple,
                                   show=False,
                                   copyright_file=meta_file if has_meta else '')

    if scan:
        scan_file = Path(scan).parts[-1]
        out_path = f'{project.site_root(project_root)}/scan/{scan_file}'

        if has_meta:
            proc_image.copyright_cmd(source_image=scan,
                                     copyright_file=meta_file,
                                     out=out_path,
                                     show=False)
        else:
            cp(scan_file, out_path)

        db_data['scan'] = scan_file

    return db_data


def _add_sketch(root: str, data: Dict, cmd: str = ''):

    print('Add sketches ...')

    imgs = [
        data.get('first_img', ''),
        data.get('second_img', '')
    ]

    if not cmd:
        cmd = shjoin(sys.argv)

    db.add_sketch(root=root,
                  full=data['cropped_img'],
                  scan=data.get('scan', ''),
                  sub=[i for i in imgs if i],
                  cmd=[cmd])


def _add_observation(root: str, name: str, img_date: datetime):

    print(f'Add observation for {name} ...')

    db.add_obs(root,
               name=name,
               date=img_date.date().isoformat())


def fetch_astronomyapi_on_demand(name: str) -> Dict[str, ObjectData]:

    app_id, secret = fetch.astronomyapi_access()
    if not app_id:
        return {}

    print('Fetching astronomyapi.com')
    print(f'  with app ID {app_id}')

    names = common.names_to_list(name)
    data = {}
    for n in names:
        d = fetch.fetch(n, app_id=app_id, app_secret=secret)
        if d:
            data[n] = d

    return data


def _add_objects(root: str, name: str):

    print(f'Add object data for {name} ...')

    fetched = fetch_astronomyapi_on_demand(name)
    db.add_objects(root, name=name, fetched=fetched)


def add(project_root: str,
        img: str,
        scan: str = '',
        x_offset: int = 0,
        y_offset: int = 0,
        scale: float = 1.0,
        first_object: str = '',
        second_object: str = '',
        full_page: bool = False,
        simple: bool = False,
        cmd: str = ''):

    sketch_data = _add_images(project_root=project_root,
                              img=img,
                              scan=scan,
                              x_offset=x_offset,
                              y_offset=y_offset,
                              scale=scale,
                              first_object=first_object,
                              second_object=second_object,
                              full_page=full_page,
                              simple=simple)

    _add_sketch(root=project_root, data=sketch_data, cmd=cmd)

    for obj in [first_object, second_object]:
        if obj:
            _add_observation(root=project_root,
                             name=obj,
                             img_date=sketch_data['img_date'])
            _add_objects(root=project_root,
                         name=obj)


def fetch_objects(project_root: str,
                  obj: str,
                  name: str = '',
                  component: str = ''):

    fetch_name = name if name else obj
    fetched = fetch_astronomyapi_on_demand(fetch_name)
    print(fetched)
    if fetched:

        if component:
            fetch_map = {component: fetch_name}
        else:
            fetch_map = {fetch_name: fetch_name}

        print(f'Add object data for {obj} ...')
        db.add_objects(root=project_root,
                       name=obj,
                       fetched=fetched,
                       fetch_map={obj: fetch_map},
                       refresh=True)
    else:
        print(f'No data for {fetch_name}')


def _reproc_one(sketch: Dict, project_root: str):

    print(f'Reprocessing sketch {sketch['full']} ...')

    commands = sketch.get('_cmd', [])
    commands = [c for c in commands if ' add ' in c]
    if not commands:
        print('Skipping, sketch has no command data for \'add\'')
        return

    for c in commands:
        try:

            cmd = shsplit(c)[1:]
            print(f'Args were {shjoin(cmd)}')
            proc_args = arg_parser().parse_args(cmd)

            sketch_data = _add_images(project_root=project_root,
                                      img=proc_args.img,
                                      scan=proc_args.scan,
                                      x_offset=proc_args.x_offset,
                                      y_offset=proc_args.y_offset,
                                      scale=proc_args.scale,
                                      first_object=proc_args.first_object,
                                      second_object=proc_args.second_object,
                                      full_page=proc_args.full_page,
                                      simple=proc_args.simple)

            _add_sketch(root=project_root, data=sketch_data, cmd=c)

        except Exception as e:
            print(e)
            print('Unable to execute command')
            print(c)


def reproc(project_root: str, sketch: str = ''):

    sketches = db.sketches_raw(project_root)

    if sketch:
        basename = Path(sketch).name
        found = [s for s in sketches if s['full'] == basename]
        if not found:
            print(f'No sketch found with full name {basename}')
        elif len(found) > 1:
            print(f'Error: multiple sketches found with full name {basename}')
        else:
            _reproc_one(sketch=found[0], project_root=project_root)
    else:
        print('Reprocessing all sketches ...')
        for s in sketches:
            print('--------')
            _reproc_one(sketch=s, project_root=project_root)


def _regen_cmd(args: argparse.Namespace):
    regen.regen(project_root=args.project_root)


def _add_cmd(args: argparse.Namespace):

    add(project_root=args.project_root,
        img=args.img,
        scan=args.scan,
        x_offset=args.x_offset,
        y_offset=args.y_offset,
        scale=args.scale,
        first_object=args.first_object,
        second_object=args.second_object,
        full_page=args.full_page,
        simple=args.simple)


def _fetch_cmd(args: argparse.Namespace):

    fetch_objects(project_root=args.project_root,
                  obj=args.object,
                  name=args.name,
                  component=args.component)


def _reproc_cmd(args: argparse.Namespace):

    reproc(project_root=args.project_root,
           sketch=args.sketch)


def arg_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser()
    parser.description = 'Process and add observations'

    parser.add_argument('project_root', help='Root folder of project to generate')
    cmd = parser.add_subparsers(title='Commands')

    regen_parser = cmd.add_parser('regen', help='Regenerate pages')
    regen_parser.set_defaults(func=_regen_cmd)

    add_parser = cmd.add_parser('add', help='Add new observations')
    add_parser.add_argument('-i', '--img', help='Source image')
    add_parser.add_argument('-c', '--scan', help='Scanned image')
    add_parser.add_argument('-x', '--x-offset', type=int, default=0)
    add_parser.add_argument('-y', '--y-offset', type=int, default=0)
    add_parser.add_argument('-s', '--scale', type=float, default=1.0)
    add_parser.add_argument('-o1', '--first-object', default='')
    add_parser.add_argument('-o2', '--second-object', default='')
    add_parser.add_argument('--full-page', action='store_true')
    add_parser.add_argument('--simple', help='Use simple resize instead of \'luminance weighted\' method',
                            action='store_true')
    add_parser.set_defaults(func=_add_cmd)

    fetch_parser = cmd.add_parser('fetch', help='Fetch object data from astronomyapi.com')
    fetch_parser.add_argument('object')
    fetch_parser.add_argument('-n', '--name', help='Alias on astronomyapi.com', default='')
    fetch_parser.add_argument('-c', '--component', help='Add as component', default='')
    fetch_parser.set_defaults(func=_fetch_cmd)

    reproc_parser = cmd.add_parser('reproc', help='Reprocess previously added images')
    reproc_parser.add_argument('-s', '--sketch', help='Sketch file', default='')
    reproc_parser.set_defaults(func=_reproc_cmd)

    return parser


def main():

    args = arg_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

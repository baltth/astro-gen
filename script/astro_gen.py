#!/usr/bin/env python3

import common
from datatypes import ObjectData
import db
import fetch
import proc_image
import project

import argparse
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from shlex import join as shjoin
import sys
from typing import Dict


def add_images(args: argparse.Namespace) -> Dict:

    print('Processing images ...')

    split_args = deepcopy(args)
    setattr(split_args, 'source_image', args.img)
    setattr(split_args, 'dest',  project.site_images(args.project_root))
    setattr(split_args, 'show', False)
    db_data = proc_image.split_cmd(split_args)

    if args.scan:
        cr_args = deepcopy(args)
        setattr(cr_args, 'source_image', args.scan)
        scan_file = Path(args.scan).parts[-1]
        setattr(cr_args, 'out',  f'{project.site_root(args.project_root)}/scan/{scan_file}')
        setattr(cr_args, 'show', False)
        proc_image.copyright_cmd(cr_args)
        db_data['scan'] = scan_file

    return db_data


def add_sketch(root: str, data: Dict):

    print('Add sketches ...')

    imgs = [
        data.get('first_img', ''),
        data.get('second_img', '')
    ]

    db.add_sketch(root=root,
                  full=data['cropped_img'],
                  scan=data.get('scan', ''),
                  sub=[i for i in imgs if i],
                  cmd=[shjoin(sys.argv)])


def add_observation(root: str, name: str, img_date: datetime):

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


def add_objects(root: str, name: str):

    print(f'Add object data for {name} ...')

    fetched = fetch_astronomyapi_on_demand(name)
    db.add_objects(root, name=name, fetched=fetched)


def add_cmd(args: argparse.Namespace):

    sketch_data = add_images(args)
    add_sketch(root=args.project_root, data=sketch_data)

    if args.first_object:
        add_observation(root=args.project_root,
                        name=args.first_object,
                        img_date=sketch_data['img_date'])
        add_objects(root=args.project_root,
                    name=args.first_object)

    if args.second_object:
        add_observation(root=args.project_root,
                        name=args.second_object,
                        img_date=sketch_data['img_date'])
        add_objects(root=args.project_root,
                    name=args.second_object)


def fetch_cmd(args: argparse.Namespace):

    fetch_name = args.name if args.name else args.object
    fetched = fetch_astronomyapi_on_demand(fetch_name)
    print(fetched)
    if fetched:

        if fetch_name != args.object:
            fetched[args.object] = fetched[fetch_name]

        print(f'Add object data for {args.object} ...')
        db.add_objects(root=args.project_root,
                       name=args.object,
                       fetched=fetched,
                       refresh=True)
    else:
        print(f'No data for {fetch_name}')


def main():

    parser = argparse.ArgumentParser()
    parser.description = 'Process and add observations'

    parser.add_argument('project_root', help='Root folder of project to generate')
    cmd = parser.add_subparsers()

    add_parser = cmd.add_parser('add')
    add_parser.add_argument('-i', '--img', help='Source image')
    add_parser.add_argument('-c', '--scan', help='Scanned image')
    add_parser.add_argument('-x', '--x-offset', type=int, default=0)
    add_parser.add_argument('-y', '--y-offset', type=int, default=0)
    add_parser.add_argument('-s', '--scale', type=float, default=1.0)
    add_parser.add_argument('-o1', '--first-object', default='')
    add_parser.add_argument('-o2', '--second-object', default='')
    add_parser.set_defaults(func=add_cmd)

    fetch_parser = cmd.add_parser('fetch')
    fetch_parser.add_argument('object')
    fetch_parser.add_argument('-n', '--name', help='Alias on astronomyapi.com', default='')
    fetch_parser.set_defaults(func=fetch_cmd)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

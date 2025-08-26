#!/usr/bin/env python3

import db
import proc_image
import project

import argparse
from copy import deepcopy
from pathlib import Path
from shlex import join as shjoin
import sys
from typing import Dict


def add_images(args: argparse.Namespace) -> Dict:

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


def add_to_sketches(root: str, data: Dict):

    imgs = [
        data.get('first_img', ''),
        data.get('second_img', '')
    ]

    db.add_sketch(root=root,
                       full=data['cropped_img'],
                       scan=data.get('scan', ''),
                       sub=[i for i in imgs if i],
                       cmd=[shjoin(sys.argv)])


def main():

    parser = argparse.ArgumentParser()
    parser.description = 'Process and add observations'

    parser.add_argument('project_root', help='Root folder of project to generate')
    parser.add_argument('-i', '--img', help='Source image')
    parser.add_argument('-c', '--scan', help='Scanned image')
    parser.add_argument('-x', '--x-offset', type=int, default=0)
    parser.add_argument('-y', '--y-offset', type=int, default=0)
    parser.add_argument('-s', '--scale', type=float, default=1.0)
    parser.add_argument('-o1', '--first-object', default='')
    parser.add_argument('-o2', '--second-object', default='')

    args = parser.parse_args()

    sketch_data = add_images(args)
    add_to_sketches(root=args.project_root, data=sketch_data)


if __name__ == "__main__":
    main()

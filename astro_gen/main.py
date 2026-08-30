#!/usr/bin/env python3

from . import add
from . import check
from . import proc_image
from . import project
from . import regen

from pathlib import Path

import argparse
import sys


def _regen_cmd(args: argparse.Namespace):
    regen.regen(project_root=args.project_root)
    if not args.skip_checks and not check.check(root=args.project_root):
        sys.exit(1)


def _add_cmd(args: argparse.Namespace):

    add.add(project_root=args.project_root,
            img=args.img,
            scan=args.scan,
            x_offset=args.x_offset,
            y_offset=args.y_offset,
            scale=args.scale,
            first_object=args.first_object,
            second_object=args.second_object,
            full_page=args.full_page,
            simple=args.simple,
            add_new=args.new)


def _fetch_cmd(args: argparse.Namespace):

    add.fetch_objects(project_root=args.project_root,
                      obj=args.object,
                      name=args.name,
                      component=args.component)


def _reproc_cmd(args: argparse.Namespace):

    add.reproc(project_root=args.project_root,
               arg_parser=arg_parser(),
               sketch=args.sketch)


def _proc_cmd(args: argparse.Namespace):
    meta_file = project.meta_file(args.project_root)
    if meta_file and not Path(meta_file).is_file():
        meta_file = ''

    print(args.cutouts)
    proc_image.proc(img=args.image,
                    out_dir=args.out_dir,
                    cut_offset=args.cut_offset,
                    cutouts=args.cutouts,
                    simple_resize=args.simple,
                    meta=meta_file)


def arg_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser()
    parser.description = 'Process and add observations'

    parser.add_argument('project_root', help='Root folder of project to generate')
    cmd = parser.add_subparsers(title='Commands')

    regen_parser = cmd.add_parser('regen', help='Regenerate pages')
    regen_parser.add_argument('-s', '--skip-checks', action='store_true', help='Skip checks after generation')
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
    add_parser.add_argument('--new', help='Force adding new images instead of overwrite in case of existing additions',
                            action='store_true')
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

    proc_parser = cmd.add_parser('proc', help='Process images (experimental)')
    proc_parser.add_argument('image', help='Source image')
    proc_parser.add_argument('-o', '--out-dir', help='Output directory, defaults to ./tmp', default='./tmp')
    proc_parser.add_argument('-f', '--cut-offset', default='0,0')
    proc_parser.add_argument('-c', '--cutouts', nargs='+', help='Cutout images in \'WxH+X+Y\' format', default=[])
    proc_parser.add_argument('--simple', help='Use simple resize instead of \'luminance weighted\' method',
                             action='store_true')
    proc_parser.set_defaults(func=_proc_cmd)

    return parser


def main():

    args = arg_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

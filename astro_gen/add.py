
#!/usr/bin/env python3

from . import common
from .datatypes import ObjectData
from . import db
from . import fetch
from . import proc_image
from . import project

import argparse
from datetime import datetime
from pathlib import Path
from shutil import copy as cp
from shlex import join as shjoin, split as shsplit
import sys
from typing import Dict, List, Optional, Tuple


def _default_cutouts(meta: Dict) -> List[str]:

    DEFAULT_CUTOUTS = ['100%x60%', '100%x57%+0+43%']

    image_meta = meta.get('images', {})
    assert isinstance(image_meta, dict)
    if 'cutouts' in image_meta:
        cutouts = image_meta['cutouts']
    else:
        cutouts = DEFAULT_CUTOUTS

    assert isinstance(cutouts, list)
    return cutouts


def _add_images(project_root: str,
                img: str,
                positive: bool = False,
                cut_offset: str = '',
                first_object: str = '',
                second_object: str = '',
                full_page: bool = False,
                simple: bool = False,
                add_new: bool = False,
                date_override: str = '',
                work_dir: str = '') -> Dict:

    print('Processing images ...')

    meta = project.load_meta(project_root)

    if not work_dir:
        work_dir = 'tmp'
    work_path = Path(work_dir).resolve()
    work_path.mkdir(parents=True, exist_ok=True)

    if date_override:
        date = datetime.fromisoformat(date_override)
    else:
        date = proc_image.image_date(img)

    cutouts = [] if full_page else _default_cutouts(meta)

    proc_image.process(img,
                       out_dir=work_dir,
                       cut_offset=cut_offset,
                       cutouts=cutouts,
                       simple_resize=simple,
                       meta=meta)

    print('Adding files to project ...')

    return _copy_to_project(root=project_root,
                            work_path=work_path,
                            date=date,
                            positive=positive,
                            orig_name=img,
                            first_object=first_object,
                            second_object=second_object,
                            add_new=add_new)


def _copy_to_project(root: str,
                     work_path: Path,
                     date: datetime,
                     positive: bool,
                     orig_name: str,
                     first_object: str = '',
                     second_object: str = '',
                     add_new: bool = False) -> Dict[str, str]:

    if second_object == first_object:
        second_object += ' 2nd'

    if first_object and not second_object:
        full_name = f'{first_object} NA'
    elif second_object and not first_object:
        full_name = f'NA {second_object}'
    else:
        full_name = f'{first_object} {second_object}'

    files = {
        'scan': work_path / 'orig.jpg',
        'cropped_img': work_path / 'full.jpg',
        'first_img': work_path / 'c1-mid.jpg' if positive else work_path / 'c1-inv-mid.jpg',
        'second_img': work_path / 'c2-mid.jpg' if positive else work_path / 'c2-inv-mid.jpg'
    }

    db_data = {
        'img_date': date
    }

    site_scan = Path(project.site_root(root)) / 'scan'
    scan_dir = site_scan / str(date.year)
    scan_dir.mkdir(parents=True, exist_ok=True)
    scan_path = _add_file(src=files['scan'],
                          dst=scan_dir / Path(orig_name).name,
                          add_new=add_new)
    db_data['scan'] = str(scan_path.relative_to(site_scan))

    site_images = Path(project.site_images(root))
    img_dir = site_images / str(date.year)
    img_dir.mkdir(parents=True, exist_ok=True)

    full_path = _add_file(src=files['cropped_img'],
                          dst=img_dir / f'{_name_slug(full_name, date)}.jpg',
                          add_new=add_new)
    db_data['cropped_img'] = str(full_path.relative_to(site_images))

    if files['first_img'].is_file():
        first_img = _add_file(src=files['first_img'],
                              dst=img_dir / f'{_name_slug(first_object, date)}.jpg',
                              add_new=add_new)
        db_data['first_img'] = str(first_img.relative_to(site_images))
        db_data['first_name'] = first_object

    if files['second_img'].is_file():
        second_img = _add_file(src=files['second_img'],
                               dst=img_dir / f'{_name_slug(second_object, date)}.jpg',
                               add_new=add_new)
        db_data['second_img'] = str(second_img.relative_to(site_images))
        db_data['second_name'] = second_object

    return db_data


def _name_slug(name: str, date: datetime) -> str:
    return common.name_slug(f'{name}-{date.year:04}{date.month:02}{date.day:02}')


def _add_file(src: Path, dst: Path, add_new: bool) -> Path:

    name = _dest_file(dst, add_new)

    if name.is_file():
        print(f'Overwriting {name} ...')
    else:
        print(f'Saving to {name} ...')

    cp(src, name)
    return name


def _dest_file(file: Path, add_new: bool) -> Path:

    if file.is_file() and add_new:
        for i in range(2, 6):
            s = file.suffix
            n = file.name.removesuffix(s)
            maybe_name = file.parent / Path(f'{n}-{i}{s}')
            if not maybe_name.is_file():
                break
        return maybe_name
    return file


def _add_sketch(root: str, data: Dict, cmd: Optional[List[str]] = None, orig_cmd: Optional[List[str]] = None):

    print('Add sketches ...')

    imgs = [
        data.get('first_img', ''),
        data.get('second_img', '')
    ]

    if not cmd:
        this_app = Path(sys.argv[0]).name
        cmd = [shjoin([this_app] + sys.argv[1:])]

    db.add_sketch(root=root,
                  full=data['cropped_img'],
                  scan=data['scan'],
                  sub=[i for i in imgs if i],
                  cmd=cmd,
                  orig_cmd=orig_cmd)


def _add_observation(root: str, name: str, img_date: datetime):

    print(f'Add observation for {name} ...')

    db.add_obs(root,
               name=name,
               date=img_date.date().isoformat())


def _add_objects(root: str, name: str):

    print(f'Add object data for {name} ...')

    fetched = fetch_astronomyapi_on_demand(name)
    db.add_objects(root, name=name, fetched=fetched)


def add(project_root: str,
        img: str,
        first_object: str = '',
        second_object: str = '',
        positive: bool = False,
        cmd: str = '',
        add_sketch_only: bool = False,
        **kwargs):

    sketch_data = _add_images(project_root=project_root,
                              img=img,
                              positive=positive,
                              first_object=first_object,
                              second_object=second_object,
                              **kwargs)

    _add_sketch(root=project_root, data=sketch_data, cmd=cmd)

    if add_sketch_only:
        return

    for obj in [first_object, second_object]:
        if obj:
            _add_observation(root=project_root,
                             name=obj,
                             img_date=sketch_data['img_date'])
            _add_objects(root=project_root,
                         name=obj)


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


def _convert_command(orig_cmd: str) -> str:

    if ' add ' not in orig_cmd:
        return orig_cmd

    def drop_opt_val(cmd: str, opt: List[str]) -> Tuple[str, str]:
        cmd_split = shsplit(cmd)
        for o in opt:
            if o in cmd_split:
                i = cmd_split.index(o)
                assert i < len(cmd_split) - 1
                dropped_val = cmd_split[i+1]
                print(f'Dropping \'{shjoin([o, dropped_val])}\'...')
                cmd_split = cmd_split[:i] + cmd_split[i+2:]
                return shjoin(cmd_split), dropped_val
        return cmd, ''

    def replace_opt_val(cmd: str, opt: List[str], new_val: str, new_opt: str = '') -> Tuple[str, str]:
        cmd_split = shsplit(cmd)
        for o in opt:
            if o in cmd_split:
                i = cmd_split.index(o)
                assert i < len(cmd_split) - 1
                dropped_val = cmd_split[i+1]
                cmd_split[i+1] = new_val
                if new_opt:
                    cmd_split[i] = new_opt
                print(f'Replacing \'{shjoin([o, dropped_val])}\' with \'{shjoin([cmd_split[i], new_val])}\' ...')
                return shjoin(cmd_split), dropped_val
        return cmd, ''

    # '-i main_image -c scan_file' -> '-i scan_file'
    cmd, scan_file = drop_opt_val(orig_cmd, ['-c', '--scan'])
    if scan_file:
        cmd, orig_img = replace_opt_val(cmd, ['-i', '--img'], new_val=scan_file)
        if orig_img == scan_file:
            cmd += ' --positive'

    # '-x 40 -y 100' -> '-f 40,100'
    cmd, x_o = drop_opt_val(cmd, ['-x', '--x-offset'])
    if x_o:
        cmd, y_o = replace_opt_val(cmd, ['-y', '--y-offset'], new_val='.')
        assert y_o
        cmd, _ = replace_opt_val(cmd,
                                 ['-y', '--y-offset'],
                                 new_opt='-f',
                                 new_val=f'{x_o},{y_o}')

    cmd, _ = drop_opt_val(cmd, ['-s', '--scale'])
    return cmd


def _reproc_one(sketch: Dict, project_root: str, arg_parser: argparse.ArgumentParser):

    print(f'Reprocessing sketch {sketch['full']} ...')

    commands = sketch.get('_cmd', [])
    if isinstance(commands, str):
        commands = [commands]
    if not any(c for c in commands if ' add ' in c):
        print('Skipping, sketch has no command data for \'add\'')
        return

    orig_commands = sketch.get('_orig_cmd', commands)
    new_commands = []

    for i, c in enumerate(commands):

        cmd_orig = c
        print(f'Command #{i+1}: {c}')
        cmd = _convert_command(c)
        if cmd != cmd_orig:
            print(f'Normalized to {cmd}')

        new_commands.append(cmd)
        if ' add ' not in cmd:
            continue

        assert i == len(orig_commands) - 1
        try:
            proc_args = arg_parser.parse_args(shsplit(cmd)[1:])

            sketch_data = _add_images(project_root=project_root,
                                      img=proc_args.img,
                                      positive=proc_args.positive,
                                      cut_offset=proc_args.cut_offset,
                                      first_object=proc_args.first_object,
                                      second_object=proc_args.second_object,
                                      full_page=proc_args.full_page,
                                      simple=proc_args.simple,
                                      add_new=False)

            _add_sketch(root=project_root,
                        data=sketch_data,
                        cmd=new_commands,
                        orig_cmd=orig_commands if orig_commands != commands else [])

        # argparse exits on a malformed command line, catch it too
        # to keep reprocessing the remaining sketches
        except (Exception, SystemExit) as e:
            print(e)
            print('Unable to execute command')
            print(c)


def reproc(project_root: str, arg_parser: argparse.ArgumentParser, sketch: str = ''):

    sketches = db.sketches_raw(project_root)

    if sketch:
        basename = Path(sketch).name
        found = [s for s in sketches if s['full'].endswith(basename)]
        if not found:
            found = [s for s in sketches if s['scan'].endswith(basename)]
        if not found:
            print(f'No sketch found with full/scan name {basename}')
        elif len(found) > 1:
            print(f'Error: multiple sketches found with full/scan name {basename}')
        else:
            _reproc_one(sketch=found[0], project_root=project_root, arg_parser=arg_parser)
    else:
        print('Reprocessing all sketches ...')
        for s in sketches:
            print('--------')
            _reproc_one(sketch=s, project_root=project_root, arg_parser=arg_parser)

#!/usr/bin/env python3

from astro_gen import add
from astro_gen.datatypes import ObjectData
from astro_gen.main import arg_parser

from datetime import datetime
from pathlib import Path
from shlex import split as shsplit
from typing import Callable, Dict, List
import pytest


IMG_DATE = datetime(2026, 8, 16, 23, 30)

DEFAULT_CUTOUTS = ['100%x60%', '100%x57%+0+43%']

# The images proc_image.process() creates in the work folder.

PROCESSED_IMAGES = ['orig.jpg', 'full.jpg',
                    'c1-mid.jpg', 'c1-inv-mid.jpg',
                    'c2-mid.jpg', 'c2-inv-mid.jpg']


def image_data(**overrides) -> Dict:
    """A typical return value of _add_images() for a single object."""

    data = {
        'img_date': IMG_DATE,
        'scan': '2026/cluster.jpg',
        'cropped_img': '2026/c47-na-20260816.jpg',
        'first_img': '2026/c47-20260816.jpg',
        'first_name': 'C47'
    }
    data.update(overrides)
    return data


def processed(*names: str) -> Callable:
    """Side effect for the process mock, creating the given images only."""

    def _create(*args, out_dir: str, **kwargs):
        for n in names:
            (Path(out_dir) / n).write_text(f'the {n}')

    return _create


def content_of(file: Path) -> str:
    return file.read_text()


def files_of(folder: Path) -> List[str]:
    return sorted(f.name for f in folder.iterdir())


@pytest.fixture
def project_root(tmp_path) -> str:
    """A project folder without a meta file."""

    (tmp_path / 'docs' / 'img').mkdir(parents=True)
    (tmp_path / 'docs' / 'scan').mkdir()
    return str(tmp_path)


@pytest.fixture
def meta_file(project_root) -> str:
    """Add a meta file with image settings to the project."""

    p = Path(project_root) / 'static' / 'meta.yaml'
    p.parent.mkdir()
    p.write_text('author: Jane Doe\nimages:\n  cutouts:\n    - 100%x50%\n')
    return str(p.resolve())


@pytest.fixture
def proc_mock(mocker):
    """Patch the image processing, it creates its images in the work folder."""

    m = mocker.patch.object(add.proc_image, 'process')
    m.side_effect = processed(*PROCESSED_IMAGES)
    return m


@pytest.fixture
def date_mock(mocker):
    return mocker.patch.object(add.proc_image, 'image_date', return_value=IMG_DATE)


@pytest.fixture
def work_dir(tmp_path) -> str:
    """The work folder of the processing, outside of the project."""
    return str(tmp_path / 'work')


@pytest.fixture
def work_path(tmp_path) -> Path:
    """A work folder holding the images of an already processed source image."""

    p = tmp_path / 'work'
    p.mkdir()
    for n in PROCESSED_IMAGES:
        (p / n).write_text(f'the {n}')
    return p


@pytest.fixture
def cp_mock(mocker):
    return mocker.patch.object(add, 'cp')


@pytest.fixture
def db_mock(mocker):
    return mocker.patch.object(add, 'db')


@pytest.fixture
def fetch_mock(mocker):
    """Patch the fetch module with credentials set and a single object found."""

    m = mocker.patch.object(add, 'fetch')
    m.astronomyapi_access.return_value = ('the-id', 'the-secret')
    m.fetch.side_effect = lambda name, **kwargs: ObjectData(name=name)
    return m


# _default_cutouts()

def test_default_cutouts():

    assert add._default_cutouts({}) == DEFAULT_CUTOUTS
    # image settings without cutouts
    assert add._default_cutouts({'images': {}}) == DEFAULT_CUTOUTS


def test_default_cutouts_from_meta():

    assert add._default_cutouts({'images': {'cutouts': ['100%x50%']}}) == ['100%x50%']


def test_default_cutouts_empty_list_is_kept():

    # an explicitly empty list means no cutouts, not the defaults
    assert add._default_cutouts({'images': {'cutouts': []}}) == []


def test_default_cutouts_malformed_meta():

    with pytest.raises(AssertionError):
        add._default_cutouts({'images': 'no-settings-here'})
    with pytest.raises(AssertionError):
        add._default_cutouts({'images': {'cutouts': '100%x50%'}})


# _add_images()

def test_add_images(project_root, work_dir, proc_mock, date_mock):

    data = add._add_images(project_root=project_root,
                           img='./orig/cluster.jpg',
                           cut_offset='10,20',
                           first_object='C47',
                           second_object='Alpha UMi',
                           simple=True,
                           work_dir=work_dir)

    # the source image is processed into the work folder
    assert proc_mock.call_args.args == ('./orig/cluster.jpg',)
    kwargs = proc_mock.call_args.kwargs
    assert kwargs['out_dir'] == work_dir
    assert kwargs['cut_offset'] == '10,20'
    assert kwargs['cutouts'] == DEFAULT_CUTOUTS
    assert kwargs['simple_resize'] is True
    # no meta file in the project
    assert kwargs['meta'] == {}

    # the results are copied to the project and registered
    assert data == {
        'img_date': IMG_DATE,
        'scan': '2026/cluster.jpg',
        'cropped_img': '2026/c47-alpha-umi-20260816.jpg',
        'first_img': '2026/c47-20260816.jpg',
        'first_name': 'C47',
        'second_img': '2026/alpha-umi-20260816.jpg',
        'second_name': 'Alpha UMi'
    }


def test_add_images_with_meta_file(project_root, meta_file, work_dir, proc_mock, date_mock):

    add._add_images(project_root=project_root,
                    img='./orig/cluster.jpg',
                    work_dir=work_dir)

    kwargs = proc_mock.call_args.kwargs
    # the meta of the project is passed to the processing ...
    assert kwargs['meta']['author'] == 'Jane Doe'
    # ... and it provides the cutouts too
    assert kwargs['cutouts'] == ['100%x50%']


def test_add_images_full_page(project_root, work_dir, proc_mock, date_mock):
    """A full page sketch is not cut into pieces."""

    proc_mock.side_effect = processed('orig.jpg', 'full.jpg')

    data = add._add_images(project_root=project_root,
                           img='./orig/cluster.jpg',
                           first_object='C47',
                           full_page=True,
                           work_dir=work_dir)

    assert proc_mock.call_args.kwargs['cutouts'] == []
    # without cutouts there are no object images
    assert 'first_img' not in data
    assert 'second_img' not in data


def test_add_images_date_of_the_image(project_root, work_dir, proc_mock, date_mock):

    data = add._add_images(project_root=project_root,
                           img='./orig/cluster.jpg',
                           work_dir=work_dir)

    date_mock.assert_called_once_with('./orig/cluster.jpg')
    assert data['img_date'] == IMG_DATE


def test_add_images_date_override(project_root, work_dir, proc_mock, date_mock):

    data = add._add_images(project_root=project_root,
                           img='./orig/cluster.jpg',
                           date_override='2025-01-02 21:00',
                           work_dir=work_dir)

    # the image is not consulted at all
    date_mock.assert_not_called()
    assert data['img_date'] == datetime(2025, 1, 2, 21, 0)
    # the folders and the names follow the overridden date
    assert data['scan'] == '2025/cluster.jpg'


def test_add_images_work_dir_is_created(project_root, work_dir, proc_mock, date_mock):

    assert not Path(work_dir).is_dir()

    add._add_images(project_root=project_root,
                    img='./orig/cluster.jpg',
                    work_dir=work_dir)

    assert Path(work_dir).is_dir()


def test_add_images_default_work_dir(project_root, proc_mock, date_mock, monkeypatch, tmp_path):
    """Without a work folder './tmp' is used."""

    cwd = tmp_path / 'cwd'
    cwd.mkdir()
    monkeypatch.chdir(cwd)

    add._add_images(project_root=project_root, img='./orig/cluster.jpg')

    assert proc_mock.call_args.kwargs['out_dir'] == 'tmp'
    assert (cwd / 'tmp').is_dir()


# _copy_to_project()

def test_copy_to_project(project_root, work_path):

    data = add._copy_to_project(root=project_root,
                                work_path=work_path,
                                date=IMG_DATE,
                                positive=False,
                                orig_name='./orig/cluster.jpg',
                                first_object='C47',
                                second_object='Alpha UMi')

    assert data == {
        'img_date': IMG_DATE,
        'scan': '2026/cluster.jpg',
        'cropped_img': '2026/c47-alpha-umi-20260816.jpg',
        'first_img': '2026/c47-20260816.jpg',
        'first_name': 'C47',
        'second_img': '2026/alpha-umi-20260816.jpg',
        'second_name': 'Alpha UMi'
    }

    # the scan is the original image, kept under its own name
    scan = Path(project_root, 'docs', 'scan', '2026', 'cluster.jpg')
    assert content_of(scan) == 'the orig.jpg'

    img_dir = Path(project_root, 'docs', 'img', '2026')
    assert content_of(img_dir / 'c47-alpha-umi-20260816.jpg') == 'the full.jpg'
    # the negatives are used by default
    assert content_of(img_dir / 'c47-20260816.jpg') == 'the c1-inv-mid.jpg'
    assert content_of(img_dir / 'alpha-umi-20260816.jpg') == 'the c2-inv-mid.jpg'


def test_copy_to_project_positive(project_root, work_path):

    add._copy_to_project(root=project_root,
                         work_path=work_path,
                         date=IMG_DATE,
                         positive=True,
                         orig_name='./orig/cluster.jpg',
                         first_object='C47',
                         second_object='Alpha UMi')

    img_dir = Path(project_root, 'docs', 'img', '2026')
    assert content_of(img_dir / 'c47-20260816.jpg') == 'the c1-mid.jpg'
    assert content_of(img_dir / 'alpha-umi-20260816.jpg') == 'the c2-mid.jpg'


def test_copy_to_project_single_object(project_root, work_path):

    data = add._copy_to_project(root=project_root,
                                work_path=work_path,
                                date=IMG_DATE,
                                positive=False,
                                orig_name='./orig/cluster.jpg',
                                first_object='C47')

    # the missing object is marked in the name of the full image
    assert data['cropped_img'] == '2026/c47-na-20260816.jpg'
    # the second cutout is added regardless, under the name of the missing object
    assert data['second_img'] == '2026/20260816.jpg'
    assert data['second_name'] == ''


def test_copy_to_project_second_object_only(project_root, work_path):

    data = add._copy_to_project(root=project_root,
                                work_path=work_path,
                                date=IMG_DATE,
                                positive=False,
                                orig_name='./orig/cluster.jpg',
                                second_object='Alpha UMi')

    assert data['cropped_img'] == '2026/na-alpha-umi-20260816.jpg'


def test_copy_to_project_two_images_of_the_same_object(project_root, work_path):

    data = add._copy_to_project(root=project_root,
                                work_path=work_path,
                                date=IMG_DATE,
                                positive=False,
                                orig_name='./orig/cluster.jpg',
                                first_object='C47',
                                second_object='C47')

    # the second one is marked to keep the images apart
    assert data['second_name'] == 'C47 2nd'
    assert data['second_img'] == '2026/c47-2nd-20260816.jpg'
    assert data['cropped_img'] == '2026/c47-c47-2nd-20260816.jpg'


def test_copy_to_project_without_cutouts(project_root, work_path):

    for f in ['c1-mid.jpg', 'c1-inv-mid.jpg', 'c2-mid.jpg', 'c2-inv-mid.jpg']:
        (work_path / f).unlink()

    data = add._copy_to_project(root=project_root,
                                work_path=work_path,
                                date=IMG_DATE,
                                positive=False,
                                orig_name='./orig/cluster.jpg',
                                first_object='C47')

    assert 'first_img' not in data
    assert 'second_img' not in data
    # the scan and the full image are added anyway
    assert data['scan'] == '2026/cluster.jpg'
    assert data['cropped_img'] == '2026/c47-na-20260816.jpg'


def test_copy_to_project_folders_of_the_year_are_created(project_root, work_path):

    assert not Path(project_root, 'docs', 'scan', '2025').is_dir()
    assert not Path(project_root, 'docs', 'img', '2025').is_dir()

    add._copy_to_project(root=project_root,
                         work_path=work_path,
                         date=datetime(2025, 1, 2, 21, 0),
                         positive=False,
                         orig_name='./orig/cluster.jpg',
                         first_object='C47')

    assert Path(project_root, 'docs', 'scan', '2025').is_dir()
    assert Path(project_root, 'docs', 'img', '2025', 'c47-20250102.jpg').is_file()


def test_copy_to_project_existing_files_are_overwritten(project_root, work_path):

    img_dir = Path(project_root, 'docs', 'img', '2026')
    img_dir.mkdir(parents=True)
    (img_dir / 'c47-20260816.jpg').write_text('the previous image')

    data = add._copy_to_project(root=project_root,
                                work_path=work_path,
                                date=IMG_DATE,
                                positive=False,
                                orig_name='./orig/cluster.jpg',
                                first_object='C47')

    assert data['first_img'] == '2026/c47-20260816.jpg'
    assert content_of(img_dir / 'c47-20260816.jpg') == 'the c1-inv-mid.jpg'


def test_copy_to_project_add_new(project_root, work_path):

    img_dir = Path(project_root, 'docs', 'img', '2026')
    img_dir.mkdir(parents=True)
    (img_dir / 'c47-20260816.jpg').write_text('the previous image')

    data = add._copy_to_project(root=project_root,
                                work_path=work_path,
                                date=IMG_DATE,
                                positive=False,
                                orig_name='./orig/cluster.jpg',
                                first_object='C47',
                                add_new=True)

    # the existing image is kept, the new one is added beside it
    assert data['first_img'] == '2026/c47-20260816-2.jpg'
    assert content_of(img_dir / 'c47-20260816.jpg') == 'the previous image'
    assert content_of(img_dir / 'c47-20260816-2.jpg') == 'the c1-inv-mid.jpg'


# _name_slug()

def test_name_slug():

    assert add._name_slug('C47', IMG_DATE) == 'c47-20260816'
    assert add._name_slug('Alpha UMi', IMG_DATE) == 'alpha-umi-20260816'


def test_name_slug_date_is_padded():

    assert add._name_slug('C47', datetime(2025, 1, 2)) == 'c47-20250102'


def test_name_slug_without_name():

    assert add._name_slug('', IMG_DATE) == '20260816'


# _add_file()

def test_add_file(tmp_path, capsys):

    src = tmp_path / 'src.jpg'
    src.write_text('the image')
    dst = tmp_path / 'dst.jpg'

    assert add._add_file(src=src, dst=dst, add_new=False) == dst

    assert content_of(dst) == 'the image'
    assert f'Saving to {dst}' in capsys.readouterr().out


def test_add_file_existing_is_overwritten(tmp_path, capsys):

    src = tmp_path / 'src.jpg'
    src.write_text('the image')
    dst = tmp_path / 'dst.jpg'
    dst.write_text('the previous image')

    assert add._add_file(src=src, dst=dst, add_new=False) == dst

    assert content_of(dst) == 'the image'
    assert f'Overwriting {dst}' in capsys.readouterr().out


def test_add_file_add_new(tmp_path):

    src = tmp_path / 'src.jpg'
    src.write_text('the image')
    dst = tmp_path / 'dst.jpg'
    dst.write_text('the previous image')

    assert add._add_file(src=src, dst=dst, add_new=True) == tmp_path / 'dst-2.jpg'

    assert files_of(tmp_path) == ['dst-2.jpg', 'dst.jpg', 'src.jpg']


# _dest_file()

def test_dest_file(tmp_path):

    file = tmp_path / 'img.jpg'
    assert add._dest_file(file, add_new=False) == file
    assert add._dest_file(file, add_new=True) == file


def test_dest_file_existing_is_reused(tmp_path):

    file = tmp_path / 'img.jpg'
    file.touch()
    assert add._dest_file(file, add_new=False) == file


def test_dest_file_add_new(tmp_path):

    file = tmp_path / 'img.jpg'
    file.touch()
    assert add._dest_file(file, add_new=True) == tmp_path / 'img-2.jpg'


def test_dest_file_add_new_takes_the_first_free_name(tmp_path):

    file = tmp_path / 'img.jpg'
    file.touch()
    (tmp_path / 'img-2.jpg').touch()
    (tmp_path / 'img-3.jpg').touch()

    assert add._dest_file(file, add_new=True) == tmp_path / 'img-4.jpg'


def test_dest_file_add_new_is_limited(tmp_path):

    file = tmp_path / 'img.jpg'
    file.touch()
    for i in range(2, 6):
        (tmp_path / f'img-{i}.jpg').touch()

    # the last variant is reused when all of them are taken
    assert add._dest_file(file, add_new=True) == tmp_path / 'img-5.jpg'


# _add_sketch()

def test_add_sketch(db_mock):

    data = image_data(second_name='Alpha UMi',
                      second_img='2026/alpha-umi-20260816.jpg')

    add._add_sketch(root='/the/root', data=data, cmd=['astro-gen /the/root add -i x.jpg'])

    db_mock.add_sketch.assert_called_once_with(
        root='/the/root',
        full='2026/c47-na-20260816.jpg',
        scan='2026/cluster.jpg',
        sub=['2026/c47-20260816.jpg', '2026/alpha-umi-20260816.jpg'],
        cmd=['astro-gen /the/root add -i x.jpg'],
        orig_cmd=None)


def test_add_sketch_single_object(db_mock):

    add._add_sketch(root='/the/root', data=image_data(), cmd=['the cmd'])

    # the missing second image is dropped
    assert db_mock.add_sketch.call_args.kwargs['sub'] == ['2026/c47-20260816.jpg']


def test_add_sketch_full_page(db_mock):

    data = image_data()
    del data['first_img']

    add._add_sketch(root='/the/root', data=data, cmd=['the cmd'])

    assert db_mock.add_sketch.call_args.kwargs['sub'] == []


def test_add_sketch_cmd_from_argv(db_mock, monkeypatch):

    monkeypatch.setattr(add.sys, 'argv', ['astro-gen', '/the/root', 'add', '-i', 'the img.jpg'])

    add._add_sketch(root='/the/root', data=image_data())

    # the invocation is recorded, quoted to stay reusable
    assert db_mock.add_sketch.call_args.kwargs['cmd'] == \
        ['astro-gen /the/root add -i \'the img.jpg\'']


# _add_observation()

def test_add_observation(db_mock):

    add._add_observation(root='/the/root', name='C47', img_date=IMG_DATE)

    # the time of the image is dropped, the date is stored in ISO format
    db_mock.add_obs.assert_called_once_with('/the/root',
                                            name='C47',
                                            date='2026-08-16')


# _add_objects()

def test_add_objects(db_mock, fetch_mock):

    add._add_objects(root='/the/root', name='C47')

    fetch_mock.fetch.assert_called_once_with('C47',
                                             app_id='the-id',
                                             app_secret='the-secret')
    db_mock.add_objects.assert_called_once_with('/the/root',
                                                name='C47',
                                                fetched={'C47': ObjectData(name='C47')})


def test_add_objects_without_credentials(db_mock, fetch_mock):

    fetch_mock.astronomyapi_access.return_value = ('', '')

    add._add_objects(root='/the/root', name='C47')

    # the object is added even without fetched data
    fetch_mock.fetch.assert_not_called()
    db_mock.add_objects.assert_called_once_with('/the/root', name='C47', fetched={})


# add()

def test_add(project_root, work_dir, proc_mock, date_mock, db_mock, fetch_mock):

    add.add(project_root=project_root,
            img='./orig/cluster.jpg',
            first_object='C47',
            cmd='the cmd',
            work_dir=work_dir)

    proc_mock.assert_called_once()
    db_mock.add_sketch.assert_called_once()
    db_mock.add_obs.assert_called_once_with(project_root, name='C47', date='2026-08-16')
    db_mock.add_objects.assert_called_once_with(project_root,
                                                name='C47',
                                                fetched={'C47': ObjectData(name='C47')})


def test_add_two_objects(project_root, work_dir, proc_mock, date_mock, db_mock, fetch_mock):

    add.add(project_root=project_root,
            img='./orig/cluster.jpg',
            first_object='C47',
            second_object='Alpha UMi',
            cmd='the cmd',
            work_dir=work_dir)

    # a single sketch with an observation of both objects
    db_mock.add_sketch.assert_called_once()
    assert [c.kwargs['name'] for c in db_mock.add_obs.call_args_list] == ['C47', 'Alpha UMi']
    assert [c.kwargs['name'] for c in db_mock.add_objects.call_args_list] == ['C47', 'Alpha UMi']


def test_add_no_objects(project_root, work_dir, proc_mock, date_mock, db_mock, fetch_mock):

    add.add(project_root=project_root,
            img='./orig/cluster.jpg',
            cmd='the cmd',
            work_dir=work_dir)

    # the sketch is added, but there's nothing to observe
    db_mock.add_sketch.assert_called_once()
    db_mock.add_obs.assert_not_called()
    db_mock.add_objects.assert_not_called()


def test_add_positive_image(project_root, work_dir, proc_mock, date_mock, db_mock, fetch_mock):

    add.add(project_root=project_root,
            img='./orig/cluster.jpg',
            first_object='C47',
            positive=True,
            cmd='the cmd',
            work_dir=work_dir)

    # the positive variant of the cutout is registered
    img = Path(project_root, 'docs', 'img', '2026', 'c47-20260816.jpg')
    assert content_of(img) == 'the c1-mid.jpg'


def test_add_sketch_only(project_root, work_dir, proc_mock, date_mock, db_mock, fetch_mock):

    add.add(project_root=project_root,
            img='./orig/cluster.jpg',
            first_object='C47',
            cmd='the cmd',
            add_sketch_only=True,
            work_dir=work_dir)

    # the images are added, the observation and the object data are left alone
    db_mock.add_sketch.assert_called_once()
    db_mock.add_obs.assert_not_called()
    db_mock.add_objects.assert_not_called()


# fetch_astronomyapi_on_demand()

def test_fetch_astronomyapi_on_demand(fetch_mock):

    assert add.fetch_astronomyapi_on_demand('C47') == {'C47': ObjectData(name='C47')}


def test_fetch_astronomyapi_on_demand_multiple_names(fetch_mock):

    data = add.fetch_astronomyapi_on_demand('C47, Alpha UMi')

    # each name is fetched separately
    assert data == {'C47': ObjectData(name='C47'),
                    'Alpha UMi': ObjectData(name='Alpha UMi')}
    assert [c.args[0] for c in fetch_mock.fetch.call_args_list] == ['C47', 'Alpha UMi']


def test_fetch_astronomyapi_on_demand_skips_missing(fetch_mock):

    fetch_mock.fetch.side_effect = \
        lambda name, **kwargs: ObjectData(name=name) if name == 'C47' else None

    assert add.fetch_astronomyapi_on_demand('C47, No Such Object') == \
        {'C47': ObjectData(name='C47')}


@pytest.mark.parametrize('access', [('', 'the-secret'), ('', '')])
def test_fetch_astronomyapi_on_demand_without_credentials(access, fetch_mock):

    fetch_mock.astronomyapi_access.return_value = access

    assert add.fetch_astronomyapi_on_demand('C47') == {}
    fetch_mock.fetch.assert_not_called()


# fetch_objects()

def test_fetch_objects(db_mock, fetch_mock):

    add.fetch_objects(project_root='/the/root', obj='C47')

    fetch_mock.fetch.assert_called_once_with('C47',
                                             app_id='the-id',
                                             app_secret='the-secret')
    db_mock.add_objects.assert_called_once_with(root='/the/root',
                                                name='C47',
                                                fetched={'C47': ObjectData(name='C47')},
                                                fetch_map={'C47': {'C47': 'C47'}},
                                                refresh=True)


def test_fetch_objects_by_alias(db_mock, fetch_mock):

    add.fetch_objects(project_root='/the/root', obj='C47', name='NGC 6934')

    # the alias is fetched ...
    assert fetch_mock.fetch.call_args.args == ('NGC 6934',)
    kwargs = db_mock.add_objects.call_args.kwargs
    # ... and stored for the object under its own name
    assert kwargs['name'] == 'C47'
    assert kwargs['fetched'] == {'NGC 6934': ObjectData(name='NGC 6934')}
    assert kwargs['fetch_map'] == {'C47': {'NGC 6934': 'NGC 6934'}}


def test_fetch_objects_as_component(db_mock, fetch_mock):

    add.fetch_objects(project_root='/the/root',
                      obj='Alpha UMi',
                      name='Polaris B',
                      component='B')

    # the fetched data is mapped to the component of the object
    assert db_mock.add_objects.call_args.kwargs['fetch_map'] == \
        {'Alpha UMi': {'B': 'Polaris B'}}


def test_fetch_objects_no_data(db_mock, fetch_mock, capsys):

    fetch_mock.fetch.return_value = None
    fetch_mock.fetch.side_effect = None

    add.fetch_objects(project_root='/the/root', obj='No Such Object')

    db_mock.add_objects.assert_not_called()
    assert 'No data for No Such Object' in capsys.readouterr().out


def test_fetch_objects_without_credentials(db_mock, fetch_mock, capsys):

    fetch_mock.astronomyapi_access.return_value = ('', '')

    add.fetch_objects(project_root='/the/root', obj='C47')

    db_mock.add_objects.assert_not_called()
    assert 'No data for C47' in capsys.readouterr().out


# The recorded 'add' commands of a sketch, in the current and in the obsolete format.

ADD_CMD = 'astro-gen ./example add -i ./orig/cluster.jpg -o1 C47 -f 10,20 --simple'
REGEN_CMD = 'astro-gen ./example regen'


OLD_ADD_CMD = ('./script/astro_gen.py ./example add -i ./orig/cluster_inv.jpg '
               '-c ./orig/cluster.jpg -x 65 -y 170 -o1 C47 -o2 \'Alpha UMi\'')


# _convert_command()

def test_convert_command_of_a_current_command():

    assert add._convert_command(ADD_CMD) == ADD_CMD


def test_convert_command_of_another_command():

    # only the 'add' commands are converted
    assert add._convert_command(REGEN_CMD) == REGEN_CMD


def test_convert_command_offsets_are_merged():

    assert add._convert_command('astro-gen ./example add -i x.jpg -x 65 -y 170 -o1 C47') == \
        'astro-gen ./example add -i x.jpg -f 65,170 -o1 C47'


def test_convert_command_long_options():

    cmd = 'astro-gen ./example add -i x.jpg --x-offset 65 --y-offset 170 --scale 2.0 -o1 C47'
    assert add._convert_command(cmd) == 'astro-gen ./example add -i x.jpg -f 65,170 -o1 C47'


def test_convert_command_scale_is_dropped():

    assert add._convert_command('astro-gen ./example add -i x.jpg -s 0.5 -o1 C47') == \
        'astro-gen ./example add -i x.jpg -o1 C47'


def test_convert_command_scan_is_dropped():

    cmd = add._convert_command('astro-gen ./example add -i x.jpg -c scan.jpg -o1 C47')
    assert ' -c ' not in cmd

    cmd = add._convert_command('astro-gen ./example add -i x.jpg --scan scan.jpg -o1 C47')
    assert '--scan' not in cmd


def test_convert_command_keeps_the_quoting():

    assert '-o2 \'Alpha UMi\'' in add._convert_command(OLD_ADD_CMD)


def test_convert_command_result_is_parseable():

    args = arg_parser().parse_args(shsplit(add._convert_command(OLD_ADD_CMD))[1:])

    assert args.cut_offset == '65,170'
    assert args.first_object == 'C47'
    assert args.second_object == 'Alpha UMi'


def test_convert_command_offset_without_its_pair():

    # the two offsets were always used together
    with pytest.raises(AssertionError):
        add._convert_command('astro-gen ./example add -i x.jpg -x 65 -o1 C47')


def test_convert_command_option_without_value():

    with pytest.raises(AssertionError):
        add._convert_command('astro-gen ./example add -i x.jpg -x')


# reproc()

def sketch_entry(full: str = '2026/c47-na-20260816.jpg', **overrides) -> Dict:

    entry = {'full': full, 'scan': '2026/cluster.jpg', '_cmd': [ADD_CMD]}
    entry.update(overrides)
    return entry


@pytest.fixture
def add_images_mock(mocker):
    """Patch the image handling, reproc() only replays the recorded commands."""
    return mocker.patch.object(add, '_add_images', return_value=image_data())


@pytest.fixture
def sketches_mock(db_mock):
    """Return a single reprocessable sketch by default."""

    db_mock.sketches_raw.return_value = [sketch_entry()]
    return db_mock.sketches_raw


def test_reproc(project_root, sketches_mock, add_images_mock, db_mock):

    add.reproc(project_root=project_root, arg_parser=arg_parser())

    # the recorded command line is replayed
    assert add_images_mock.call_args.kwargs == {
        'project_root': project_root,
        'img': './orig/cluster.jpg',
        'positive': False,
        'cut_offset': '10,20',
        'first_object': 'C47',
        'second_object': '',
        'full_page': False,
        'simple': True,
        # the existing images are replaced, no new ones are added
        'add_new': False
    }

    # the sketch is updated, keeping the original command
    assert db_mock.add_sketch.call_args.kwargs['cmd'] == [ADD_CMD]
    # the observations and objects are left untouched
    db_mock.add_obs.assert_not_called()
    db_mock.add_objects.assert_not_called()


def test_reproc_all_sketches(project_root, sketches_mock, add_images_mock, db_mock):

    sketches_mock.return_value = [sketch_entry('a.jpg'), sketch_entry('b.jpg')]

    add.reproc(project_root=project_root, arg_parser=arg_parser())

    assert add_images_mock.call_count == 2
    assert db_mock.add_sketch.call_count == 2


def test_reproc_positive_image(project_root, sketches_mock, add_images_mock):

    sketches_mock.return_value = [sketch_entry(_cmd=[f'{ADD_CMD} -p'])]

    add.reproc(project_root=project_root, arg_parser=arg_parser())

    assert add_images_mock.call_args.kwargs['positive'] is True


def test_reproc_converts_an_old_command(project_root, sketches_mock, add_images_mock, capsys):

    sketches_mock.return_value = [sketch_entry(_cmd=[OLD_ADD_CMD])]

    add.reproc(project_root=project_root, arg_parser=arg_parser())

    # the obsolete options are converted to the current ones
    kwargs = add_images_mock.call_args.kwargs
    assert kwargs['cut_offset'] == '65,170'
    assert kwargs['first_object'] == 'C47'
    assert kwargs['second_object'] == 'Alpha UMi'
    assert 'Normalized to' in capsys.readouterr().out


def test_reproc_single_sketch(project_root, sketches_mock, add_images_mock, db_mock):

    sketches_mock.return_value = [sketch_entry('a.jpg'), sketch_entry('b.jpg')]

    # the sketch is matched by file name, regardless of the path
    add.reproc(project_root=project_root,
               arg_parser=arg_parser(),
               sketch='./docs/img/b.jpg')

    add_images_mock.assert_called_once()
    assert db_mock.add_sketch.call_args.kwargs['full'] == '2026/c47-na-20260816.jpg'


def test_reproc_sketch_by_file_name(project_root, sketches_mock, add_images_mock):

    sketches_mock.return_value = [sketch_entry('2026/a.jpg'), sketch_entry('2026/b.jpg')]

    # the folder of the year is not part of the name to match
    add.reproc(project_root=project_root, arg_parser=arg_parser(), sketch='b.jpg')

    add_images_mock.assert_called_once()


def test_reproc_sketch_by_scan_name(project_root, sketches_mock, add_images_mock):

    sketches_mock.return_value = [sketch_entry('a.jpg', scan='2026/cluster.jpg'),
                                  sketch_entry('b.jpg', scan='2026/comet.jpg')]

    # sketches without a matching full name are looked up by their scan
    add.reproc(project_root=project_root,
               arg_parser=arg_parser(),
               sketch='./orig/comet.jpg')

    add_images_mock.assert_called_once()


def test_reproc_unknown_sketch(project_root, sketches_mock, add_images_mock, capsys):

    add.reproc(project_root=project_root, arg_parser=arg_parser(), sketch='no-such.jpg')

    add_images_mock.assert_not_called()
    assert 'No sketch found with full/scan name no-such.jpg' in capsys.readouterr().out


def test_reproc_ambiguous_sketch(project_root, sketches_mock, add_images_mock, capsys):

    sketches_mock.return_value = [sketch_entry('a.jpg'), sketch_entry('a.jpg')]

    add.reproc(project_root=project_root, arg_parser=arg_parser(), sketch='a.jpg')

    add_images_mock.assert_not_called()
    assert 'multiple sketches found with full/scan name a.jpg' in capsys.readouterr().out


def test_reproc_ambiguous_scan(project_root, sketches_mock, add_images_mock, capsys):

    sketches_mock.return_value = [sketch_entry('a.jpg'), sketch_entry('b.jpg')]

    # both sketches were made of the same scan
    add.reproc(project_root=project_root, arg_parser=arg_parser(), sketch='cluster.jpg')

    add_images_mock.assert_not_called()
    assert 'multiple sketches found with full/scan name cluster.jpg' in capsys.readouterr().out


@pytest.mark.parametrize('sketch', [sketch_entry(_cmd=[]),
                                    sketch_entry(_cmd=[REGEN_CMD]),
                                    {'full': 'c47-na-20260816.jpg'}])
def test_reproc_sketch_without_add_command(sketch,
                                           project_root,
                                           sketches_mock,
                                           add_images_mock,
                                           db_mock,
                                           capsys):

    sketches_mock.return_value = [sketch]

    add.reproc(project_root=project_root, arg_parser=arg_parser())

    add_images_mock.assert_not_called()
    db_mock.add_sketch.assert_not_called()
    assert 'Skipping, sketch has no command data' in capsys.readouterr().out


def test_reproc_continues_on_error(project_root,
                                   sketches_mock,
                                   add_images_mock,
                                   db_mock,
                                   capsys):

    sketches_mock.return_value = [sketch_entry('a.jpg'), sketch_entry('b.jpg')]
    add_images_mock.side_effect = [FileNotFoundError('./orig/cluster.jpg'), image_data()]

    add.reproc(project_root=project_root, arg_parser=arg_parser())

    # the failing sketch is reported and skipped, the next one is processed
    out = capsys.readouterr().out
    assert 'Unable to execute command' in out
    db_mock.add_sketch.assert_called_once()


def test_reproc_continues_on_malformed_command(project_root,
                                               sketches_mock,
                                               add_images_mock,
                                               db_mock,
                                               capsys):

    # a hand-edited command line argparse can't parse
    bad_cmd = 'astro-gen ./example add --no-such-option'
    sketches_mock.return_value = [sketch_entry('a.jpg', _cmd=[bad_cmd]),
                                  sketch_entry('b.jpg')]

    add.reproc(project_root=project_root, arg_parser=arg_parser())

    # the exit of the parser doesn't abort the run
    out = capsys.readouterr().out
    assert 'Unable to execute command' in out
    add_images_mock.assert_called_once()
    db_mock.add_sketch.assert_called_once()

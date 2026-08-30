#!/usr/bin/env python3

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from math import floor, ceil
import numpy
from pathlib import Path
from pprint import pformat
import shutil
from tempfile import mkstemp
from typing import Tuple, Dict, List, Optional, Union
import yaml

from PIL import Image, ImageDraw, ImageFont, ExifTags
from PIL.Image import Image as ImageT
from slugify import slugify

from .image_curves import Curves, apply

ARTIST_TAG = 0x013b
COPYRIGHT_TAG = 0x8298
DATE_TIME_TAG = 0x132
DESCRIPTION_TAG = 0x010e
SOFTWARE_TAG = 0x0131


def load_yaml(file: str) -> Dict:

    with open(file, encoding='utf8') as f:
        data = yaml.safe_load(f)
        assert isinstance(data, dict)
        return data


def copyright_meta(year: int, cr_data: Dict) -> str:
    assert year >= 1900
    return f'(C) {year}, {cr_data['author']}, {cr_data['email']}'


def copyright_text_on_image(year: int, cr_data: Dict) -> str:
    assert year >= 1900
    text = cr_data['image_note']
    assert isinstance(text, str)
    return text.replace('YEAR', str(year))


def print_meta(img: ImageT):

    meta = img.getexif()
    for k, v in meta.items():
        print(f'  {k} - {ExifTags.TAGS.get(k, k)}: {v}')


def image_date(img: ImageT) -> datetime:

    try:
        date_str = img.getexif()[DATE_TIME_TAG]
        return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
    except Exception:
        return datetime.now()


def image_year(img: ImageT) -> int:

    return image_date(img).year


def _to_px(v: str, ref: int):
    if v.endswith('%'):
        if not ref:
            raise ValueError('Using relative size \'%\' without reference value')
        return round(int(v.removesuffix('%')) / 100 * ref)
    return int(v)


def parse_offset(desc: str, ref_size: Optional[Tuple[int, int]] = None) -> Tuple[int, int]:

    if '+' in desc:
        o_x, _, o_y = desc.partition('+')
    elif ',' in desc:
        o_x, _, o_y = desc.partition(',')
    else:
        raise ValueError(f'Invalid offset: {desc}')

    return (_to_px(o_x, ref_size[0]), _to_px(o_y, ref_size[1]))


def parse_size_offset(desc: str, ref_size: Optional[Tuple[int, int]] = None) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """ WxH+X+Y to ((W, H), (X, Y)) """

    if not ref_size:
        ref_size = (0, 0)

    size, _, offset = desc.partition('+')

    assert 'x' in size
    w, _, h = size.partition('x')
    width = _to_px(w, ref_size[0])
    height = _to_px(h, ref_size[1])

    if offset:
        offs_x, offs_y = parse_offset(offset, ref_size)
    else:
        offs_x = 0
        offs_y = 0

    return ((width, height), (offs_x, offs_y))


def parse_bounds(desc: str, ref_size: Optional[Tuple[int, int]]) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """ WxH+X+Y to ((X, Y), (X+W, Y+H)) """
    size, offs = parse_size_offset(desc, ref_size)
    return (offs[0], offs[1], int(offs[0] + size[0]), int(offs[1] + size[1]))


def remove_frame(src: ImageT,
                 o_x: int,
                 o_y: int,
                 scale: float) -> ImageT:

    W = 0.94
    H = 0.91

    orig_width, orig_height = src.size
    w = int(orig_width * W * scale)
    h = int(orig_height * H * scale)

    print(f"Crop {orig_width}x{orig_height} to {w}x{h}")
    bounds = (o_x, o_y, o_x + w, o_y + h)
    print(f'Bounds: {pformat(bounds)}')

    return src.crop(bounds)


def crop(src: ImageT, desc: str) -> ImageT:

    bounds = parse_bounds(desc, src.size)
    print(f'Cutting {desc} -> {bounds} ...')

    if bounds[2] > src.size[0] or bounds[3] > src.size[1]:
        raise ValueError(f'Cut {bounds} exceeds image size {src.size}')

    return src.crop(bounds)


def split_image(src: ImageT) -> Tuple[ImageT, ImageT]:

    H_SPLIT = 60
    H_SPLIT_2 = 57

    img1 = crop(src, f'100%x{H_SPLIT}%')
    img2 = crop(src, f'100%x{H_SPLIT_2}%+0+{100-H_SPLIT_2}%')

    return (img1, img2)


def luminance_weighted_downscale(image_array: numpy.ndarray, scale: float):
    """Apply luminance-weighted downscaling to preserve bright features."""

    assert 0 < scale < 1

    h, w = image_array.shape[:2]
    new_h = int(h * scale)
    new_w = int(w * scale)

    scale_inv = 1 / scale

    # Block index range for a dimension
    def ix_range(ix: int, dim: int) -> Tuple[int, int]:
        start_ix = ix * scale_inv
        end_ix = min(start_ix + scale_inv, dim)
        return (int(floor(start_ix)), int(ceil(end_ix)))

    # Weighted average based on luminance
    def calc_from_weights(block: numpy.ndarray, weights: numpy.ndarray) -> float:
        total_weight = numpy.sum(weights)
        if total_weight > 0:
            return numpy.sum(block * weights) / total_weight
        else:
            return numpy.mean(block)

    # Check if RGB
    assert len(image_array.shape) == 3

    # RGB image - calculate luminance weights
    # Standard luminance weights: R=0.299, G=0.587, B=0.114
    luminance = 0.299 * image_array[:, :, 0] + 0.587 * image_array[:, :, 1] + 0.114 * image_array[:, :, 2]
    channels = image_array.shape[2]
    result = numpy.zeros((new_h, new_w, channels), dtype=image_array.dtype)

    for c in range(channels):
        for i in range(new_h):
            for j in range(new_w):
                start_i, end_i = ix_range(i, h)
                start_j, end_j = ix_range(j, w)

                block = image_array[start_i:end_i, start_j:end_j, c]
                weights = luminance[start_i:end_i, start_j:end_j]
                result[i, j, c] = calc_from_weights(block=block, weights=weights)

    # For grayscale image:
    # ```py
    # result = numpy.zeros((new_h, new_w), dtype=image_array.dtype)
    #
    # for i in range(new_h):
    #     for j in range(new_w):
    #         start_i, end_i = ix_range(i, h)
    #         start_j, end_j = ix_range(j, w)
    #
    #         block = image_array[start_i:end_i, start_j:end_j]
    #         weights = block.astype(numpy.float32) ** 2    # Use squared values as weights
    #         result[i, j] = calc_from_weights(block=block, weights=weights)
    # ```

    return result


def resize_to_width(img: ImageT, w: int, mode: str = 'lw') -> ImageT:

    print(f'Resizing to width {w} ...')
    orig_width, orig_height = img.size

    scale = w / orig_width
    assert scale < 1.0

    if mode == 'lw':
        print('Using \'luminance weighted\' method, this may take some time...')
        assert img.mode == 'RGB'
        img_array = numpy.array(img)
        resized_array = luminance_weighted_downscale(img_array, scale)
        resized_array = numpy.clip(resized_array, 0, 255).astype(numpy.uint8)
        return Image.fromarray(resized_array, mode='RGB')
    else:
        return img.resize((w, int(scale * orig_height)))


def add_copyright_img(src: ImageT, cr_data: Dict) -> ImageT:

    FONT_SIZE = 11
    TEXT_OFFSET = 4
    TEXT_COLOR = 'dimgray'

    img = deepcopy(src)

    if not cr_data:
        return img

    _, height = img.size
    coords = (TEXT_OFFSET, height - TEXT_OFFSET - FONT_SIZE)

    draw = ImageDraw.Draw(img)
    draw.text(coords,
              copyright_text_on_image(image_year(img), cr_data),
              fill=TEXT_COLOR,
              font=ImageFont.load_default(FONT_SIZE))
    return img


def update_exif(img: ImageT, desc: str, cr_data: Dict) -> Image.Exif:

    exif = img.getexif()
    exif[SOFTWARE_TAG] = 'github.com/baltth/astro-gen.git'
    if desc:
        exif[DESCRIPTION_TAG] = desc
    if cr_data:
        exif[ARTIST_TAG] = cr_data['author']
        exif[COPYRIGHT_TAG] = copyright_meta(image_year(img), cr_data)

    return exif


def process(src: ImageT,
            x_offset: int,
            y_offset: int,
            scale: float,
            simple_resize: bool = False,
            split: bool = True,
            cr_data: Optional[Dict] = None) -> Tuple[ImageT, ImageT, Optional[ImageT]]:

    if not cr_data:
        cr_data = {}

    WIDTH = 800

    cropped = remove_frame(src, x_offset, y_offset, scale)

    method = 'simple' if simple_resize else 'lw'

    if split:
        img1, img2 = split_image(cropped)
        img1 = resize_to_width(img1, WIDTH, method)
        img2 = resize_to_width(img2, WIDTH, method)
    else:
        img1 = resize_to_width(cropped, WIDTH, method)
        img2 = None

    return (add_copyright_img(cropped, cr_data),
            add_copyright_img(img1, cr_data),
            add_copyright_img(img2, cr_data) if img2 else None)


def save_image(img: ImageT,
               name: str,
               add_new: bool,
               desc: str,
               cr_data: Dict) -> str:

    name_as_path = Path(name)
    if name_as_path.is_file() and add_new:
        for i in range(2, 6):
            s = name_as_path.suffix
            n = name.removesuffix(s)
            maybe_name = f'{n}-{i}{s}'
            if not Path(maybe_name).is_file():
                break
        name = maybe_name

    if Path(name).is_file():
        print(f'Overwriting {name} ...')
    else:
        print(f'Saving to {name} ...')

    name_as_path.parent.mkdir(parents=True, exist_ok=True)
    meta = update_exif(img, desc, cr_data)
    img.save(name, exif=meta.tobytes())
    return name


def save_object(img: ImageT,
                dest_dir: str,
                object_name: str,
                date: datetime,
                add_new: bool,
                cr_data: Optional[Dict] = None) -> str:

    if not cr_data:
        cr_data = {}

    name = f'{date.year:04}/' + slugify(f'{object_name}-{date.year:04}{date.month:02}{date.day:02}')
    path_prefix = f'{dest_dir}/' if dest_dir else ''
    saved = save_image(img,
                       name=f'{path_prefix}{name}.jpg',
                       add_new=add_new,
                       desc=f'Sketch of {object_name}',
                       cr_data=cr_data)
    return saved.removeprefix(path_prefix)


def split_cmd(source_image: str,
              dest: str,
              x_offset: int = 0,
              y_offset: int = 0,
              scale: float = 1.0,
              first_object: str = '',
              second_object: str = '',
              full_page: bool = False,
              add_new: bool = False,
              date_override: str = '',
              simple: bool = False,
              show: bool = False,
              copyright_file: str = '') -> Dict:

    if copyright_file:
        cr_data = load_yaml(copyright_file)
    else:
        cr_data = None

    src = Image.open(source_image)

    print(f'Source image: {source_image}')
    print_meta(src)

    cropped, img1, img2 = process(src,
                                  x_offset,
                                  y_offset,
                                  scale,
                                  simple_resize=simple,
                                  split=not full_page,
                                  cr_data=cr_data)

    if show:
        cropped.show()
        img1.show()
        if img2:
            img2.show()

    if date_override:
        date = datetime.fromisoformat(date_override)
    else:
        date = image_date(src)

    db_data = {}
    db_data['img_date'] = date

    if first_object:
        n = save_object(img=img1,
                        dest_dir=dest,
                        object_name=first_object,
                        date=date,
                        add_new=add_new,
                        cr_data=cr_data)
        db_data['first_name'] = first_object
        db_data['first_img'] = n

        if second_object == first_object:
            second_object += ' 2nd'

    if second_object:
        assert not full_page
        assert img2

        n = save_object(img=img2,
                        dest_dir=dest,
                        object_name=second_object,
                        date=date,
                        add_new=add_new,
                        cr_data=cr_data)
        db_data['second_name'] = first_object
        db_data['second_img'] = n

    if first_object and not second_object:
        full_name = f'{first_object} NA'
    elif second_object and not first_object:
        full_name = f'NA {second_object}'
    else:
        full_name = f'{first_object} {second_object}'

    n = save_object(img=cropped,
                    dest_dir=dest,
                    object_name=full_name,
                    date=date,
                    add_new=add_new,
                    cr_data=cr_data)
    db_data['cropped_img'] = n

    return db_data


def copyright_cmd(source_image: str,
                  copyright_file: str,
                  out: str = '',
                  show: bool = False):

    cr_data = load_yaml(copyright_file)
    src = Image.open(source_image)

    print(f'Source image: {source_image}')
    print_meta(src)

    img = add_copyright_img(src, cr_data)
    if show:
        img.show()
    if out:
        out_file = out
    else:
        _, name = mkstemp(suffix='.jpg')
        out_file = name

    save_image(img,
               name=out_file,
               desc='',
               add_new=False,
               cr_data=cr_data)


def _enhance_pos(img: ImageT, strength: float) -> ImageT:
    c = Curves.combine(Curves.ambient(strength), Curves.shadows(strength))
    return apply(image=img, curve=c)


def _enhance_inv(img: ImageT, strength: float) -> ImageT:
    c = Curves.combine(Curves.ambient(strength), Curves.highlights(strength))
    return apply(image=img, curve=c)


def _prepare_out_dir(out_dir) -> Path:

    out_path = Path(out_dir).resolve()

    print(f'Creating {out_path} ...')
    out_path.mkdir(parents=True, exist_ok=True)

    # out_path could be simply removed with rmtree, but this would
    # remove wrk dir of other sw (e.g. a picture viewer), inducing
    # a restart on it. This is avoided removing the contents one-by-one.
    for f in out_path.glob('*'):
        if f.is_file():
            f.unlink()
        elif f.is_dir():
            shutil.rmtree(f, ignore_errors=True)

    return out_path


@dataclass
class SaveContext:
    out_path: Path
    meta: Optional[Dict]
    exif_desc: str


EXT = '.jpg'

FULL = 'full'
INV = 'inv'
MID = 'mid'
SMALL = 'small'
ENH = 'enh'

MID_WIDTH = 800
SMALL_WIDTH = 200

ADD_CR_ABOVE = 250


def _save(ctx: SaveContext, img: ImageT, *args):

    name = '-'.join([*args])
    file = ctx.out_path / f'{name}{EXT}'

    if ctx.meta and img.width > ADD_CR_ABOVE:
        img = add_copyright_img(img, ctx.meta)

    exif = update_exif(img, desc=ctx.exif_desc, cr_data=ctx.meta)

    print(f'Saving {file} ...')
    img.save(file, exif=exif.tobytes())


def _create_images(img: ImageT,
                   name: str,
                   ctx: SaveContext,
                   sizes: Optional[List[Tuple[str, int]]] = None,
                   simple_resize: bool = False,
                   add_enhanced: bool = False):

    ENH_STRENGTH = 0.3

    images = {}

    def add(i: ImageT, *args):
        _save(ctx, i, *args)
        images[args] = i

    pos = _enhance_pos(img, ENH_STRENGTH)
    add(pos, name)

    # LW resize method works on inverted images, thus we invert, resize, and invert again for the positive

    inv = apply(pos, Curves.invert())
    inv = _enhance_inv(inv, ENH_STRENGTH)
    add(inv, name, INV)

    if not sizes:
        sizes = []
    for s in sizes:
        size_qual, width = s
        assert width > 0
        if width < img.width:
            method = 'simple' if simple_resize else 'lw'
            inv_resized = resize_to_width(inv, width, mode=method)
        else:
            inv_resized = inv.copy()

        add(inv_resized, name, INV, size_qual)
        add(apply(inv_resized, Curves.invert()), name, size_qual)

    if add_enhanced:
        created = list(images.keys())
        for qual in created:
            if INV in qual:
                i_e = _enhance_inv(images[qual], ENH_STRENGTH)
            else:
                i_e = _enhance_pos(images[qual], ENH_STRENGTH)
            new_qual = qual + (ENH,)
            add(i_e, *new_qual)


def proc(img: Union[str, ImageT],
         out_dir: str,
         cut_offset: str,
         cutouts: List[str] = 0,
         simple_resize: bool = False,
         meta: Union[str, Dict] = ''):

    def raise_invalid_type(**kwargs):
        k, v = list(kwargs.items())[0]
        raise ValueError(f'Invalid type for {k}: {type(v)}')

    if meta:
        if isinstance(meta, str):
            meta = load_yaml(meta)
        elif not isinstance(meta, dict):
            raise_invalid_type(copyright_data=meta)
    else:
        meta = None

    if isinstance(img, str):
        print(f'Loading {img} ...')
        src = Image.open(img)
    elif isinstance(img, ImageT):
        src = img
    else:
        raise_invalid_type(source_image=img)
        return

    out_path = _prepare_out_dir(out_dir)

    save_ctx = SaveContext(out_path=out_path,
                           meta=meta,
                           exif_desc='')

    x_offset, y_offset = parse_offset(cut_offset, src.size)

    full = remove_frame(src, int(x_offset), int(y_offset), 1.0)
    _create_images(img=full,
                   name=FULL,
                   ctx=save_ctx,
                   simple_resize=simple_resize,
                   add_enhanced=True)

    sizes = [(MID, MID_WIDTH), (SMALL, SMALL_WIDTH)]

    for i, cr in enumerate(cutouts):
        img = crop(full, cr)
        _create_images(img=img,
                       name=f'c{i+1}',
                       ctx=save_ctx,
                       sizes=sizes,
                       simple_resize=simple_resize,
                       add_enhanced=True)

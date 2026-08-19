#!/usr/bin/env python3

from tempfile import mkstemp
from copy import deepcopy
from datetime import datetime
from typing import Tuple, Dict, Optional
import numpy
from math import floor, ceil
from pathlib import Path
import yaml

from PIL import Image, ImageDraw, ImageFont, ExifTags
from slugify import slugify

ARTIST_TAG = 0x013b
COPYRIGHT_TAG = 0x8298
DATE_TIME_TAG = 0x132
DESCRIPTION_TAG = 0x010e
SOFTWARE_TAG = 0x0131


def load_copyright_data(file: str) -> Dict:

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


def print_meta(img: Image):

    meta = img.getexif()
    for k, v in meta.items():
        print(f'  {k} - {ExifTags.TAGS.get(k, k)}: {v}')


def image_date(img: Image) -> datetime:

    try:
        date_str = img.getexif()[DATE_TIME_TAG]
        return datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
    except Exception:
        return datetime.now()


def image_year(img: Image) -> int:

    return image_date(img).year


def remove_frame(src: Image,
                 o_x: int,
                 o_y: int,
                 scale: float) -> Image:

    W = 0.94
    H = 0.91

    orig_width, orig_height = src.size
    w = int(orig_width * W * scale)
    h = int(orig_height * H * scale)

    print(f"Crop: {orig_width}x{orig_height} -> {w}x{h}")

    return src.crop((o_x, o_y, o_x + w, o_y + h))


def split_image(src: Image) -> Tuple[Image, Image]:

    H_SPLIT = 0.6
    H_SPLIT_2 = 0.57

    width, height = src.size

    top_cropped_height = int(H_SPLIT * height)
    bot_cropped_height = int(H_SPLIT_2 * height)
    img1 = src.crop((0, 0, width, top_cropped_height))
    img2 = src.crop((0, height-bot_cropped_height, width, height))

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


def resize_to_width(img: Image, w: int, mode: str = 'lw') -> Image:

    orig_width, orig_height = img.size

    scale = w / orig_width
    assert scale < 1.0

    if mode == 'lw':
        assert img.mode == 'RGB'
        img_array = numpy.array(img)
        resized_array = luminance_weighted_downscale(img_array, scale)
        resized_array = numpy.clip(resized_array, 0, 255).astype(numpy.uint8)
        return Image.fromarray(resized_array, mode='RGB')
    else:
        return img.resize((w, int(scale * orig_height)))


def add_copyright_img(src: Image, cr_data: Dict) -> Image:

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


def add_copyright_meta(img: Image, desc: str, cr_data: Dict) -> Image.Exif:

    meta = img.getexif()
    meta[SOFTWARE_TAG] = 'github.com/baltth/astro-gen.git'
    if desc:
        meta[DESCRIPTION_TAG] = desc
    if cr_data:
        meta[ARTIST_TAG] = cr_data['author']
        meta[COPYRIGHT_TAG] = copyright_meta(image_year(img), cr_data)

    return meta


def process(src: Image,
            x_offset: int,
            y_offset: int,
            scale: float,
            simple_resize: bool = False,
            split: bool = True,
            cr_data: Optional[Dict] = None) -> Tuple[Image, Image, Optional[Image]]:

    if not cr_data:
        cr_data = {}

    WIDTH = 800

    cropped = remove_frame(src, x_offset, y_offset, scale)

    method = 'orig' if simple_resize else 'lw'

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


def save_image(img: Image, name: str, desc: str, cr_data: Dict) -> str:

    name_as_path = Path(name)
    if name_as_path.is_file():
        for i in range(2, 6):
            s = name_as_path.suffix
            n = name.removesuffix(s)
            maybe_name = f'{n}-{i}{s}'
            if not Path(maybe_name).is_file():
                break
        name = maybe_name

    print(f'Saving to {name} ...')

    name_as_path.parent.mkdir(parents=True, exist_ok=True)
    meta = add_copyright_meta(img, desc, cr_data)
    img.save(name, exif=meta.tobytes())
    return name


def save_object(img: Image,
                dest_dir: str,
                object_name: str,
                date: datetime,
                cr_data: Optional[Dict] = None) -> str:

    if not cr_data:
        cr_data = {}

    name = f'{date.year:04}/' + slugify(f'{object_name}-{date.year:04}{date.month:02}{date.day:02}')
    path_prefix = f'{dest_dir}/' if dest_dir else ''
    saved = save_image(img, name=f'{path_prefix}{name}.jpg', desc=f'Sketch of {object_name}', cr_data=cr_data)
    return saved.removeprefix(path_prefix)


def split_cmd(source_image: str,
              dest: str,
              x_offset: int = 0,
              y_offset: int = 0,
              scale: float = 1.0,
              first_object: str = '',
              second_object: str = '',
              full_page: bool = False,
              date_override: str = '',
              simple: bool = False,
              show: bool = False,
              copyright_file: str = '') -> Dict:

    if copyright_file:
        cr_data = load_copyright_data(copyright_file)
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
                        date=date)
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
                        date=date)
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
                    date=date)
    db_data['cropped_img'] = n

    return db_data


def copyright_cmd(source_image: str,
                  copyright_file: str,
                  out: str = '',
                  show: bool = False):

    cr_data = load_copyright_data(copyright_file)
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

    save_image(img, out_file, '', cr_data)

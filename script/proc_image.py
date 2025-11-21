#!/usr/bin/env python3

import argparse
from tempfile import mkstemp
from copy import deepcopy
from datetime import datetime
from typing import Tuple, Dict, Optional
import numpy
from math import floor, ceil
from PIL import Image, ImageDraw, ImageFont, ExifTags
from slugify import slugify


ARTIST_TAG = 0x013b
COPYRIGHT_TAG = 0x8298
DATE_TIME_TAG = 0x132
DESCRIPTION_TAG = 0x010e
SOFTWARE_TAG = 0x0131

AUTHOR = 'Balazs Toth'
MAIL = 'baltth@gmail.com'


def copyright_text(year: int) -> str:
    assert year >= 2025
    return f'(C) {year}, {AUTHOR}, {MAIL}'


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

    W = 2035 / 2144
    H = 2795 / 3028

    orig_width, orig_height = src.size
    w = int(orig_width * W * scale)
    h = int(orig_height * H * scale)

    print(f"Crop: {orig_width}x{orig_height} -> {w}x{h}")

    return src.crop((o_x, o_y, o_x + w, o_y + h))


def split_image(src: Image) -> Tuple[Image, Image]:

    H_SPLIT = 0.58

    width, height = src.size

    cropped_height = int(H_SPLIT * height)
    img1 = src.crop((0, 0, width, cropped_height))
    img2 = src.crop((0, height-cropped_height, width, height))

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


def add_copyright_img(src: Image) -> Image:

    FONT_SIZE = 12
    TEXT_OFFSET = 6
    TEXT_COLOR = 'dimgray'

    img = deepcopy(src)

    _, height = img.size
    coords = (TEXT_OFFSET, height - TEXT_OFFSET - FONT_SIZE)

    draw = ImageDraw.Draw(img)
    draw.text(coords,
              copyright_text(image_year(img)),
              fill=TEXT_COLOR,
              font=ImageFont.load_default(FONT_SIZE))
    return img


def add_copyright_meta(img: Image, desc: str = '') -> Image.Exif:

    meta = img.getexif()
    meta[ARTIST_TAG] = AUTHOR
    meta[COPYRIGHT_TAG] = copyright_text(image_year(img))
    meta[SOFTWARE_TAG] = 'github.com/baltth/astro.git'
    if desc:
        meta[DESCRIPTION_TAG] = desc

    return meta


def process(src: Image,
            x_offset: int,
            y_offset: int,
            scale: float,
            simple_resize: bool = False,
            split: bool = True) -> Tuple[Image, Image, Optional[Image]]:

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

    return (add_copyright_img(cropped),
            add_copyright_img(img1),
            add_copyright_img(img2) if img2 else None)


def save_image(img: Image, name: str, desc: str = ''):

    meta = add_copyright_meta(img, desc)
    img.save(name, exif=meta.tobytes())


def save_object(img: Image, dest_dir: str, object_name: str, date: Optional[datetime] = None) -> str:

    if not date:
        date = image_date(img)
    name = slugify(f'{object_name}-{date.year:04}{date.month:02}{date.day:02}')
    path_prefix = f'{dest_dir}/' if dest_dir else ''
    save_image(img, name=f'{path_prefix}{name}.jpg', desc=f'Sketch of {object_name}')
    return f'{name}.jpg'


def split_cmd(args) -> Dict:

    src = Image.open(args.source_image)

    print(f'Source image: {args.source_image}')
    print_meta(src)

    cropped, img1, img2 = process(src,
                                  args.x_offset,
                                  args.y_offset,
                                  args.scale,
                                  simple_resize=args.simple,
                                  split=not args.full_page)

    if args.show:
        cropped.show()
        img1.show()
        if img2:
            img2.show()

    date = image_date(src)

    db_data = {}
    db_data['img_date'] = date

    if args.first_object:
        n = save_object(img=img1,
                        dest_dir=args.dest,
                        object_name=args.first_object,
                        date=date)
        db_data['first_name'] = args.first_object
        db_data['first_img'] = n

        if args.second_object == args.first_object:
            args.second_object += ' 2nd'

    if args.second_object:
        assert not args.full_page
        assert img2

        n = save_object(img=img2,
                        dest_dir=args.dest,
                        object_name=args.second_object,
                        date=date)
        db_data['second_name'] = args.first_object
        db_data['second_img'] = n

    if args.first_object and not args.second_object:
        full_name = f'{args.first_object} NA'
    elif args.second_object and not args.first_object:
        full_name = f'NA {args.second_object}'
    else:
        full_name = f'{args.first_object} {args.second_object}'

    n = save_object(img=cropped,
                    dest_dir=args.dest,
                    object_name=full_name,
                    date=date)
    db_data['cropped_img'] = n

    return db_data


def copyright_cmd(args):

    src = Image.open(args.source_image)

    print(f'Source image: {args.source_image}')
    print_meta(src)

    img = add_copyright_img(src)
    if args.show:
        img.show()
    if args.out:
        out_file = args.out
    else:
        _, name = mkstemp(suffix='.jpg')
        out_file = name

    print(f'Saving to {out_file} ...')
    save_image(img, out_file)


def main():

    parser = argparse.ArgumentParser()
    parser.description = 'Split and annotate sketches of the sky'

    cmd = parser.add_subparsers()

    split = cmd.add_parser("split")
    split.add_argument('source_image')
    split.add_argument('-d', '--dest', default='')
    split.add_argument('-x', '--x-offset', type=int, default=0)
    split.add_argument('-y', '--y-offset', type=int, default=0)
    split.add_argument('-s', '--scale', type=float, default=1.0)
    split.add_argument('-o1', '--first-object', default='')
    split.add_argument('-o2', '--second-object', default='')
    split.add_argument('--full-page', action='store_true')
    split.add_argument('-w', '--show', action='store_true')
    split.add_argument('--simple', help='Use simple resize instead of \'luminance weighted\' method',
                       action='store_true')
    split.set_defaults(func=split_cmd)

    cr = cmd.add_parser("copyright")
    cr.add_argument('source_image')
    cr.add_argument('-w', '--show', action='store_true')
    cr.add_argument('-o', '--out')
    cr.set_defaults(func=copyright_cmd)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

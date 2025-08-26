#!/usr/bin/env python3

import argparse
from tempfile import mkstemp
from copy import deepcopy
from datetime import datetime
from typing import Tuple, Dict
from shlex import join as shjoin
import sys

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


def resize_to_width(img: Image, w: int) -> Image:

    orig_width, orig_height = img.size

    scale = w / orig_width

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


def process(src: Image, x_offset: int, y_offset: int, scale: float) -> Tuple[Image, Image, Image]:

    cropped = remove_frame(src, x_offset, y_offset, scale)
    img1, img2 = split_image(cropped)

    WIDTH = 800

    img1 = resize_to_width(img1, WIDTH)
    img2 = resize_to_width(img2, WIDTH)

    return (add_copyright_img(cropped), add_copyright_img(img1), add_copyright_img(img2))


def save_image(img: Image, name: str, desc: str = ''):

    meta = add_copyright_meta(img, desc)
    img.save(name, exif=meta.tobytes())


def save_object(img: Image, dest_dir: str, object_name: str) -> str:

    date = image_date(img)
    name = slugify(f'{object_name}-{date.year:04}{date.month:02}{date.day:02}')
    path_prefix = f'{dest_dir}/' if dest_dir else ''
    save_image(img, name=f'{path_prefix}{name}.jpg', desc=f'Sketch of {object_name}')
    return f'{name}.jpg'


def split_cmd(args) -> Dict:

    src = Image.open(args.source_image)

    print(f'Source image: {args.source_image}')
    print_meta(src)

    cropped, img1, img2 = process(src, args.x_offset, args.y_offset, args.scale)

    if args.show:
        cropped.show()
        img1.show()
        img2.show()

    db_data = {}
    db_data['img_date'] = image_date(src)

    if args.first_object:
        n = save_object(img=img1, dest_dir=args.dest, object_name=args.first_object)
        db_data['first_name'] = args.first_object
        db_data['first_img'] = n

        if args.second_object == args.first_object:
            args.second_object += ' 2nd'

    if args.second_object:
        n = save_object(img=img2, dest_dir=args.dest, object_name=args.second_object)
        db_data['second_name'] = args.first_object
        db_data['second_img'] = n

    if args.second_object and not args.first_object:
        full_name = f'NA {args.second_object}'
    else:
        full_name = f'{args.first_object} {args.second_object}'

    n = save_object(img=cropped,
                    dest_dir=args.dest,
                    object_name=full_name)
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
    split.add_argument('-w', '--show', action='store_true')
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

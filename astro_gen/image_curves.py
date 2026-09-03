#!/usr/bin/env python3

from argparse import ArgumentParser
from typing import Tuple, List, Callable, Optional, Union
from math import sin, sqrt, floor, pi
import numpy as np
from natsort import natsorted
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, ImageChops, ImageDraw
from PIL.Image import Image as ImageT

CURVE_LEN = 256
MAX_LEVEL = CURVE_LEN - 1

# Rec. 709 luminance weights, summing up to exactly 1.0
LUMA_WEIGHTS = (0.2126, 0.7152, 0.0722)

# Luminance below this level fades the gain over to a plain offset,
# see _apply_to_luminance()
GAIN_FADE_LEVEL = 8.0

EPSILON = 1e-6

CurveXY = List[Tuple[float, float]]
CurveFunc = Callable[[float], float]
Curve = Union[CurveXY, CurveFunc]

LookupTable = List[float]

NORMAL_RANGE_TSH = 1.1

INVERT_CURVE = [(0, 255), (255, 0)]


class Curves:

    @staticmethod
    def linear() -> CurveFunc:
        return lambda x: x

    @staticmethod
    def highlights(strength: float) -> CurveFunc:
        assert -1.0 <= strength <= 1.0

        SCALE = 0.2

        def neg_fn(x: float):
            TSH = 0.45
            assert strength < 0
            assert 0 <= x <= 1.0
            if x > TSH:
                val = x + (SCALE * (x - TSH) * strength * Curves._mask(x-TSH))
                return min(val, 1.0)
            return x

        def pos_fn(x: float):
            assert strength >= 0
            assert 0 <= x <= 1.0
            val = x + (SCALE * x * strength * Curves._mask(x))
            return min(val, 1.0)

        return pos_fn if strength >= 0 else neg_fn

    @staticmethod
    def ambient(strength: float) -> CurveFunc:
        assert -1.0 <= strength <= 1.0

        def _fn(x: float) -> float:
            assert 0 <= x <= 1.0
            mod = sin(x * 2 * pi)
            return x + (0.15 * mod * strength * Curves._mask(x))
        return _fn

    @staticmethod
    def shadows(strength: float) -> CurveFunc:
        assert -1.0 <= strength <= 1.0

        SCALE = 0.2
        TSH = 0.5

        def _fn(x: float) -> float:
            assert 0 <= x <= 1.0
            if x >= TSH:
                return x
            # A tight mask over [0, TSH] keeps the black point in place,
            # the effect peaks in the middle of the shadows.
            val = x + (SCALE * TSH * strength * Curves._tight_mask(x / TSH))
            return max(val, 0)

        return _fn

    @staticmethod
    def _mask(x: float) -> float:
        return sqrt(sin(x * pi))

    @staticmethod
    def _tight_mask(x: float) -> float:
        """A narrower mask than _mask(), fading out smoothly at both ends."""
        return sin(x * pi) ** 2

    @staticmethod
    def combine(curve: CurveFunc, *args) -> CurveFunc:
        if not args:
            return curve
        rem = Curves.combine(*args)
        return lambda x: rem(curve(x))


def is_normal_range(v: List) -> bool:
    if not v:
        return False
    if isinstance(v[0], tuple):
        return is_normal_range([p[0] for p in v])
    return all(x < NORMAL_RANGE_TSH for x in v)


def _clamp(min_v: float, val: float, max_v: float) -> float:
    if val < min_v:
        return min_v
    if val > max_v:
        return max_v
    return val


def normalize(lut: LookupTable) -> LookupTable:
    if is_normal_range(lut):
        return lut
    return [_clamp(0, v / CURVE_LEN, 1) for v in lut]


def denormalize(lut: LookupTable) -> LookupTable:
    if is_normal_range(lut):
        return [_clamp(0, floor((v * CURVE_LEN) + 0.5), CURVE_LEN - 1) for v in lut]
    return lut


def _interpol(c: CurveXY, samples: List[float]) -> LookupTable:

    xp = [p[0] for p in c]
    fp = [p[1] for p in c]
    return list(np.interp(x=samples,
                          xp=xp,
                          fp=fp,
                          left=fp[0],
                          right=fp[-1]))


def _sample_range_of(c: CurveXY) -> List[float]:
    if is_normal_range(c):
        return [v / CURVE_LEN for v in range(CURVE_LEN)]
    return [float(v) for v in range(CURVE_LEN)]


def _populate_from_xy(c: CurveXY) -> LookupTable:

    assert 2 <= len(c) <= CURVE_LEN
    x_set = set(p[0] for p in c)
    assert len(x_set) == len(c)

    if len(c) == CURVE_LEN:
        return [v[1] for v in c]

    c = sorted(c)

    return _interpol(c, samples=_sample_range_of(c))


def _populate_from_func(c: CurveFunc) -> LookupTable:
    samples = [v / CURVE_LEN for v in range(CURVE_LEN)]
    return [c(x) for x in samples]


def populate_curve_xy(c: CurveXY) -> CurveXY:
    assert isinstance(c, list)
    return list(zip(_sample_range_of(c), _populate_from_xy(c)))


def populate(c: Curve) -> LookupTable:
    if callable(c):
        return denormalize(_populate_from_func(c))
    return denormalize(_populate_from_xy(c))


def _apply_to_luminance(image: ImageT, lut: LookupTable) -> ImageT:
    """
    Apply the lookup table to the luminance of each pixel and scale
    its channels by the resulting gain. This keeps the R:G:B ratios,
    thus the color balance, which an independent per-channel mapping
    would distort wherever the curve is steep, flat, or clipping.
    """
    if image.mode != 'RGB':
        raise ValueError(f'RGB image is needed, got {image.mode}')

    rgb = np.asarray(image, dtype=np.float32)
    lum = rgb @ np.asarray(LUMA_WEIGHTS, dtype=np.float32)
    target = np.interp(lum,
                       np.arange(CURVE_LEN, dtype=np.float32),
                       np.asarray(lut, dtype=np.float32))

    # Scaling by target/lum blows up in the deepest shadows - a lifted
    # near-black pixel would turn into a saturated one - so below
    # GAIN_FADE_LEVEL the gain is faded over to adding the difference.
    # Both reach the target luminance exactly, as the weights sum to 1.
    gain = np.divide(target, lum, out=np.zeros_like(lum), where=lum > EPSILON)
    scaled = rgb * gain[..., None]
    offset = rgb + (target - lum)[..., None]
    fade = np.clip(lum / GAIN_FADE_LEVEL, 0, 1)[..., None]
    res = (fade * scaled) + ((1 - fade) * offset)

    # A clipping channel would shift the balance again, so desaturate
    # towards the target luminance instead of letting the clamp do it.
    peak = res.max(axis=-1)
    excess = np.maximum(peak - MAX_LEVEL, 0)
    ratio = np.clip(excess / np.maximum(peak - target, EPSILON), 0, 1)
    res += (target[..., None] - res) * ratio[..., None]

    return Image.fromarray(np.clip(res + 0.5, 0, MAX_LEVEL).astype(np.uint8))


def apply(image: ImageT, curve: Curve, per_channel: bool = False) -> ImageT:
    """
    Apply a curve to an image, keeping the color balance of the pixels.
    Pass per_channel=True to map R, G, and B independently, e.g. for
    curves which are not tonal adjustments like an invert.
    """
    lut = populate(curve)
    if per_channel:
        return image.point(lut * 3)  # Apply the same curve to R, G, and B
    return _apply_to_luminance(image, lut)


def invert_image(image: ImageT) -> ImageT:
    return apply(image=image, curve=INVERT_CURVE, per_channel=True)


def annotate_image(image: ImageT, curve: Optional[Curve] = None) -> ImageT:

    lw = min(image.size)
    hist = image.convert(mode='L').histogram()

    img = image.copy().convert(mode='RGB')
    xs = [x * lw / CURVE_LEN for x in range(CURVE_LEN)]

    def line(ys: List[float], color: str):
        draw = ImageDraw.Draw(img)
        xy = list(zip(xs, [lw - y for y in ys]))
        draw.line(xy, width=2, fill=color)

    line([x / 30 for x in hist], color='blue')

    if curve:
        lut = populate(curve)
        lut = [x * img.height / CURVE_LEN for x in lut]
        line(lut, color='red')

    return img


def gradient_image() -> ImageT:

    # Standard deviation of the dithering noise of the generated gradient, in levels
    DITHER_SIGMA = 2.0

    size = (2*CURVE_LEN, 2*CURVE_LEN)
    image = Image.linear_gradient(mode='L').resize(size)
    image = image.transpose(Image.Transpose.ROTATE_90)

    # Gaussian noise is centered at 128, the offset keeps the mean level intact
    noise = Image.effect_noise(size, DITHER_SIGMA)
    image = ImageChops.add(image, noise, offset=-128)

    return image.convert(mode='RGB')


def gen_curve_test_set(inp: Optional[Union[ImageT, str]] = None, out_dir: Optional[str] = None):

    if not inp:
        image = gradient_image()
    elif isinstance(inp, ImageT):
        image = inp
    else:
        image = Image.open(inp)

    if out_dir:
        out_path = Path(out_dir)
        out_path.mkdir(parents=True, exist_ok=True)
    else:
        tmp_dir = TemporaryDirectory(delete=False)
        out_path = Path(tmp_dir.name)

    def _annot_and_save(img, curve, name):
        img = annotate_image(image=img, curve=curve)
        out_file = out_path / f'{name}.jpg'
        img.save(out_path / out_file)

    _annot_and_save(image, Curves.linear(), 'base')

    img_inv = apply(image, INVERT_CURVE, per_channel=True)
    _annot_and_save(img_inv, INVERT_CURVE, 'inv')

    def series(curve_type, name: str, rng: Tuple[float, float, float]):

        start, step, end = rng
        for i, s in enumerate(np.arange(start, end+step, step, dtype=float)):
            s = round(s, 2)
            c = curve_type(s)
            img_amb = apply(image, c)
            name_postfix = f'{i}{s:+1.2f}'
            _annot_and_save(img_amb, c, f'{name}.{name_postfix}')

    series(Curves.ambient, 'ambient', (-1, 0.2, 1))
    series(Curves.highlights, 'highlights', (-1, 0.2, 1))
    series(Curves.shadows, 'shadows', (-1, 0.2, 1))

    print(f'Out directory: {out_path.resolve()}')
    for f in natsorted(out_path.glob(pattern='*.jpg')):
        print(f'    {f.name}')


if __name__ == "__main__":

    parser = ArgumentParser()
    parser.add_argument('-i', '--input', help='Input image, default is a generated gradient')
    parser.add_argument('-o', '--out-dir', help='Output directory, default is a temp dir')
    args = parser.parse_args()

    gen_curve_test_set(inp=args.input, out_dir=args.out_dir)

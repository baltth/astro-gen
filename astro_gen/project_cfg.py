#!/usr/bin/env python3

from pathlib import Path
from typing import Dict, List, Optional
import yaml

from . import project


def load(root: str) -> Dict:

    file = project.meta_file(root)
    if not Path(file).is_file():
        return {}

    with open(file, encoding='utf8') as f:
        data = yaml.safe_load(f)
        assert isinstance(data, dict)
        return data


def _image_cfg(cfg: Optional[Dict]) -> Dict:
    if not cfg:
        return {}
    image_cfg = cfg.get('images', {})
    assert isinstance(image_cfg, dict)
    return image_cfg


def cutouts(cfg: Optional[Dict]) -> List[str]:

    DEFAULT_CUTOUTS = ['100%x100%']

    image_cfg = _image_cfg(cfg)
    if 'cutouts' in image_cfg:
        cuts = image_cfg['cutouts']
    else:
        cuts = DEFAULT_CUTOUTS

    assert isinstance(cuts, list)
    return cuts


def enhance_mask(cfg: Optional[Dict]) -> str:
    return _image_cfg(cfg).get('enhance_mask', '')


def mid_width(cfg: Optional[Dict]) -> int:
    return _image_cfg(cfg).get('mid_width', 800)


def small_width(cfg: Optional[Dict]) -> int:
    return _image_cfg(cfg).get('small_width', 200)

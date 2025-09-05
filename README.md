# astro-gen

Generator for astronomy observation page.

See [astro](https://baltth.github.io/astro)
and its [source](https://github.com/baltth/astro).

> This program is specialized for my site and workflow
> but going to be generalized later. Please contact
> me if you're interested in generating your
> own observation page.

---

### Requirements

- _pyhton3 venv_ with packages
  - `natsort`
  - `pillow`
  - `pyhon-slugify`
  - `requests`
  - `ruamel.yaml==0.18.15`

To fetch data from <astronomyapi.com>:
- register your 'application'
- set the credentials as environment variables:
  - `ASTRONOMYAPI_ID`
  - `ASTRONOMYAPI_SECRET`

...

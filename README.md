# astro-gen

Generator for astronomy observation pages.

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
  - `numpy`
  - `pillow`
  - `pyhon-slugify`
  - `requests`
  - `ruamel.yaml==0.18.15`

To fetch data from <astronomyapi.com>:
- register your 'application'
- set the credentials as environment variables:
  - `ASTRONOMYAPI_ID`
  - `ASTRONOMYAPI_SECRET`

---

## Example project

> An example project is available in `./example`. Copy this to create you own,
> trivially delete all content on demand.

...

## Usage

### Add observations

Assuming
- a project at `path/to/project`,
- observation images
  - `path/to/obs.jgp` and
  - the original scanned image `path/to/scan.jgp`,
- to be cropped with offset _50, 185,_
- about objects _M35_ and _11 Aql_,

run the command

```sh
./script/astro_gen.py path/to/project add -i path/to/obs.jpg -c path/to/scan.jpg -x 50 -y 185 -o1 M35 -o2 '11 Aql'
```

This adds image files to `path/to/project/docs/img` and `path/to/project/docs/scan`.


### Fill observation details

The previous step creates new entries into `path/to/project` files
- `db/objects.yml` for object data
- `db/obs.yml` for the observation details and description
- `db/sketch.yml` for registering the images

Fill the observation details in `db/obs.yml` and modify object data in `db/obs.yml` on demand.


### Regenerate 

Generate Markdown pages with

```sh
./script/regen.py path/to/project
```

This adds or refreshes all `.md` content in `path/to/project/docs`. 


### View the generated site

Setup _Jekyll_ to render the content themed, or use any Markdown renderer to view the raw content.

#### Setup test environment with Jekyll

- install `ruby`
- setup local environment:
  ```sh
  export GEM_HOME=~/.local/ruby/
  export PATH=$PATH:~/.local/ruby/bin
  ```
- `gem install jekyll bundler`
- create or copy a `Gemfile` (`jekyll new dummy`)
  - with extra content
    ```
    gem "github-pages", group: :jekyll_plugins
    gem "jekyll-theme-midnight"
    ```
- run server with `bundle exec jekyll serve` from `path/to/project/docs`
- browse http://localhost:4000/


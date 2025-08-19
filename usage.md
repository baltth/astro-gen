### Add images

```sh
./script/proc_image.py copyright ./orig/scan/20250715014417_002.jpg -o scan/20250715_1.jpg
./script/proc_image.py split ./orig/inv/1000001116.jpg -x 41 -y 160 -o1 "Zeta UMa 80 UMa" -o2 "Kappa Her" -d img/
```

### Setup test environment with Jekyll

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
- run server with `bundle exec jekyll serve` from the root
- browse http://localhost:4000/

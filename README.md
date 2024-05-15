# CliX

An intelligent command line interface for ChimeraX.

## How to use

1. Get the source code.
   1. Get the latest release and unzip it.
      https://github.com/hanjinliu/Chimerax-clix/releases
   2. Clone this repository.
      ```shell
      git clone git+https://github.com/hanjinliu/ChimeraX-clix
      ```
   3. Manually download the contents from the "<> Code" pulldown menu in this page.

2. Install `clix` using ChimeraX built-in command line interface
   ```shell
   devel install "path/to/ChimeraX-clix"
   ```

3. If you want to replace the built-in command line interface with `clix`, open
   `Favorites > Settings...` and define a startup as follows:
   ```shell
   ui tool hide "command line interface"
   ui tool show clix
   ```

## Issues/Requests

If you find a bug, or have some feature requests, feel free to open an issue in this 
GitHub repository, or contact me via [X/Twitter](https://twitter.com/liu_hanjin).

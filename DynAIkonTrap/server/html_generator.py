# Code contained within this file is a heavily modified version of a starting point by glowinthedark - thanks! 
# Original GIST: https://gist.githubusercontent.com/glowinthedark/625eb4caeca12c5aa52778a3b4b0adb4/raw/d245a5c53e935f03b08e528f0b79c66e58823987/generate_directory_index_caddystyle.py
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#
# You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#
# See the License for the specific language governing permissions and limitations under the License.

"""This file contains functions for generating html pages for the DynAikonTrap web viewer. Heavily modifed from the startpoint provided over at: https://gist.githubusercontent.com/glowinthedark/625eb4caeca12c5aa52778a3b4b0adb4/raw/d245a5c53e935f03b08e528f0b79c66e58823987/generate_directory_index_caddystyle.py"""

from os import path, getcwd, stat
from glob import glob
from urllib.parse import quote
from datetime import datetime as dt

from DynAIkonTrap.logging import get_logger

logger = get_logger(__name__)

MAIN_PAGE = 'index.html'
FOV_PAGE = 'html/fov.html'
CSS_DIR = 'assets/bootstrap-3.3.5/css'
SHELL_PAGE = 'html/shell.html'

SVG_IMAGES = {
    #go back svg image, instructions from: https://icons.getbootstrap.com/icons/arrow-return-left/
    "go-back-sprite" : {"d":"\"M4.854 1.146a.5.5 0 0 0-.708 0l-4 4a.5.5 0 1 0 .708.708L4 2.707V12.5A2.5 2.5 0 0 0 6.5 15h8a.5.5 0 0 0 0-1h-8A1.5 1.5 0 0 1 5 12.5V2.707l3.146 3.147a.5.5 0 1 0 .708-.708l-4-4z\"", "fill":"\"black\""},
    #folder svg image, instructions from: https://icons.getbootstrap.com/icons/folder-fill/
    "folder-sprite" : {"d": "\"M9.828 3h3.982a2 2 0 0 1 1.992 2.181l-.637 7A2 2 0 0 1 13.174 14H2.825a2 2 0 0 1-1.991-1.819l-.637-7a1.99 1.99 0 0 1 .342-1.31L.5 3a2 2 0 0 1 2-2h3.672a2 2 0 0 1 1.414.586l.828.828A2 2 0 0 0 9.828 3zm-8.322.12C1.72 3.042 1.95 3 2.19 3h5.396l-.707-.707A1 1 0 0 0 6.172 2H2.5a1 1 0 0 0-1 .981l.006.139z\"" , "fill":"\"orange\""},
    #video svg image, instructions from: https://icons.getbootstrap.com/icons/camera-video-fill/
    "video-sprite" : {"d": "\"M0 5a2 2 0 0 1 2-2h7.5a2 2 0 0 1 1.983 1.738l3.11-1.382A1 1 0 0 1 16 4.269v7.462a1 1 0 0 1-1.406.913l-3.111-1.382A2 2 0 0 1 9.5 13H2a2 2 0 0 1-2-2V5z\"", "fill":"\"green\""},
    #jpg/png svg image, instructions from: https://icons.getbootstrap.com/icons/card-image/
    "image-sprite" : {"d1": "\"M6.002 5.5a1.5 1.5 0 1 1-3 0 1.5 1.5 0 0 1 3 0z\"",
                      "d2": "\"M1.5 2A1.5 1.5 0 0 0 0 3.5v9A1.5 1.5 0 0 0 1.5 14h13a1.5 1.5 0 0 0 1.5-1.5v-9A1.5 1.5 0 0 0 14.5 2h-13zm13 1a.5.5 0 0 1 .5.5v6l-3.775-1.947a.5.5 0 0 0-.577.093l-3.71 3.71-2.66-1.772a.5.5 0 0 0-.63.062L1.002 12v.54A.505.505 0 0 1 1 12.5v-9a.5.5 0 0 1 .5-.5h13z\"",
                      "fill":"\"green\""},
    #file svg image, instructions from: https://icons.getbootstrap.com/icons/file-earmark/
    "file-sprite" : {"d": "\"M14 4.5V14a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V2a2 2 0 0 1 2-2h5.5L14 4.5zm-3 0A1.5 1.5 0 0 1 9.5 3V1H4a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V4.5h-2z\"", "fill":"\"black\""}
}

def make_fov_page():
    """ Creates the HTML for the page to view camera's current field of view, this is saved to a file, `html/fov.html` """
    fov_path = path.join(getcwd(), FOV_PAGE)
    try:
        with open(fov_path, 'w') as fov_file:
            fov_file.write(
                f"""{make_head(path.dirname(fov_path))}
                <body> 
                <div class="d-flex justify-content-center">
                <img src="camera-fov.jpg" class="img-responsive" alt="Responsive image">
                </div>
                <div class="container-fluid">
                <button type="button" class="btn btn-primary btn-lg btn-block" onClick="window.location.reload();">Refresh FOV...</button>
                </div>
                </body>
                """ 
            )
    except OSError as e:
        logger.error('Cannot write file {}: {}'.format(fov_path, e))
        return

def make_shell_page(ip_addr, port):
    shell_path = path.join(getcwd(), SHELL_PAGE)
    try:
        with open(shell_path, 'w') as fov_file:
            fov_file.write(
                f"""{make_head(path.dirname(shell_path))}
                <body> 
                <div class="d-flex justify-content-center">
                <iframe src="https://{ip_addr}:{port}/" style="position:fixed; top:0; left:0; bottom:0; right:0; width:100%; height:100%; border:none; margin:0; padding:0; overflow:hidden; z-index:999999;">
                    Your browser doesn't support iframes
                </iframe>
                </div>
                </body>
                """ 
            )
    except OSError as e:
        logger.error('Cannot write file {}: {}'.format(shell_path, e))
        return



def make_head(dir) -> str:
    """ Creates and returns the header html for served pages, includes bootstrap styling. """
    style_path = path.relpath(CSS_DIR, dir)
    return f"""
    <head>
        <meta charset="utf-8">
        <meta http-equiv="X-UA-Compatible" content="IE=edge" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="{style_path}/bootstrap.min.css" />
        <link rel="stylesheet" href="{style_path}/bootstrap-theme.min.css" />
    </head>
    """

def make_main_page(top_dir, output_log):
    """ Creates the html for the main page and writes this to a file, `index.html` """
    index_path = path.join(getcwd(), MAIN_PAGE)
    try:
        with open(index_path, 'w') as index_file:
            index_file.write(f"""<!DOCTYPE html>
            <html>
            {make_head(getcwd())}
            <body>
            <div class="container-fluid">
            <h1>DynAikonTrap Web Viewer</h1>
            <a href="{top_dir}" class="btn btn-primary btn-block" role="button">Check Observations</a>
            <br/>
            <a href="{output_log}" class="btn btn-primary btn-block" role="button">View the System Log</a>
            <br/>
            <a href="{FOV_PAGE}" class="btn btn-primary btn-block" role="button">Check the Camera FOV</a>
            <br/>
            <a href="{SHELL_PAGE}" class="btn btn-primary btn-block" role="button">Access the shell</a>
            </div>
            </body>
            """
        )
    except OSError as e:
        logger.error('Cannot write file {}: {}'.format(index_path, e))
        return
def make_sprites():
    """Creates html code for loading svg sprites used, this is returned as a string"""
    return f"""
        <svg version="1.1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" height="0" width="0" style="position: absolute;">
        <defs>
            <g id="file-back">
                <path d={SVG_IMAGES["go-back-sprite"]["d"]} fill={SVG_IMAGES["go-back-sprite"]["fill"]}/>
            </g>
            <g id="folder">
                <path d={SVG_IMAGES["folder-sprite"]["d"]} fill={SVG_IMAGES["folder-sprite"]["fill"]}/>
            </g>
            <g id="video-file">
                <path d={SVG_IMAGES["video-sprite"]["d"]} fill={SVG_IMAGES["video-sprite"]["fill"]}/>
            </g>
            <g id="image-file">
                <path d={SVG_IMAGES["image-sprite"]["d1"]} fill={SVG_IMAGES["image-sprite"]["fill"]}/>
                <path d={SVG_IMAGES["image-sprite"]["d2"]} fill={SVG_IMAGES["image-sprite"]["fill"]}/>
            </g>
            <g id="file">
                <path d={SVG_IMAGES["file-sprite"]["d"]} fill={SVG_IMAGES["file-sprite"]["fill"]}/>
            </g>
        </defs>
        </svg>
    """

def process_dir(path_top_dir):
    """Make the html for a serving a directory and its nested members"""

    index_path = path.join(path_top_dir, 'index.html')

    try:
        index_file = open(index_path, 'w')
        index_file.write(f"""<!DOCTYPE html>
        <html>
        {make_head(path_top_dir)}
        <body>
            {make_sprites()}
        <header>
        <div class="container-fluid">
            <h1>{path_top_dir}</h1> 
            </div>
                </header>
                <main>
                <div class="h-100 d-flex align-items-center justify-content-center">
                <div class="container-fluid">
                <div class="table-responsive">
                    <table class="table table-bordered table-sm table-striped m-10px">
                    <thead>
                        <tr>
                        <th>Name</th>
                        <th>Size</th>
                        <th>Modified class="hideable"</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr class="clickable">
                            <td><a href=".."><svg width="1.5em" height="1em" version="1.1" viewBox="0 1 15 15"><use xlink:href="#file-back"></use></svg>
                            <span class="goup">..</span></a></td>
                            <td>&mdash;</td>
                             <td class="hideable">&mdash;</td>
                        </tr>
        """)
    except OSError as e:
        logger.error('Cannot create file {}. {}'.format(index_path, e))
        return

    # sort enties by name, dirs first, files after
    sorted_entries = sorted(glob(path.join(path_top_dir, '*')), key=lambda p: (path.isfile(p), path.basename(p)))

    for entry in sorted_entries:
        # Skip dotfiles, symlinks and html files
        if path.basename(entry).startswith('.') or path.islink(entry) or path.splitext(entry)[1] == ".html":
            continue
        
        # Recurse if entry is directory
        if path.isdir(entry):
            process_dir(entry)


        size_bytes = -1  # is a folder
        size_pretty = '&mdash;'
        last_modified = '-'
        last_modified_human_readable = '-'
        last_modified_iso = ''
        try:
            if path.isfile(entry):
                size_bytes = stat(entry).st_size
                size_pretty = pretty_size(size_bytes)

            if path.isdir(entry) or path.isfile(entry):
                last_modified = dt.fromtimestamp(stat(entry).st_mtime).replace(microsecond=0)
                last_modified_iso = last_modified.isoformat()
                last_modified_human_readable = last_modified.strftime("%c")

        except Exception as e:
            print('ERROR accessing file name:', e, entry)
            continue

        entry_name = path.basename(entry)
        if path.isdir(entry):
            entry_type = "folder"
            entry_name = path.join(entry_name, '')
        elif path.splitext(entry_name)[1] in [".jpg", ".jpeg", ".png"]:
            entry_type = "image-file"
        elif path.splitext(entry_name)[1] in [".mp4", '.mpeg', ".avi"]:
            entry_type = "video-file"
        else:
            entry_type = "file"

        index_file.write(f"""
        <tr class="file">
            <td>
                <a href="{quote(entry_name)}">
                    <svg width="1.5em" height="1em" version="1.1" viewBox="0 1 13 13"><use xlink:href="#{entry_type}"></use></svg>
                    <span class="name">{path.basename(entry)}</span>
                </a>
            </td>
            <td data-order="{size_bytes}">{size_pretty}</td>
            <td class="hideable"><time datetime="{last_modified_iso}">{last_modified_human_readable}</time></td>
        </tr>
    """)

    index_file.write("""
    </tbody>
    </table>
    </div>
    </div>
    </div>
    </main>
    </body>
    </html>""")
    if index_file:
        index_file.close()


# bytes pretty-printing
UNITS_MAPPING = [
    (1024 ** 5, ' PB'),
    (1024 ** 4, ' TB'),
    (1024 ** 3, ' GB'),
    (1024 ** 2, ' MB'),
    (1024 ** 1, ' KB'),
    (1024 ** 0, (' byte', ' bytes')),
]

def pretty_size(bytes, units=UNITS_MAPPING):
    """Human-readable file sizes.
    ripped from https://pypi.python.org/pypi/hurry.filesize/
    """
    for factor, suffix in units:
        if bytes >= factor:
            break
    amount = int(bytes / factor)

    if isinstance(suffix, tuple):
        singular, multiple = suffix
        if amount == 1:
            suffix = singular
        else:
            suffix = multiple
    return str(amount) + suffix


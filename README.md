Quick and dirty python script to modify svg files. The SVG images I create are generally with Inkscape, so it may not work for any SVG. 


usage: modify_svg.py [-h] -i INPUT_FILE [-o OUTPUT_FILE] [--theme THEME]
                     [--force-fill]

Modify fill and stroke colors in the <style> section of an SVG file.

options:
  -h, --help            show this help message and exit
  -i INPUT_FILE, --input_file INPUT_FILE
                        Path to the SVG file
  -o OUTPUT_FILE, --output_file OUTPUT_FILE
                        Output path to the SVG file. If not provided, will
                        modify the input file inplace.
  --theme THEME         Theme to use
  --force-fill

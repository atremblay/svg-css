import argparse
import ipdb
import os
import configparser
from typing import Any
import re
from lxml import etree


class Attribute:
    def __init__(self):
        self.is_set: bool = False
        self.value: str | Any | None = None


def parse_args():
    parser = argparse.ArgumentParser(
        description="Modify fill and stroke colors in the <style> section of an SVG file."
    )
    parser.add_argument(
        "-i", "--input_file", type=str, required=True, help="Path to the SVG file"
    )
    parser.add_argument(
        "-o",
        "--output_file",
        type=str,
        required=False,
        default="",
        help="Output path to the SVG file. If not provided, will modify the input file inplace.",
    )
    parser.add_argument("--theme", type=str, help="Theme to use")
    parser.add_argument("--force-fill", default=False, action='store_true')
    return parser.parse_args()


def load_file(svg_path):
    return etree.parse(svg_path)

def get_namespace_details(element):
    # Extracting namespace and prefix from the root element
    namespace_match = re.match(r'\{.*\}', element.tag)
    namespace_uri = namespace_match.group(0) if namespace_match else ''
    prefix = ''
    for ns_prefix, ns_uri in element.nsmap.items():
        if ns_uri == namespace_uri.strip('{}'):
            prefix = ns_prefix
            break
    return namespace_uri, prefix

def get_style_element(tree):
    root = tree.getroot()
    namespace_uri, _ = get_namespace_details(root)
    # Define the style tag with namespace prefix if it exists
    style_tag = f"{namespace_uri}style" if namespace_uri != "" else "style"

    # Find or create the <style> element
    style_element = root.find(style_tag)
    if style_element is None:
        # Create a new <style> element if it doesn't exist
        style_element = etree.Element(style_tag, type="text/css")
        style_element.text = ""
        root.insert(0, style_element)

    return style_element


def update_svg_style(tree, new_colors):
    """
    Updates the SVG style section with new colors.

    :param svg_style: A string containing the style section of the SVG file.
    :param new_colors: A dictionary of colors in the format {'color_name': 'rgb_value'}.
    :return: Updated style section as a string.
    """
    style_element = get_style_element(tree)

    style_content: str = str(style_element.text)

    # Regular expression to match the fill and stroke classes
    css_pattern = r".(?P<rule_type>(fill|stroke))-(?P<color_name>[a-zA-Z0-9]+) {(\1):#(?P<color>[a-fA-F0-9]{3}([a-fA-F0-9]{3})?);}"

    # Find all CSS rules
    css_rules = re.finditer(css_pattern, style_content)

    # Update existing CSS rules and keep track of which colors are updated
    updated_colors = set()
    for color_match in css_rules:
        color_match = color_match.groupdict()
        color_name = color_match['color_name']
        rule_type = color_match['rule_type']
        if color_name in new_colors:
            new_color = new_colors[color_name]
            style_content = re.sub(
                f".{rule_type}-{color_name} {{\1:#([a-fA-F0-9]{3}([a-fA-F0-9]{3})?);}}",
                f".{rule_type}-{color_name} {{{rule_type}:{new_color};}}",
                style_content,
            )
            updated_colors.add(color_name)

    # Add new CSS rules for colors not already in the style section
    for color_name, color_value in new_colors.items():
        if color_name not in updated_colors:
            style_content += f"\n        .fill-{color_name} {{fill:{color_value};}}"
            style_content += f"\n        .stroke-{color_name} {{stroke:{color_value};}}"

    style_element.text = style_content

    return tree

def replace_color(tree, color_mapping):
    """
    Replace fill and stroke colors with corresponding CSS classes in an SVG file.
    Also handles fill and stroke attributes within 'style' attribute strings.

    Args:
    svg_path (str): Path to the SVG file.
    """
    root = tree.getroot()


    # Function to modify style attribute
    def modify_style_attribute(style_attr, fill_attr, stroke_attr):
        updated_style = []
        style_attr = style_attr.strip()
        if style_attr == "":
            return ""
        for style in style_attr.split(";"):
            attr, value = style.split(":")
            attr = attr.strip()
            value = value.strip()
            if attr == "fill" and value in color_mapping:
                fill_attr.is_set = True
                if value != "none":
                    fill_attr.value = value


            elif attr == "stroke" and value in color_mapping:
                stroke_attr.is_set = True
                if value != "none":
                    stroke_attr.value = value

            else:
                updated_style.append(style)
        return ";".join(updated_style)

    # Iterate through all elements and replace fill and stroke attributes
    for element in root.iter():
        fill_attr = Attribute()
        stroke_attr = Attribute()
        if "style" in element.attrib:
            new_style = modify_style_attribute(element.attrib["style"], fill_attr, stroke_attr)
            element.set("style", new_style)

        if "fill" in element.attrib and not fill_attr.is_set:
            fill_attr.is_set = True
            fill_attr.value = element.attrib["fill"]

        if "stroke" in element.attrib and not stroke_attr.is_set:
            stroke_attr.is_set = True
            stroke_attr.value = element.attrib["stroke"]
        
        if (classes := element.get("class")) is None:
            classes = set()
        else:
            classes = set([c.strip() for c in classes.split(" ")])
        if fill_attr.is_set  and fill_attr.value in color_mapping:
            classes.add(f"fill-{color_mapping[fill_attr.value]}")
            if 'fill' in element.attrib:
                del element.attrib["fill"]
        if stroke_attr.is_set and stroke_attr.value in color_mapping:
            classes.add(f"stroke-{color_mapping[stroke_attr.value]}")
            if 'stroke' in element.attrib:
                del element.attrib["stroke"]
        if len(classes) > 0:
            element.set("class", " ".join(classes).strip())

def find_element_with_id(tree, element_id):
    root = tree.getroot()
    return root.find(f".//*[@id='{element_id}']")

def deal_with_markers(tree, force_fill=False):
    # marker-start:url(#marker49)
    root = tree.getroot()
    pattern = r"marker-(start|end|mid):url\(#(?P<marker_id>.*)\)"
    regex = re.compile(pattern)

    for element in root.iter():
        if "style" in element.attrib:
            for style in element.attrib['style'].split(';'):
                if (result := regex.match(style.strip())) is not None and (classes := element.get("class")) is not None:
                    classes = [c for c in classes.split(" ") if c.startswith('fill') or c.startswith('stroke')]
                    marker_id = result.groupdict()['marker_id']
                    marker_element = find_element_with_id(tree, marker_id)
                    if (marker_classes := marker_element.get("class")) is None:
                        marker_classes = set()
                    else:
                        marker_classes = set([c.strip() for c in marker_classes.split(" ")])

                    marker_classes.update(classes)
                    if force_fill and len(classes) > 0:
                        color = list(classes)[0].split('-')[1]
                        marker_classes.add(f'fill-{color}')
                    if len(marker_classes) > 0:
                        marker_element.set("class", " ".join(marker_classes).strip())



def get_file_path(filename):
    current_file_path = os.path.abspath(__file__)
    current_directory = os.path.dirname(current_file_path)
    return os.path.join(current_directory, filename)


def load_theme_colors(theme = None) -> dict:
    themes_file = get_file_path('themes.ini')
    config = configparser.ConfigParser()
    config.read(themes_file)

    if theme is not None and theme not in config:
        raise ValueError(f"Theme {theme} not supported")

    if theme is not None:
        return {key: f"#{value}" for key, value in config[theme].items()}

    color_mapping = {}

    for theme in config:
        color_mapping[theme] = {key: f"#{value}" for key, value in config[theme].items()}
    return color_mapping

def load_color_mapping() -> dict:
    themes_file = get_file_path('color_mapping.ini')
    config = configparser.ConfigParser()
    config.read(themes_file)

    color_mapping = dict(config['color.mapping'])
    # Get mapping from theme file 
    theme_colors = load_theme_colors(theme=None)
    for theme in theme_colors:
        color_mapping.update({f"#{value}":key  for key, value in theme_colors[theme].items()})
    return color_mapping


if __name__ == "__main__":
    with ipdb.launch_ipdb_on_exception():
        args = parse_args()

        # Replace colors with classes in the SVG file
        tree = load_file(args.input_file)
        theme_colors = load_theme_colors(args.theme)
        color_mapping = load_color_mapping()
        tree = update_svg_style(tree, theme_colors)
        replace_color(tree, color_mapping)
        deal_with_markers(tree, args.force_fill)

        # Modify the SVG file
        try:
            tree.write(
                args.output_file if args.output_file != "" else args.input_file,
            )
        except Exception as e:
            print(f"Error: {e}")

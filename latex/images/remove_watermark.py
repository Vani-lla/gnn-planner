import os
import sys
import xml.etree.ElementTree as ET

def clear_vp_text(svg_path):
    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()

        # SVG namespace handling
        ns = {'svg': 'http://www.w3.org/2000/svg'}
        ET.register_namespace('', ns['svg'])

        # Find all <g> elements
        for g in root.findall('.//{http://www.w3.org/2000/svg}g'):
            # Find text elements inside the group
            texts = g.findall('.//{http://www.w3.org/2000/svg}text')

            # Count how many contain "Visual Paradigm Standard"
            vp_texts = [
                t for t in texts
                if (t.text or "").strip().find("Visual Paradigm Standard") != -1
            ]

            if len(vp_texts) > 1:
                # We found the target <g>; clear all its <text> content
                for t in texts:
                    if "Visual Paradigm Standard" in t.text:
                        t.text = ""

                tree.write(svg_path, encoding="utf-8", xml_declaration=True)
                print(f"Cleared text in <g> for: {svg_path}")
                return

        print(f"No matching <g> found in: {svg_path}")

    except Exception as e:
        print(f"Error processing {svg_path}: {e}")


def process_directory(directory):
    if not os.path.isdir(directory):
        print("Not a valid directory:", directory)
        return

    for filename in os.listdir(directory):
        if filename.lower().endswith(".svg"):
            full_path = os.path.join(directory, filename)
            clear_vp_text(full_path)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <directory>")
        sys.exit(1)

    process_directory(sys.argv[1])

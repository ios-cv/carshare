import sys

def replace_placeholder(html_file, svg_file, output_file):
    try:
        # Read the HTML file
        with open(html_file, 'r', encoding='utf-8') as html:
            html_content = html.read()
        
        # Read the SVG file
        with open(svg_file, 'r', encoding='utf-8') as svg:
            svg_content = svg.read()
        
        # Replace the placeholder with the SVG content
        updated_html = html_content.replace('PLACE_HOLDER', svg_content)
        
        # Write the updated HTML to a new file
        with open(output_file, 'w', encoding='utf-8') as output:
            output.write(updated_html)
        
        print(f"Updated HTML file has been saved to {output_file}.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Example usage:
# replace_placeholder('index.html', 'graphic.svg', 'updated_index.html')

# If running from the command line:
if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python script.py <html_file> <svg_file> <output_file>")
    else:
        replace_placeholder(sys.argv[1], sys.argv[2], sys.argv[3])

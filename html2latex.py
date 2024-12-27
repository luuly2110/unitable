import argparse
import os
from bs4 import BeautifulSoup

def escape_latex(text):
    """
    Escapes LaTeX special characters in the given text.

    Args:
        text (str): The text to escape.

    Returns:
        str: The escaped text.
    """
    replacements = {
        '\\': r'\textbackslash{}',
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
    }
    for key, value in replacements.items():
        text = text.replace(key, value)
    return text

def parse_table(table):
    """
    Parses an HTML table and returns a list of rows, where each row is a list of cell dictionaries.

    Each cell dictionary contains:
        - 'text': The cell text
        - 'colspan': Number of columns to span
        - 'rowspan': Number of rows to span
    """
    rows = []
    for row in table.find_all("tr"):
        parsed_row = []
        for cell in row.find_all(["td", "th"]):
            # Use separator=' ' so that <br> or other tags become spaces rather than concatenated text
            cell_text = escape_latex(cell.get_text(separator=' ', strip=True))
            colspan = int(cell.get("colspan", 1))
            rowspan = int(cell.get("rowspan", 1))
            parsed_row.append({
                "text": cell_text,
                "colspan": colspan,
                "rowspan": rowspan
            })
        rows.append(parsed_row)
    return rows

def html_table_to_latex(html_content, output_tex_file):
    """
    Convert HTML tables to LaTeX tables and save them to a file.

    Args:
        html_content (str): HTML content containing tables.
        output_tex_file (str): Path to the output LaTeX file.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    tables = soup.find_all("table")

    if not tables:
        print("No tables found in the HTML content.")
        return

    # Start the LaTeX document with necessary packages
    latex_code = r"""\documentclass{article}
\usepackage[utf8]{inputenc}
\usepackage{hyperref}
\usepackage{graphicx}
\usepackage{float}
\usepackage[margin=1in]{geometry}
\usepackage{longtable}
\usepackage{multirow}
\usepackage{array}
\usepackage{caption}  % for \captionof
\renewcommand{\arraystretch}{1.2}
\begin{document}
"""

    # Percentage of \textwidth the table will occupy
    TOTAL_WIDTH_PERCENT = 0.95

    for idx, table in enumerate(tables, 1):
        latex_code += "\n"

        # Optional: Add caption and label if available
        caption = table.find("caption")
        if caption:
            caption_text = escape_latex(caption.get_text(separator=' ', strip=True))
            latex_code += f"\\captionof{{table}}{{{caption_text}}}\n"
            latex_code += f"\\label{{tab:table{idx}}}\n"

        # Parse the table into rows and cells
        parsed_rows = parse_table(table)

        if not parsed_rows:
            print(f"Warning: Table {idx} has no rows.")
            continue

        # Separate header and body (if <thead> exists)
        thead = table.find("thead")
        if thead:
            header_rows = parse_table(thead)
            body_rows = parsed_rows[len(header_rows):]
        else:
            # Assume first row is header if <thead> is not present
            header_rows = [parsed_rows[0]]
            body_rows = parsed_rows[1:]

        # Determine the number of columns based on the first row of headers
        num_columns = 0
        for cell in header_rows[0]:
            num_columns += cell['colspan']

        # Compute column width based on the number of columns
        # Each column: p{(TOTAL_WIDTH_PERCENT / num_columns)\textwidth}
        column_width = TOTAL_WIDTH_PERCENT / num_columns

        # Build the column format string using the 'p' column type without vertical lines
        column_format = " ".join([f"p{{{column_width:.3f}\\textwidth}}" for _ in range(num_columns)])

        # Begin longtable without vertical lines
        latex_code += (
            r"\setlength\LTleft{0pt}" + "\n"  # no extra left indent
            r"\setlength\LTright{0pt}" + "\n"  # no extra right indent
            r"\begin{longtable}{" + column_format + "}\n"
            r"\hline" + "\n"  # Top horizontal line
        )

        def row_to_latex(row):
            """
            Convert a single row (list of cell dicts) to LaTeX, handling colspan and rowspan.
            """
            row_latex = ""
            for cell in row:
                if cell['colspan'] > 1:
                    row_latex += f"\\multicolumn{{{cell['colspan']}}}{{c}}{{{cell['text']}}} & "
                elif cell['rowspan'] > 1:
                    # Basic \multirow example (no advanced row offset handling)
                    row_latex += f"\\multirow{{{cell['rowspan']}}}{{*}}{{{cell['text']}}} & "
                else:
                    row_latex += f"{cell['text']} & "
            return row_latex.rstrip(" & ") + r" \\" + "\n"

        # -- Header rows --
        for row_num, row in enumerate(header_rows):
            latex_code += row_to_latex(row)
            # Add \hline between header rows if there are multiple
            if row_num < len(header_rows) - 1:
                latex_code += r"\hline" + "\n"

        # The 'first head' is what appears at the top of the table on the first page
        latex_code += r"\endfirsthead" + "\n"
        latex_code += r"\hline" + "\n"

        # The 'head' is repeated on every subsequent page
        for row in header_rows:
            latex_code += row_to_latex(row)
            latex_code += r"\hline" + "\n"
        latex_code += r"\endhead" + "\n"

        # The 'foot' is placed at the bottom of each page
        latex_code += r"\endfoot" + "\n"

        # Add body rows with \hline between them
        for row_num, row in enumerate(body_rows):
            latex_code += row_to_latex(row)
            # Add \hline between rows except after the last row
            if row_num < len(body_rows) - 1:
                latex_code += r"\hline" + "\n"

        # Add the final horizontal line before ending the table
        latex_code += r"\hline" + "\n"

        # End the longtable environment
        latex_code += r"\end{longtable}" + "\n"

    # End the LaTeX document
    latex_code += r"\end{document}"

    # Write the LaTeX code to the output file
    with open(output_tex_file, "w", encoding="utf-8") as f:
        f.write(latex_code)

    print(f"LaTeX tables have been saved to {output_tex_file}")

def main():
    parser = argparse.ArgumentParser(
        description="Convert HTML tables (including those with colspan) to LaTeX longtable environments, "
                    "remove vertical lines, and ensure they fit within page margins."
    )
    parser.add_argument("input_html", help="Path to the input HTML file.")
    parser.add_argument("output_tex", nargs='?', default="output.tex",
                        help="Path to the output LaTeX file (default: output.tex).")
    args = parser.parse_args()

    input_html = args.input_html
    output_tex = args.output_tex

    if not os.path.isfile(input_html):
        print(f"Error: The file '{input_html}' does not exist.")
        return

    with open(input_html, 'r', encoding="utf-8") as file:
        html_content = file.read()

    if not html_content.strip():
        print("Error: The input HTML file is empty.")
        return

    html_table_to_latex(html_content, output_tex)

if __name__ == "__main__":
    main()

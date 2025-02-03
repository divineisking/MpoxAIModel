"""
A modular script for extracting and processing data from multiple PDF reports,
adapting to several formats while ensuring that:
 • Any section containing cumulative data for multiple years is skipped.
 • Data from multiweek reports is retained and the week column reflects the range (e.g., "21-24").
 • For each report (identified by its week and year), either:
      - A state-by-state breakdown is captured (each of Nigeria's 36 states plus FCT; missing states get zero),
      - OR, if no specific state breakdown is provided, a single overall cumulative row is output.
 • When a state's data is provided as a percentage (e.g., "Abia (20%)"), its count is computed from the overall total.
 • If the week number cannot be determined from the text, it falls back to using the last number in the file name.
 • Only valid records (with raw counts or computed counts) are written to the CSV.
This script uses pdfminer.six for text extraction, regex for pattern matching, and CSV for output.
"""

import re
import csv
import os
import logging
from pdfminer.high_level import extract_text

# ======================
# Setup Logging
# ======================
logging.basicConfig(
    filename='pdf_parser.log',
    level=logging.INFO,
    format='%(asctime)s:%(levelname)s:%(message)s'
)

# ======================
# Global Constants
# ======================
# List of Nigeria's 36 states plus the Federal Capital Territory.
NIGERIA_STATES = [
    "Abia", "Adamawa", "Akwa Ibom", "Anambra", "Bauchi", "Bayelsa", "Benue", "Borno",
    "Cross River", "Delta", "Ebonyi", "Edo", "Ekiti", "Enugu", "Gombe", "Imo", "Jigawa",
    "Kaduna", "Kano", "Katsina", "Kebbi", "Kogi", "Kwara", "Lagos", "Nasarawa", "Niger",
    "Ogun", "Ondo", "Osun", "Oyo", "Plateau", "Rivers", "Sokoto", "Taraba", "Yobe",
    "Zamfara", "FCT"
]

# ======================
# Module 1: PDF Extraction
# ======================
def extract_text_from_pdf(file_path):
    """
    Extract text from the PDF at file_path using pdfminer.six.
    Returns the full text as a string, or None if extraction fails.
    """
    try:
        text = extract_text(file_path)
        logging.info(f"Successfully extracted text from {file_path}")
        return text
    except Exception as e:
        logging.error(f"Error extracting text from {file_path}: {e}")
        return None

# ======================
# Module 2: Report-Level Identification and Metadata Extraction
# ======================
def detect_cumulative_multiyear(text_segment):
    """
    Detect if a text segment includes cumulative data for multiple years.
    Uses heuristics such as the presence of the word 'cumulative' alongside multiple distinct years.
    Returns True if such data is detected in the segment, False otherwise.
    """
    pattern = re.compile(r'cumulative.*?(20\d{2})', re.IGNORECASE | re.DOTALL)
    matches = pattern.findall(text_segment)
    if matches and len(set(matches)) > 1:
        return True
    return False

def extract_year(text):
    """
    Extract a 4-digit year (e.g., 2023) from the text.
    Returns the first occurrence of a year, or an empty string if not found.
    """
    year_pattern = re.compile(r'(20\d{2})')
    match = year_pattern.search(text)
    if match:
        return match.group(1)
    return ''

def extract_week_info(text):
    """
    Extract week information from the text.
    Looks for patterns like "epi week: 22", "week 6", or "weeks 13-16".
    Returns the extracted week or week range as a string, or "Unknown" if not found.
    """
    week_pattern = re.compile(r'week\s*[:\-]?\s*(\d+(?:\s*-\s*\d+)?)', re.IGNORECASE)
    match = week_pattern.search(text)
    if match:
        return match.group(1).strip()
    # Fallback: try "epi week"
    epi_pattern = re.compile(r'epi\s*week\s*[:\-]?\s*(\d+(?:\s*-\s*\d+)?)', re.IGNORECASE)
    match = epi_pattern.search(text)
    if match:
        return match.group(1).strip()
    return 'Unknown'

# ======================
# Module 3: Highlighted Data Parsing
# ======================
def parse_highlighted_section(text, case_type):
    """
    Parse a highlighted section for a given case type ("suspected" or "confirmed").
    Looks for narrative text such as:
      "In week X, the number of new suspected cases is Y, ... reported from ... – Lagos (9), Ogun (3), ... and Oyo (1)"
    The regex is generic so that it matches any week number.
    Returns a tuple: (week, total, mapping) where mapping is a dict {state: count}.
    If a state's value is given as a percentage (e.g., "Abia (20%)"), its count is computed from the overall total.
    If not found, returns (None, None, {}).
    """
    regex = re.compile(
        r"In\s+week\s*(?P<week>\d+).*?new\s+{}(?:\s+cases)?\s+is\s+(?P<total>\d+).*?reported\s+from.*?[–:-]\s*(?P<list>.+?)(?:[\n\.]|$)".format(case_type),
        re.IGNORECASE | re.DOTALL
    )
    m = regex.search(text)
    if m:
        week = m.group('week').strip()
        try:
            total = int(m.group('total'))
        except ValueError:
            total = 0
        state_list = m.group('list').strip().rstrip('.')
        # Normalize: replace " and " with ", "
        state_list = re.sub(r'\s+and\s+', ', ', state_list, flags=re.IGNORECASE)
        items = [x.strip() for x in state_list.split(',')]
        mapping = {}
        for item in items:
            # Allow for numbers with optional "%" sign.
            state_match = re.match(r'(?P<state>[A-Za-z\s]+)\s*\((?P<count>\d+)(?P<perc>%?)\)', item)
            if state_match:
                state_name = state_match.group('state').strip()
                count_str = state_match.group('count')
                perc_flag = state_match.group('perc')
                if perc_flag == '%':
                    try:
                        perc_val = int(count_str)
                        computed = round(total * perc_val / 100)
                        mapping[state_name] = computed
                    except:
                        mapping[state_name] = 0
                else:
                    try:
                        mapping[state_name] = int(count_str)
                    except:
                        mapping[state_name] = 0
        return week, total, mapping
    return None, None, {}

def parse_global_value(text, case_type):
    """
    Parse a global (cumulative) value for a given case type from a narrative that lacks state breakdown.
    Looks for text like:
      "In weeks 13-16 2024, 120 new suspected cases were reported..."
    Returns a tuple: (week, total) or (None, None) if not found.
    """
    regex = re.compile(
       r"In\s+weeks?\s*(?P<week>[\d\-]+).*?(?P<total>\d+)\s+new\s+{}(?:\s+cases)?".format(case_type),
       re.IGNORECASE | re.DOTALL
    )
    m = regex.search(text)
    if m:
        week = m.group('week').strip()
        try:
            total = int(m.group('total'))
        except:
            total = 0
        return week, total
    return None, None

def parse_highlighted_data(text):
    """
    Attempt to parse highlighted sections for both suspected and confirmed cases.
    If at least one state breakdown mapping is found, returns one row per Nigerian state.
    Otherwise, if no specific state data is present but global cumulative values are found,
    returns a single row with state "Overall".
    """
    suspected_week, suspected_total, suspected_map = parse_highlighted_section(text, "suspected")
    confirmed_week, confirmed_total, confirmed_map = parse_highlighted_section(text, "confirmed")
    
    if suspected_map or confirmed_map:
        week_info = suspected_week if suspected_week else (confirmed_week if confirmed_week else extract_week_info(text))
        year = extract_year(text)
        data_rows = []
        for state in NIGERIA_STATES:
            sus_val = suspected_map.get(state, 0)
            con_val = confirmed_map.get(state, 0)
            row = {
                'year': year,
                'week': week_info,
                'state': state,
                'suspected': sus_val,
                'confirmed': con_val
            }
            data_rows.append(row)
        return data_rows
    else:
        # Try global parsing if no state breakdown is present.
        global_sus_week, global_sus_total = parse_global_value(text, "suspected")
        global_con_week, global_con_total = parse_global_value(text, "confirmed")
        if global_sus_total is not None or global_con_total is not None:
            week_info = global_sus_week if global_sus_week else (global_con_week if global_con_week else extract_week_info(text))
            year = extract_year(text)
            row = {
                'year': year,
                'week': week_info,
                'state': "Overall",
                'suspected': global_sus_total if global_sus_total is not None else 0,
                'confirmed': global_con_total if global_con_total is not None else 0
            }
            return [row]
        else:
            return []

# ======================
# Module 4: General Data Parsing (Segment-Based Fallback)
# ======================
def parse_report(text):
    """
    Parse the report text to extract data rows.
    First, attempt to parse highlighted narrative sections. If these are found, use them.
    Otherwise, split the document into segments (by double newlines) and process each segment,
    skipping segments flagged as cumulative multi-year.
    Returns a list of dictionaries with:
      - 'year': Report year.
      - 'week': Week or week range.
      - 'state': State name.
      - 'suspected': Count of suspected cases.
      - 'confirmed': Count of confirmed cases.
    """
    # Attempt highlighted parsing first.
    highlighted_rows = parse_highlighted_data(text)
    if highlighted_rows:
        logging.info("Highlighted data section parsed successfully.")
        return highlighted_rows

    # Fallback: segment-based parsing.
    data_rows = []
    report_year = extract_year(text)
    week_info = extract_week_info(text)
    
    segments = re.split(r'\n\s*\n', text)
    
    summary_pattern = re.compile(
        r'(?P<state>[A-Za-z\s]+)[\s:,-]+'
        r'(?:suspected\s*cases?[:\-]?\s*(?P<suspected>\d{1,3}(?:,\d{3})*|\d+))[\s,;-]+'
        r'(?:confirmed\s*cases?[:\-]?\s*(?P<confirmed>\d{1,3}(?:,\d{3})*|\d+))',
        re.IGNORECASE
    )
    table_pattern = re.compile(
        r'^(?P<state>[A-Za-z\s]+)[,\s]+'
        r'(?P<suspected>\d{1,3}(?:,\d{3})*|\d+)[,\s]+'
        r'(?P<confirmed>\d{1,3}(?:,\d{3})*|\d+)$'
    )
    
    for segment in segments:
        if detect_cumulative_multiyear(segment):
            logging.info("Skipping segment due to cumulative multi-year data.")
            continue
        segment_found = False
        for match in summary_pattern.finditer(segment):
            segment_found = True
            state = match.group('state').strip()
            try:
                suspected = int(match.group('suspected').replace(',', ''))
                confirmed = int(match.group('confirmed').replace(',', ''))
            except ValueError:
                logging.warning(f"Conversion error in segment for state {state}")
                continue
            row = {
                'year': report_year,
                'week': week_info,
                'state': state,
                'suspected': suspected,
                'confirmed': confirmed
            }
            data_rows.append(row)
        if not segment_found:
            lines = segment.splitlines()
            for line in lines:
                line = line.strip()
                match = table_pattern.match(line)
                if match:
                    state = match.group('state').strip()
                    try:
                        suspected = int(match.group('suspected').replace(',', ''))
                        confirmed = int(match.group('confirmed').replace(',', ''))
                    except ValueError:
                        continue
                    row = {
                        'year': report_year,
                        'week': week_info,
                        'state': state,
                        'suspected': suspected,
                        'confirmed': confirmed
                    }
                    data_rows.append(row)
    
    if not data_rows:
        logging.warning("No valid data rows parsed from the report.")
    return data_rows

# ======================
# Module 5: Data Validation, Completion, and CSV Output
# ======================
def write_to_csv(data_rows, output_file):
    """
    Write the list of dictionaries (data_rows) to a CSV file at output_file.
    Uses the following schema: year, week, state, suspected, confirmed.
    """
    if not data_rows:
        logging.info("No data rows available for CSV output.")
        return

    fieldnames = ['year', 'week', 'state', 'suspected', 'confirmed']
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in data_rows:
                writer.writerow(row)
        logging.info(f"CSV successfully written to {output_file}")
    except Exception as e:
        logging.error(f"Error writing CSV file {output_file}: {e}")

def process_pdf_file(file_path):
    """
    Process an individual PDF file:
     1. Extract text.
     2. Parse the report to extract data rows.
     3. Validate each row to ensure raw count data is used.
     4. For the report's week, ensure every Nigerian state plus FCT is recorded
        (adding zeros for missing states if a breakdown is provided).
        (If only global data is present, a single row with state "Overall" is output.)
     5. If the week number is "Unknown", fall back to extracting it from the file name.
    Returns a list of valid data rows.
    """
    text = extract_text_from_pdf(file_path)
    if text is None:
        return []

    parsed_rows = parse_report(text)
    valid_rows = []
    for row in parsed_rows:
        if row['state'] and row['suspected'] is not None and row['confirmed'] is not None:
            valid_rows.append(row)
        else:
            logging.warning(f"Incomplete data row skipped: {row}")

    # If we got a breakdown (i.e. not an "Overall" row), ensure every state is present.
    if not (len(valid_rows) == 1 and valid_rows[0]['state'] == "Overall"):
        found_states = { row['state'].strip().lower() for row in valid_rows }
        for state in NIGERIA_STATES:
            if state.lower() not in found_states:
                default_row = {
                    'year': extract_year(text),
                    'week': extract_week_info(text),
                    'state': state,
                    'suspected': 0,
                    'confirmed': 0
                }
                valid_rows.append(default_row)

    # Fallback: if week is still "Unknown", attempt to extract from the file name.
    for row in valid_rows:
        if row['week'] == 'Unknown':
            # Look for the last number before ".pdf" in the file name.
            fallback_match = re.search(r'(\d+)(?=\.pdf$)', file_path, re.IGNORECASE)
            if fallback_match:
                row['week'] = fallback_match.group(1)
            else:
                row['week'] = 'Unknown'
                
    return valid_rows

def process_directory(pdf_directory, output_csv):
    """
    Process all PDF files in pdf_directory:
     - For each PDF, extract and validate data rows.
     - Consolidate all valid rows and write them to the specified CSV file.
    """
    all_data = []
    for file_name in os.listdir(pdf_directory):
        if file_name.lower().endswith('.pdf'):
            file_path = os.path.join(pdf_directory, file_name)
            logging.info(f"Processing file: {file_path}")
            rows = process_pdf_file(file_path)
            if rows:
                all_data.extend(rows)
            else:
                logging.info(f"No valid data extracted from {file_path}")
    write_to_csv(all_data, output_csv)

# ======================
# Module 6: Execution Steps
# ======================
if __name__ == '__main__':
    # Define the input directory containing PDF reports and the output CSV file.
    pdf_directory = 'pdfs'    # Ensure this directory exists and contains the PDFs.
    output_csv = 'parsed_report_2.csv'
    
    # Process the directory of PDF files.
    process_directory(pdf_directory, output_csv)
    
    # Review the generated CSV and the log file (pdf_parser.log) for any skipped segments or errors.

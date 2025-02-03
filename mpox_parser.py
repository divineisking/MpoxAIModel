import pdfplumber
import csv
import os
import re
import logging
from tqdm import tqdm
from datetime import datetime
from collections import defaultdict

# Configure logging
logging.basicConfig(
    filename='mpox_errors.log',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Master list of Nigerian states (36 + FCT)
STATES = [
    "Abia", "Adamawa", "Akwa Ibom", "Anambra", "Bauchi", "Bayelsa",
    "Benue", "Borno", "Cross River", "Delta", "Ebonyi", "Edo",
    "Ekiti", "Enugu", "FCT", "Gombe", "Imo", "Jigawa",
    "Kaduna", "Kano", "Katsina", "Kebbi", "Kogi", "Kwara",
    "Lagos", "Nasarawa", "Niger", "Ogun", "Ondo", "Osun",
    "Oyo", "Plateau", "Rivers", "Sokoto", "Taraba", "Yobe",
    "Zamfara"
]

def extract_year_week(filename):
    """Extract year/week from filename with validation"""
    match = re.search(r"_(\d{2})(\d{2})(\d{2})_(\d+)\.pdf", filename)
    if match:
        day, month, year_short, week = match.groups()
        year = 2000 + int(year_short)
        return (year, int(week))
    return (None, None)

def get_expected_weeks():
    """Generate all expected (year, week) pairs from 2017-2024"""
    expected = set()
    for year in range(2017, 2025):
        for week in range(1, 53):
            expected.add((year, week))
    return expected

def parse_pdf(pdf_path):
    """Parse PDF file and return structured data"""
    data = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            filename = os.path.basename(pdf_path)
            year, week = extract_year_week(filename)
            full_text = "\n".join([page.extract_text() or "" for page in pdf.pages])

            # Extract confirmed cases from tables
            confirmed_cases = defaultdict(int)
            for page in pdf.pages:
                for table in page.extract_tables():
                    if len(table) > 1 and "Confirmed Cases" in table[0][0]:
                        for row in table[1:]:
                            if len(row) >= 2 and row[0].strip() in STATES:
                                state = row[0].strip()
                                confirmed_cases[state] = int(row[1].strip() or 0)

            # Extract suspected cases from text
            suspected_cases = defaultdict(int)
            suspect_pattern = r"(\b[A-Za-z\s]+\b)\s+(\d+)(?=\s*$)"
            matches = re.findall(suspect_pattern, full_text, re.MULTILINE)
            for match in matches:
                state = match[0].strip()
                if state in STATES:
                    suspected_cases[state] = int(match[1])

            # Create entries for all states
            for state in STATES:
                data.append({
                    'year': year,
                    'week': week,
                    'state': state,
                    'suspected': suspected_cases.get(state, 0),
                    'confirmed': confirmed_cases.get(state, 0)
                })

    except Exception as e:
        logging.error(f"Error parsing {pdf_path}: {str(e)}", exc_info=True)
        return []

    return data

def process_pdfs(pdf_folder, output_csv):
    """Main processing function with error handling and reporting"""
    all_data = []
    processed_weeks = set()
    existing_files = set()
    failed_weeks = []

    # First pass: Process all PDF files
    pdf_files = []
    for f in os.listdir(pdf_folder):
        if f.endswith(".pdf"):
            year, week = extract_year_week(f)
            if year and week:
                pdf_files.append((f, year, week))
                existing_files.add((year, week))

    # Process files with progress bar
    for filename, year, week in tqdm(pdf_files, desc="Processing PDFs"):
        pdf_path = os.path.join(pdf_folder, filename)
        try:
            entries = parse_pdf(pdf_path)
            if entries:
                processed_weeks.add((year, week))
                all_data.extend(entries)
        except Exception as e:
            failed_weeks.append((year, week, str(e)))
            logging.error(f"Failed to process {filename}: {str(e)}", exc_info=True)

    # Second pass: Identify missing weeks
    expected_weeks = get_expected_weeks()
    missing_weeks = expected_weeks - existing_files

    # Add missing week entries
    for year, week in missing_weeks:
        for state in STATES:
            all_data.append({
                'year': year,
                'week': week,
                'state': state,
                'suspected': 0,
                'confirmed': 0,
                'missing': True,
                'not_processed': False,
                'error': 'No PDF file found'
            })

    # Add failed processing entries
    for year, week, error in failed_weeks:
        for state in STATES:
            all_data.append({
                'year': year,
                'week': week,
                'state': state,
                'suspected': 0,
                'confirmed': 0,
                'missing': False,
                'not_processed': True,
                'error': error
            })

    # Data validation and cleaning
    valid_data = []
    for item in all_data:
        if isinstance(item, dict) and all(key in item for key in ['year', 'week', 'state']):
            valid_data.append(item)
        else:
            logging.warning(f"Removed invalid entry: {item}")

    # Sort data chronologically
    valid_data.sort(key=lambda x: (x['year'], x['week'], x['state']))

    # Write to CSV
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['year', 'week', 'state', 'suspected', 'confirmed',
                     'missing', 'not_processed', 'error']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(valid_data)
    all_data = []
    processed_weeks = set()
    existing_pdf_weeks = set()
    failed_weeks = []

    # Get all PDF files with valid year/week
    pdf_files = []
    for f in os.listdir(pdf_folder):
        if f.endswith(".pdf"):
            year, week = extract_year_week(f)
            if year and week:
                pdf_files.append((f, year, week))
                existing_pdf_weeks.add((year, week))

    # Process PDFs with progress bar
    for pdf_file, year, week in tqdm(pdf_files, desc="Processing PDFs"):
        pdf_path = os.path.join(pdf_folder, pdf_file)
        try:
            # Existing parse_pdf logic (modified to return year/week)
            entries = parse_pdf(pdf_path)  # Your existing parsing function
            processed_weeks.add((year, week))
            all_data.extend(entries)
        except Exception as e:
            logging.error(f"Failed {pdf_file}: {str(e)}", exc_info=True)
            failed_weeks.append((year, week, str(e)))

    # Identify missing weeks (no PDF file)
    all_years = range(2017, 2025)
    missing_weeks = []
    for year in all_years:
        for week in range(1, 53):
            if (year, week) not in existing_pdf_weeks:
                missing_weeks.append((year, week))

    # Add missing week entries
    for year, week in missing_weeks:
        for state in STATES:
            all_data.append({
                'year': year,
                'week': week,
                'state': state,
                'suspected': 0,
                'confirmed': 0,
                'missing': True,
                'not_processed': False,
                'error': 'No PDF file found'
            })

    # Add failed processing entries
    for year, week, error in failed_weeks:
        for state in STATES:
            all_data.append({
                'year': year,
                'week': week,
                'state': state,
                'suspected': 0,
                'confirmed': 0,
                'missing': False,
                'not_processed': True,
                'error': error
            })

    # Sort data by year/week/state
    all_data.sort(key=lambda x: (x['year'], x['week'], x['state']))

    # Write to CSV
    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['year', 'week', 'state', 'suspected', 'confirmed',
                     'missing', 'not_processed', 'error']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_data)


if __name__ == "__main__":
    # Configuration
    PDF_FOLDER = r"C:\\xampp\\htdocs\\ncdc_scraper\\pdfs"  # Path to folder containing PDFs
    OUTPUT_CSV = "mpox_cases_sorted_1.csv"
    
    process_pdfs(PDF_FOLDER, OUTPUT_CSV)
    print(f"\nProcessing complete! Data saved to {OUTPUT_CSV}")
    print(f"Error log: mpox_errors.log")
from scraper.utils import parse_date_from_file_name
from datetime import datetime, date

class Test_Scraper_Utils:

    def test_parse_date_from_file_name(self):
        filename = "pdfs/An Update of Monkeypox Outbreak in Nigeria_090323_11.pdf"
        assert parse_date_from_file_name(filename) == date(year=2023, month=3, day=9)

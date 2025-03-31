# ncdc_scraper
pls switch to the master branch before cloning 
This is a data scraper tool designe to scrap for mpox incidence data from publicly available repos


* to run the php webscraper install guzzle with composer
* to run the mpox_parser.py install pdfplumber and tqdm
* to pdf_parser.py install pdfminer.six
* mpox_parser.py and pdf_parser.py both scrap and parse data from the /pdfs dir and save to a csv file in the same format
* but they follow different logic
* I didn't create an a python venv when creatin this project, just saying but i'd advice a venv is created

### LLM Scraping Feature.
Built Integration with Meta's LLAMA to extract relevant data from the documents. 
- To Implement please switch to the Feature-1 branch.

import os
from PyPDF2 import PdfReader
from pathlib import Path
from pydantic import BaseModel
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser, PydanticOutputParser
from data_model import LLMDataModel, MpoxDataModel
from dotenv import load_dotenv
from datetime import date, datetime
import re

load_dotenv()

file_path = r"pdfs/An Update of Monkeypox Outbreak in Nigeria_050123_2.pdf"
file_2 = r"pdfs/An Update of Monkeypox Outbreak in Nigeria_090223_7.pdf"

file_3 = r"pdfs/An Update of Monkeypox Outbreak in Nigeria_090323_11.pdf"

def retrieve_dates_from_file_names(folder_dir: str):
    # Confirm that the file exists
    assert Path(folder_dir).exists()
    path = Path(folder_dir)

    files = [f.name for f in path.iterdir() if f.is_file()]
    print("Files in", folder_dir, ":")
    for file in files:
        print(file) 
    
def parse_date_from_file_name(filename:str):
    date_str = filename.split("_")[1]
    day = int(date_str[:2])
    month = int(date_str[2:4])
    year = int("20" + date_str[4:])

    return date(day=day, month=month, year=year)

def parse_pdf(pdf_file_path: str):
    # Confirm that File Path Exists
    assert Path(pdf_file_path).exists()

    # Read PDF File
    pdf_reader = PdfReader(pdf_file_path)
    print("Reading Pdf File")
    page = pdf_reader.pages[0]
    # Remove "Highlights" line if present
    page_content = page.extract_text()
    # print(page_content)
    text = re.sub(r'^Highlights\s*', '', page_content, flags=re.MULTILINE)

    # Split text into items
    items = re.split(r'(?=•)', text)
    results = []

    # Extract first and third items (ignoring empty strings)
    first_item = re.sub(r'^•\s*', '', items[1]).strip()
    third_item = [line for line in items if "The number of confirmed cases" in line] 
     
    results.append(first_item)
    results.append(third_item)

    return results
    


def get_prompt_for_llm(text_list: list[str]):
    # Define LLM Template Message
    suspected = text_list[0]
    confirmed = text_list[1]

    template_message = f""" I want to extract the Following Information from the Text Below Under the Highlights List, the Information i need supposed to follow this format.

                            The week, State, Suspected Cases and Confirmed Cases. Note the the data contains data from Nigierian States. so ensure that the states are only states of Nigeria. The Suspected cases are 
                            are usually in the First unordered list of the text under the highlights and the COnfirmed cases are usually at the 3rd Item in the highlights. 
                            Do not write any code to extract it. Just give me the data i need in python dictionary format.
                            
                            A expected data output is a dictionary with the following format. Output just the dictionary without defining it using a variable because i'm parsing the output to a json parser. 
                            If the individual states is not given whether in the confirmed or suspected section. You can just output the total given for either confirmed or suspected.
                            week key with the week number as an int e.g 'week' : 34
                            suspected_cases key with values which is a dictionary of all the suspected states cases from the data below  
                            confirmed_cases key with values which is a dictionary of all the confirmed states cases from the data below
                            
                            You to only extract Suspected cases from here
                            data_containing_suspected_cases = {suspected}
                            And you are to extract Confirmed cases from here 
                            data_containing_confirmed = "{confirmed}"

                            You must always return valid JSON fenced by a markdown code block. Do not return any additional text.
                        """
    
    # Create Template message.
    # prompt_template = PromptTemplate.from_template(template_message)
    
    # #Create the Prompt 
    # prompt = prompt_template.invoke({"Data" : text})
    # print("Defining Prompt...")
    # print(prompt)
    return template_message

def parse_data_to_llm(text: str):
    # Call LLama using Langchain

    # Define Vairables for Langchain
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    model_version = "llama-3.3-70b-versatile"

    

    # Create Model Instance and Invoke a message to the model
    model = ChatGroq(api_key=GROQ_API_KEY, model=model_version)
    # model.invoke("Hello, how are you?")

    # Format the prompt to properly get an output
    llm_prompt = get_prompt_for_llm(text)

    # Parse the output through the Pydantic Output Parser
    parser = PydanticOutputParser(pydantic_object=LLMDataModel)
    chain = model|parser
    output = chain.invoke(llm_prompt)
    print(output)





# print(parse_pdf(file_2))

# parse_data_to_llm(parse_pdf(file_2))
# parse_data_to_llm(parse_pdf(file_3))
# parse_data_to_llm(parse_pdf(file_path))

print(parse_date_from_file_name("pdfs/An Update of Monkeypox Outbreak in Nigeria_090223_7.pdf"))
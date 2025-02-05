import os
from PyPDF2 import PdfReader
from pathlib import Path
from pydantic import BaseModel
from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv

load_dotenv()

file_path = r"pdfs/An Update of Monkeypox Outbreak in Nigeria_050123_2.pdf"
file_2 = r"pdfs/An Update of Monkeypox Outbreak in Nigeria_090223_7.pdf"

file_3 = r"pdfs/An Update of Monkeypox Outbreak in Nigeria_090323_11.pdf"


def parse_pdf(pdf_file_path: str):
    # Confirm that File Path Exists
    assert Path(pdf_file_path).exists()

    # Read PDF File
    pdf_reader = PdfReader(pdf_file_path)
    print("Reading Pdf File")
    page = pdf_reader.pages[0]
    print(page.extract_text())


def parse_data_to_llm(text: str):
    # Call LLama using Langchain

    # Define Vairables for Langchain
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    model_version = "llama-3.3-70b-versatile"

    # Create Model Instance and Invoke a message to the model
    model = ChatGroq(api_key=GROQ_API_KEY, model=model_version)
    # model.invoke("Hello, how are you?")

    # Parse the output through the STROutputParser
    parser = StrOutputParser()
    chain = model|parser
    output = chain.invoke(text)
    print(output)






# parse_pdf(file_path)
# parse_pdf(file_2)
# parse_pdf(file_3)

parse_data_to_llm()
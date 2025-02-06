from pydantic import BaseModel
from datetime import datetime

# Define a clear data model to ensure data accuracy in the csv file
class MpoxDataModel(BaseModel):
    """
    The Mpox Data Model is the final Data Model Format that is passed into the csv file to ensure data Consistency
    """
    date: datetime
    year: int
    month: int
    day: int
    week: int
    state: str
    suspected_cases: int
    confirmed_cases: int

class LLMDataModel(BaseModel):
    """
    The LLMDataModel is actually used to parse data from the LLM to get the states and confirmed cases.
    """
    # date: datetime
    week: int 
    suspected_cases: dict[str, int] 
    confirmed_cases: dict[str, int]

from pydantic import BaseModel
from datetime import datetime

# Define a clear data model to ensure data accuracy in the csv file
class MpoxDataModel(BaseModel):
    date: datetime
    year: int
    month: int
    day: int
    week: int
    state: str
    suspected_cases: int
    confirmed_cases: int
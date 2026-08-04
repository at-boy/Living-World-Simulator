from dataclasses import dataclass

@dataclass(slots=True)
class Connection:
    source:str
    destination:str
    travel_time:int=1

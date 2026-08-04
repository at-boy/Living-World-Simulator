from dataclasses import dataclass

@dataclass(slots=True)
class Location:
    id:str
    name:str
    description:str=""

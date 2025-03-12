from dataclasses import dataclass
from .direction import Direction

@dataclass
class Order:
    asset: str
    price: float
    direction: Direction
    quantity: int
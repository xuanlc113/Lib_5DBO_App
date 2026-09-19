from dataclasses import dataclass
from enum import Enum


class SignalType(Enum):
    BO = "BO"
    PB_DAILY = "PB_daily"
    PB_WEEKLY = "PB_weekly"


class OrderType(Enum):
    LMT = "LMT"
    STP_LMT = "STP_LMT"


@dataclass
class Bar:
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class OrderInfo:
    order_type: OrderType
    status: str
    avg_fill_price: float
    filled: float


@dataclass
class BOSignal:
    ticker: str
    bar: Bar
    action: str
    price: float
    stop: float
    risk: float


@dataclass
class PBSignal:
    ticker: str
    bar: Bar
    atr: float
    signal_type: SignalType
    risk: float

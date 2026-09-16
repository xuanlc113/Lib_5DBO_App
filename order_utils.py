from __future__ import annotations

from domain import Bar


def calcQuantity(bet_size: float, risk_per_share: float) -> int:
    if risk_per_share <= 0:
        return 0
    return int(round(bet_size / risk_per_share))


def calc_bo_risk(action: str, bar: Bar, entry_price: float, limit_buffer: float) -> float:
    if action == "LONG":
        return (entry_price + limit_buffer) - bar.low
    return bar.high - (entry_price - limit_buffer)


def getAcceptableEntry(close: float, bidask: float, action: str, spread: float = 0.005) -> float:
    if action == "LONG":
        percent_diff = (bidask - close) / close
    else:
        percent_diff = (close - bidask) / close
    if percent_diff > spread:
        return close
    return bidask


def calc_limit_price(action: str, entry_price: float, buffer: float) -> float:
    if action == "LONG":
        return entry_price + buffer
    return entry_price - buffer


def is_past_trigger(action: str, close: float, trigger_price: float) -> bool:
    if action == "LONG":
        return close >= trigger_price
    return close <= trigger_price



def calc_atr(bars: list[Bar], period: int = 5) -> float:
    bars = bars[-(period + 1):]
    true_ranges = []
    for i in range(1, len(bars)):
        prev_close = bars[i - 1].close
        tr = max(
            bars[i].high - bars[i].low,
            abs(bars[i].high - prev_close),
            abs(bars[i].low - prev_close),
        )
        true_ranges.append(tr)

    print(true_ranges)
    return sum(true_ranges) / len(true_ranges)

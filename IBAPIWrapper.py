from dataclasses import dataclass
from ibapi.wrapper import EWrapper, BarData, OrderId, Decimal, TickerId, TickType, TickAttrib
import utils


@dataclass
class OrderState:
    status: str = ""
    filled: float = 0.0
    remaining: float = 0.0
    avg_fill_price: float = 0.0


class IBAPIWrapper(EWrapper):
    def __init__(self):
        super().__init__()
        self.tickerBarsList: dict[int, list[BarData]] = {}
        self.tickerRetrieved: dict[int, bool] = {}
        self._reqIdToTicker: dict[int, str] = {}
        self.tickerBid: dict[str, float] = {}
        self.tickerAsk: dict[str, float] = {}
        self.orderData: dict[int, OrderState] = {}
        self.accountSummaryDict: dict[str, float] = {}
        self.accountSummaryReqDone: dict[int, bool] = {}

    def nextValidId(self, orderId):
        self.nextOrderId = orderId
        utils.log(f"Next valid order id: {self.nextOrderId}")

    def historicalData(self, reqId: int, bar: BarData):
        utils.log(f"Received historical data for reqId {reqId}: {bar}")
        if reqId not in self.tickerBarsList:
            self.tickerBarsList[reqId] = []
        self.tickerBarsList[reqId].append(bar)

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        utils.log(f"Historical data for reqId {reqId} received from {start} to {end}.")
        self.tickerRetrieved[reqId] = True

    def tickPrice(self, reqId: TickerId, tickType: TickType, price: float, attrib: TickAttrib):
        ticker = self._reqIdToTicker.get(reqId)
        if ticker is None:
            return
        if tickType == 1:  # BID
            self.tickerBid[ticker] = price
        elif tickType == 2:  # ASK
            self.tickerAsk[ticker] = price

    def orderStatus(self, orderId: OrderId, status: str, filled: Decimal, remaining: Decimal, avgFillPrice: float, permId: int, parentId: int, lastFillPrice: float, clientId: int, whyHeld: str, mktCapPrice: float):
        state = self.orderData.setdefault(orderId, OrderState())
        state.status = status
        state.filled = float(filled)
        state.remaining = float(remaining)
        state.avg_fill_price = avgFillPrice
        if status == "Filled":
            state.remaining = 0
            utils.log(f"Order {orderId} filled: {filled} shares at avg price {avgFillPrice}.")
        elif filled > 0 and remaining > 0:
            utils.log(f"Order {orderId} partially filled: {filled} filled, {remaining} remaining.")

    def accountSummary(self, reqId: int, account: str, tag: str, value: str, currency: str):
        try:
            if tag == "NetLiquidationByCurrency" and currency == "BASE":
                self.accountSummaryDict["NetLiquidationBase"] = float(value)
            elif tag == "ExchangeRate" and currency == "USD":
                self.accountSummaryDict["ExchangeRateUSD"] = float(value)
        except ValueError:
            pass

    def accountSummaryEnd(self, reqId: int):
        self.accountSummaryReqDone[reqId] = True

    def error(self, reqId: int, errorCode: int, errorString: str, advancedOrderRejectJson = ""):
        try:
            utils.log(f"ERROR {reqId} {errorCode} {errorString}")
        except Exception:
            print(f"ERROR {reqId} {errorCode} {errorString}")

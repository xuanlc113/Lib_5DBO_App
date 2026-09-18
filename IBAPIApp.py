import math
import threading
import time
from dataclasses import dataclass
from typing import Optional

from ibapi.order import Order
from ibapi.contract import Contract
from ibapi.order_cancel import OrderCancel

from IBAPIWrapper import IBAPIWrapper
from IBAPIClient import IBAPIClient
from domain import Bar, OrderInfo, OrderType
import utils
import order_utils


@dataclass
class _TickerOrderState:
    order_id: int
    order_type: OrderType


_INTERVAL_TO_BAR_SIZE = {
    "D": "1 day",
    "W": "1 week",
}


class IBAPIApp(IBAPIWrapper, IBAPIClient):
    def __init__(self, ipAddress, portId, clientId):
        IBAPIWrapper.__init__(self)
        IBAPIClient.__init__(self, wrapper=self)

        self.nextOrderId = 0
        self._tickerOrderStateDict: dict[str, _TickerOrderState] = {}
        self._cumulativeRiskDict: dict[str, float] = {}
        self._lastAccumulatedOrderId: dict[str, int] = {}

        self.connect(ipAddress, portId, clientId)

        thread = threading.Thread(target=self.run)
        thread.start()
        setattr(self, "_thread", thread)

    def isReady(self) -> bool:
        return self.nextOrderId != 0

    def _nextRequestID(self) -> int:
        oldId = self.nextOrderId
        self.nextOrderId += 1
        return oldId

    def _createContract(self, ticker: str) -> Contract:
        contract = Contract()
        contract.symbol = ticker
        contract.secType = 'STK'
        contract.exchange = 'SMART'
        contract.currency = 'USD'
        return contract

    def fetchHistoricalBars(self, ticker: str, period: int, interval: str, timeout: int = 10) -> list[Bar]:
        reqId = self._nextRequestID()
        contract = self._createContract(ticker)
        bar_size = _INTERVAL_TO_BAR_SIZE[interval]
        fetch_period = period + (math.ceil(period/5) * 2) + 5 if period > 1 else period
        duration = f"{fetch_period} {interval}"
        super().reqHistoricalData(reqId, contract, "", duration, bar_size, "TRADES", 1, 1, False, [])
        start = time.time()
        while True:
            if self.tickerRetrieved.get(reqId, False):
                bars = self.tickerBarsList.get(reqId, [])
                for _ in range(5):
                    if len(bars) >= period:
                        break
                    time.sleep(0.1)
                    bars = self.tickerBarsList.get(reqId, [])
                if len(bars) < period:
                    utils.log(f"Insufficient bars for {ticker}: got {len(bars)}, expected >= {period}.")
                    return []
                return [Bar(open=b.open, high=b.high, low=b.low, close=b.close, volume=float(b.volume)) for b in bars]
            if time.time() - start > timeout:
                utils.log(f"Timeout waiting for historical bars for {ticker}.")
                self.cancelHistoricalData(reqId)
                return []
            time.sleep(0.1)

    def fetchMarketPrice(self, ticker: str, action: str, timeout: int = 10) -> Optional[float]:
        self.tickerAsk.pop(ticker, None)
        self.tickerBid.pop(ticker, None)
        reqId = self._nextRequestID()
        contract = self._createContract(ticker)
        self._reqIdToTicker[reqId] = ticker
        super().reqMktData(reqId, contract, "", False, False, [])
        start = time.time()
        while True:
            if action == "LONG" and ticker in self.tickerAsk:
                self.cancelMktData(reqId)
                return self.tickerAsk[ticker]
            if action == "SHORT" and ticker in self.tickerBid:
                self.cancelMktData(reqId)
                return self.tickerBid[ticker]
            if time.time() - start > timeout:
                utils.log(f"Timeout waiting for bid/ask for {ticker}.")
                self.cancelMktData(reqId)
                return None
            time.sleep(0.1)

    def getOrderInfo(self, ticker: str) -> Optional[OrderInfo]:
        state = self._tickerOrderStateDict.get(ticker)
        if state is None:
            return None
        order_state = self.orderData.get(state.order_id)
        if order_state is None:
            return OrderInfo(order_type=state.order_type, status="", avg_fill_price=0.0, filled=0.0)
        return OrderInfo(
            order_type=state.order_type,
            status=order_state.status,
            avg_fill_price=order_state.avg_fill_price,
            filled=order_state.filled,
        )

    def accumulateFilledRisk(self, ticker: str, risk_per_share: float) -> float:
        state = self._tickerOrderStateDict.get(ticker)
        if state is None:
            return self._cumulativeRiskDict.get(ticker, 0.0)
        order_id = state.order_id
        if self._lastAccumulatedOrderId.get(ticker) == order_id:
            return self._cumulativeRiskDict.get(ticker, 0.0)
        order_state = self.orderData.get(order_id)
        if order_state is None or order_state.filled == 0:
            return self._cumulativeRiskDict.get(ticker, 0.0)
        self._cumulativeRiskDict[ticker] = self._cumulativeRiskDict.get(ticker, 0.0) + risk_per_share * order_state.filled
        self._lastAccumulatedOrderId[ticker] = order_id
        return self._cumulativeRiskDict[ticker]

    def cancelOrderForTicker(self, ticker: str) -> bool:
        state = self._tickerOrderStateDict.get(ticker)
        if state is None:
            utils.log(f"No order found for ticker {ticker}.")
            return False
        order_id = state.order_id
        super().cancelOrder(order_id, OrderCancel())
        start = time.time()
        while True:
            order_state = self.orderData.get(order_id)
            if order_state is not None and order_state.status == "Cancelled":
                utils.log(f"Order {order_id} for {ticker} has been cancelled.")
                return True
            if time.time() - start > 10:
                utils.log(f"Timeout waiting for cancellation of order {order_id} for {ticker}.")
                return False
            time.sleep(0.1)

    def _placeLimitOrder(self, orderID: int, contract: Contract, action: str, quantity: int, limit_price: float):
        order = Order()
        order.orderType = "LMT"
        order.action = action
        order.totalQuantity = quantity
        order.lmtPrice = limit_price
        super().placeOrder(orderID, contract, order)

    def _placeStopLimitOrder(self, orderID: int, contract: Contract, action: str, quantity: int, stop_price: float, limit_price: float):
        order = Order()
        order.orderType = "STP LMT"
        order.action = action
        order.totalQuantity = quantity
        order.auxPrice = stop_price
        order.lmtPrice = limit_price
        super().placeOrder(orderID, contract, order)

    def sendLimitOrder(self, ticker: str, action: str, quantity: int, limit_price: float, order_type: OrderType):
        new_id = self._nextRequestID()
        contract = self._createContract(ticker)
        side = "BUY" if action == "LONG" else "SELL"
        self._tickerOrderStateDict[ticker] = _TickerOrderState(order_id=new_id, order_type=order_type)
        self._placeLimitOrder(new_id, contract, side, quantity, limit_price)

    def sendStopLimitOrder(self, ticker: str, action: str, quantity: int, stop_price: float, limit_price: float, order_type: OrderType):
        new_id = self._nextRequestID()
        contract = self._createContract(ticker)
        side = "BUY" if action == "LONG" else "SELL"
        self._tickerOrderStateDict[ticker] = _TickerOrderState(order_id=new_id, order_type=order_type)
        self._placeStopLimitOrder(new_id, contract, side, quantity, stop_price, limit_price)

    def fetchATR(self, ticker: str, period: int = 5, interval: str = "D") -> Optional[float]:
        fetch_period = period * 5 # fetch 5x bars for rma calculation
        bars = self.fetchHistoricalBars(ticker, fetch_period + 1, interval) # fetch additional bars for atr gap
        if not bars:
            return None
        return order_utils.calc_atr(bars, period)

    def fetchAccountCapital(self, timeout: int = 10) -> Optional[float]:
        reqId = self._nextRequestID()
        super().reqAccountSummary(reqId, "All", "$LEDGER:ALL")
        start = time.time()
        while True:
            if self.accountSummaryReqDone.get(reqId, False):
                super().cancelAccountSummary(reqId)
                net_liq_base = self.accountSummaryDict.get("NetLiquidationBase")
                exchange_rate_usd = self.accountSummaryDict.get("ExchangeRateUSD")
                if net_liq_base is not None and exchange_rate_usd and exchange_rate_usd != 0:
                    return net_liq_base / exchange_rate_usd
                return None
            if time.time() - start > timeout:
                utils.log("Timeout waiting for account summary.")
                super().cancelAccountSummary(reqId)
                return None
            time.sleep(0.1)

from ibapi.wrapper import EWrapper, BarData, OrderId, Decimal, TickerId, TickType, TickAttrib

class IBAPIWrapper(EWrapper):
    def __init__(self):
        super().__init__()
        self.tickerData = {}
        self.tickerRetrieved = {}
        self.tickerBid = {}
        self.tickerBidRetrieved = {}
        self.tickerAsk = {}
        self.tickerAskRetrieved = {}
        self.orderStatusDict = {}
        self.orderFilledDict = {}
        self.orderRemainingDict = {}
        self.orderAvgFillPrice = {}

    def nextValidId(self, orderId):
        self.nextOrderId = orderId
        print(self.nextOrderId)

    def historicalData(self, reqId:int, bar: BarData):
        print(f"Received historical data for reqId {reqId}: {bar}")
        self.tickerData[reqId] = bar

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        print(f"Historical data for reqId {reqId} received from {start} to {end}.")
        self.tickerRetrieved[reqId] = True

    def tickPrice(self, reqId: TickerId, tickType: TickType, price: float, attrib: TickAttrib):
        print(f"Received tick price for reqId {reqId}: {tickType}, {price}, {attrib}")
        if tickType == 1:  # BID
            self.tickerBid[reqId] = price
            self.tickerBidRetrieved[reqId] = True
        elif tickType == 2:  # ASK
            self.tickerAsk[reqId] = price
            self.tickerAskRetrieved[reqId] = True

    def orderStatus(self, orderId: OrderId, status: str, filled: Decimal, remaining: Decimal, avgFillPrice: float, permId: int, parentId: int, lastFillPrice: float, clientId: int, whyHeld: str, mktCapPrice: float):
        self.orderStatusDict[orderId] = status
        self.orderFilledDict[orderId] = float(filled)
        self.orderRemainingDict[orderId] = float(remaining)
        self.orderAvgFillPrice[orderId] = avgFillPrice
        if status == "Filled":
            self.orderRemainingDict[orderId] = 0
        elif filled > 0 and remaining > 0:
            print(f"Order {orderId} partially filled: {filled} filled, {remaining} remaining.")
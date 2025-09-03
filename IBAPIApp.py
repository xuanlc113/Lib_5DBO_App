import threading
import time

from ibapi.order import Order
from ibapi.contract import Contract
from ibapi.order_cancel import OrderCancel

from IBAPIWrapper import IBAPIWrapper
from IBAPIClient import IBAPIClient

class IBAPIApp(IBAPIWrapper, IBAPIClient):
    def __init__(self, ipAddress, portId, clientId):
        IBAPIWrapper.__init__(self)
        IBAPIClient.__init__(self, wrapper=self)

        self.nextOrderId = 0
        self.tickerReqIdDict = {}
        self.tickerOrderIdDict = {}
        self.orderIdTypeDict = {}

        self.connect(ipAddress, portId, clientId)

        thread = threading.Thread(target=self.run)
        thread.start()
        setattr(self, "_thread", thread)

    def nextRequestID(self):
        oldId = self.nextOrderId
        self.nextOrderId += 1
        return oldId

    def createContract(self, ticker):
        contract = Contract()
        contract.symbol = ticker
        contract.secType = 'STK'
        contract.exchange = 'SMART'
        contract.currency = 'USD'
        return contract

    def reqData(self, reqId, contract):
        self.tickerReqIdDict[contract.symbol] = reqId
        super().reqHistoricalData(reqId, contract, "", "1 D", "1 day", "TRADES", 1, 1, False, [])
        super().reqMktData(reqId, contract, "", False, False, [])
    
    def waitForData(self, ticker, action, timeout=5):
        reqId = self.tickerReqIdDict.get(ticker)
        if reqId is None:
            print(f"No reqId found for ticker {ticker}.")
            return False
        start = time.time()
        while True:
            ohlc_ready = self.tickerRetrieved.get(reqId, False)
            if action == "LONG":
                ask_ready = self.tickerAskRetrieved.get(reqId, False)
                if ohlc_ready and ask_ready:
                    break
            elif action == "SHORT":
                bid_ready = self.tickerBidRetrieved.get(reqId, False)
                if ohlc_ready and bid_ready:
                    break
            if time.time() - start > timeout:
                print(f"Timeout waiting for OHLC data for {ticker}.")
                self.cancelMktData(reqId)
                return False
            time.sleep(0.1)
        
        self.cancelMktData(reqId)
        return True
    
    def waitForCancelOrder(self, orderId, timeout=5):
        start = time.time()
        while True:
            status = self.orderStatusDict.get(orderId, "")
            if status == "Cancelled":
                print(f"Order {orderId} has been cancelled.")
                return True
            if time.time() - start > timeout:
                print(f"Timeout waiting for cancellation of order {orderId}.")
                return False
            time.sleep(0.1)
    
    def getOrderStatus(self, orderID):
        return self.orderStatusDict.get(orderID, None)

    def sendLimitOrder(self, orderID, contract, action, quantity, limit_price): 
        order = Order()
        order.orderType = "LMT"
        order.action = action
        order.totalQuantity = quantity
        order.lmtPrice = limit_price

        self.orderIdTypeDict[orderID] = "LMT"

        super().placeOrder(orderID, contract, order)

    def sendStopLimitOrder(self, orderID, contract, action, quantity, stop_price, limit_price):
        order = Order()
        order.orderType = "STP LMT"
        order.action = action
        order.totalQuantity = quantity
        order.auxPrice = stop_price
        order.lmtPrice = limit_price

        self.orderIdTypeDict[orderID] = "STP LMT"
        
        super().placeOrder(orderID, contract, order)

    def cancelOrder(self, orderID):
        orderCancel = OrderCancel()
        super().cancelOrder(orderID, orderCancel)
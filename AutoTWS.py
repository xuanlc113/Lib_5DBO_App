import time
from datetime import datetime, time as dtime
import pytz

from IBAPIApp import IBAPIApp
import utils
import config

def getUnfilledTickers(app, orders):
    unfilled = set()
    for order in orders:
        ticker = order["ticker"]
        orderId = app.tickerOrderIdDict.get(ticker)
        if orderId is None:
            unfilled.add(ticker)
            continue
        status = app.getOrderStatus(orderId)
        if status != "Filled":
            unfilled.add(ticker)
    return unfilled

def isWithinRetryWindow():
    ny_tz = pytz.timezone("America/New_York")
    now_ny = datetime.now(ny_tz).time()
    return dtime(15, 50) <= now_ny < dtime(15, 59, 35)
    # return dtime(12, 50) <= now_ny < dtime(13, 0)

def wait_for_358_ny():
    utils.log("Waiting for 15:58...")
    ny_tz = pytz.timezone('America/New_York')
    while True:
        now_ny = datetime.now(ny_tz)
        # if (now_ny.hour == 12 and now_ny.minute >= 57 and now_ny.second >= 45) or (now_ny.hour == 12 and now_ny.minute >= 58):
        if (now_ny.hour == 15 and now_ny.minute >= 57 and now_ny.second >= 45) or (now_ny.hour == 15 and now_ny.minute >= 58):
            break
        time.sleep(1)

def launchTWSAPI(host, port, clientId):
    utils.log("Launching IB API application...")
    app = IBAPIApp(host, port, clientId)
    time.sleep(5)
    if app.nextOrderId == 0:
        utils.log("Failed to connect to IB API, exiting...")
        return None
    
    utils.log("IB API Application Launched.")
    
    # dummy call for historical data connection
    utils.log("Making dummy call for historical data connection...")
    reqId = app.nextRequestID()
    contract = app.createContract("AAPL")
    app.reqData(reqId, contract)

    if not app.waitForData('AAPL', 'LONG', timeout=10):
        utils.log(f"No OHLC data for dummy AAPL call")
        return None
    else:
        utils.log("IB API historical data connection successful.")
        return app
    

def start(orders):
    cfg = config.read_config()
    host = cfg["host"]
    port = int(cfg["port"])
    clientId = int(cfg["client_id"])
    maxCapital = float(cfg["max_capital"])
    fallbackCapital = float(cfg["fallback_capital"])
    risk = float(cfg["risk"])
    limitBuffer = float(cfg["limit_buffer"])
    betMultiplier = float(cfg.get("bet_multiplier", 1.0))

    # if not isWithinRetryWindow():
    #     utils.log("Not within entry window, exiting...")
    #     return
    
    app = launchTWSAPI(host, port, clientId)
    if not app:
        time.sleep(3)
        app = launchTWSAPI(host, port, clientId)

    if not app:
        utils.log("Failed to launch IB API application after retry, exiting...")
        utils.alarm()
        return
    
    
    capital = fallbackCapital
    # Retrieve live account capital and apply config capital as a cap
    acctReqId = app.reqAccountCapital()
    accountCapital = app.waitForAccountCapital(acctReqId)
    if accountCapital is not None:
        utils.log(f"Account capital (NetLiquidation): ${accountCapital:.2f}, max cap: ${maxCapital:.2f}")
        config.save_settings({"fallback_capital": round(accountCapital, 2)})
        capital = min(accountCapital, maxCapital)
        utils.log(f"Using capital: ${capital:.2f}")
    else:
        utils.log(f"Could not retrieve account capital, using fallback capital: ${fallbackCapital:.2f}")
        utils.alarm()
    
    betSize = capital * risk * betMultiplier
    utils.log(f"Using bet size: ${betSize:.2f}")

    wait_for_358_ny()
    utils.log("placing orders...")

    for order in orders:
        ticker = order["ticker"]
        action = order["action"]
        triggerPrice = order["price"]
        contract = app.createContract(ticker)
        reqId = app.nextRequestID()
        app.tickerReqIdDict[ticker] = reqId
        app.reqData(reqId, contract)

        if not app.waitForData(ticker, action, timeout=10):
            utils.log(f"No OHLC data for {ticker}, skipping order.")
            utils.alarm()
            continue

        bar = app.tickerData[reqId]

        orderId = app.nextRequestID()
        app.tickerOrderIdDict[ticker] = orderId
        if action == "LONG":
            if bar.close >= triggerPrice:
                utils.log(f"Current price {bar.close:.3f} > trigger price {triggerPrice} for LONG order on {ticker}, sending limit order")

                entryPrice = app.tickerAsk.get(reqId, bar.close)
                entryPrice = utils.getAcceptableEntry(bar.close, entryPrice)
                quantity = utils.calcQuantity(action, bar, entryPrice, limitBuffer, betSize)
                if quantity <= 0:
                    utils.log(f"Invalid quantity for {ticker}, skipping order.")
                    continue
                limitPrice = entryPrice + limitBuffer
                app.sendLimitOrder(orderId, contract, "BUY", quantity, limitPrice)
                utils.log(f"Placed LONG limit order for {ticker}: qty={quantity}, price={limitPrice}")
            else:
                utils.log(f"Current price {bar.close:.3f} < trigger price {triggerPrice} for LONG order on {ticker}, sending stop limit order")

                stopLimitQuantity = utils.calcQuantity(action, bar, triggerPrice, limitBuffer, betSize)
                if stopLimitQuantity <= 0:
                    utils.log(f"Invalid quantity for {ticker}, skipping order.")
                    continue
                stopPrice = triggerPrice
                limitPrice = triggerPrice + limitBuffer
                app.sendStopLimitOrder(orderId, contract, "BUY", stopLimitQuantity, stopPrice, limitPrice)
                utils.log(f"Placed LONG stop limit order for {ticker}: qty={stopLimitQuantity}, stopPrice={stopPrice}, limitPrice={limitPrice}")
        elif action == "SHORT":
            if bar.close <= triggerPrice:
                utils.log(f"Current price {bar.close:.3f} < trigger price {triggerPrice} for SHORT order on {ticker}, sending limit order")

                entryPrice = app.tickerBid.get(reqId, bar.close)
                entryPrice = utils.getAcceptableEntry(bar.close, entryPrice)
                quantity = utils.calcQuantity(action, bar, entryPrice, limitBuffer, betSize)
                if quantity <= 0:
                    utils.log(f"Invalid quantity for {ticker}, skipping order.")
                    continue
                limitPrice = entryPrice - limitBuffer
                app.sendLimitOrder(orderId, contract, "SELL", quantity, limitPrice)
                utils.log(f"Placed SHORT limit order for {ticker}: qty={quantity}, price={limitPrice}")
            else:
                utils.log(f"Current price {bar.close:.3f} > trigger price {triggerPrice} for SHORT order on {ticker}, sending stop limit order")
                
                stopLimitQuantity = utils.calcQuantity(action, bar, triggerPrice, limitBuffer, betSize)
                if stopLimitQuantity <= 0:
                    utils.log(f"Invalid quantity for {ticker}, skipping order.")
                    continue
                stopPrice = triggerPrice
                limitPrice = triggerPrice - limitBuffer
                app.sendStopLimitOrder(orderId, contract, "SELL", stopLimitQuantity, stopPrice, limitPrice)
                utils.log(f"Placed SHORT stop limit order for {ticker}: qty={stopLimitQuantity}, stopPrice={stopPrice}, limitPrice={limitPrice}")

    time.sleep(10)
    
    # Use the helper function to get unfilled tickers
    unfilledTickers = getUnfilledTickers(app, orders)
    utils.log(f"Unfilled tickers: {unfilledTickers}")
    while unfilledTickers and isWithinRetryWindow():
        for order in orders:
            ticker = order["ticker"]
            action = order["action"]
            triggerPrice = order["price"]
            if ticker not in unfilledTickers:
                continue
            orderId = app.tickerOrderIdDict.get(ticker)
            if orderId is None:
                continue

            contract = app.createContract(ticker)
            utils.log(f"Order for {ticker} not filled, requesting new data and replacing order...")

            # Request new bar data
            newReqId = app.nextRequestID()
            app.tickerReqIdDict[ticker] = newReqId
            app.reqData(newReqId, contract)

            if not app.waitForData(ticker, action, timeout=10):
                utils.log(f"No new OHLC data or Bid/Ask for {ticker}, skipping replace.")
                continue

            newBar = app.tickerData[newReqId]

            # Calculate filled quantity and capital used so far
            filledQty = app.orderFilledDict.get(orderId, 0)
            avgFillPrice = app.orderAvgFillPrice.get(orderId, 0)
            stopValue = newBar.low
            if action == "SHORT":
                stopValue = newBar.high
            
            dollarRisk = abs(avgFillPrice - stopValue) * filledQty

            # Calculate remaining bet size
            totalBetSize = capital * risk * betMultiplier
            remainingBetSize = totalBetSize - dollarRisk
            if remainingBetSize <= 0:
                utils.log(f"No remaining risk for {ticker}, skipping replace.")
                continue


            entryPrice = newBar.close
            if action == "LONG":
                entryPrice = app.tickerAsk.get(newReqId, newBar.close)
            elif action == "SHORT":
                entryPrice = app.tickerBid.get(newReqId, newBar.close)
            entryPrice = utils.getAcceptableEntry(newBar.close, entryPrice)
            newQty = utils.calcQuantity(action, newBar, entryPrice, limitBuffer, remainingBetSize)
            if newQty <= 0:
                utils.log(f"No remaining quantity {newQty} for {ticker}, skipping replace.")
                continue

            status = app.getOrderStatus(orderId)
            if status == "Filled":
                utils.log(f"Order for {ticker} filled.")
                continue

            if action == "LONG":
                if newBar.close > triggerPrice:
                    if app.orderIdTypeDict.get(orderId, "") == "STP LMT":
                        app.cancelOrder(orderId)
                        if not app.waitForCancelOrder(orderId, timeout=10):
                            utils.log(f"failed to cancel stop limit order for {ticker}, skipping limit order.")
                            continue

                        orderId = app.nextRequestID()
                        app.tickerOrderIdDict[ticker] = orderId

                        newLimitPrice = entryPrice + limitBuffer
                        app.sendLimitOrder(orderId, contract, "BUY", newQty, newLimitPrice)
                        utils.log(f"Replaced LONG limit order for {ticker}: qty={newQty}, price={newLimitPrice}")
                    else:
                        newLimitPrice = entryPrice + limitBuffer
                        app.sendLimitOrder(orderId, contract, "BUY", newQty, newLimitPrice)
                        utils.log(f"Replaced LONG limit order for {ticker}: qty={newQty}, price={newLimitPrice}")
                else:
                    utils.log(f"Current price {newBar.close} is below trigger price {triggerPrice} for LONG order on {ticker}, skipping.")
            elif action == "SHORT":
                if newBar.close < triggerPrice:
                    if app.orderIdTypeDict.get(orderId, "") == "STP LMT":
                        app.cancelOrder(orderId)
                        if not app.waitForCancelOrder(orderId, timeout=10):
                            utils.log(f"failed to cancel stop limit order for {ticker}, skipping limit order.")
                            continue

                        orderId = app.nextRequestID()
                        app.tickerOrderIdDict[ticker] = orderId
                        
                        newLimitPrice = entryPrice - limitBuffer
                        app.sendLimitOrder(orderId, contract, "SELL", newQty, newLimitPrice)
                        utils.log(f"Replaced SHORT limit order for {ticker}: qty={newQty}, price={newLimitPrice}")
                    else:
                        newLimitPrice = entryPrice - limitBuffer
                        app.sendLimitOrder(orderId, contract, "SELL", newQty, newLimitPrice)
                        utils.log(f"Replaced SHORT limit order for {ticker}: qty={newQty}, price={newLimitPrice}")
                else:
                    utils.log(f"Current price {newBar.close} is above trigger price {triggerPrice} for SHORT order on {ticker}, skipping.")

        time.sleep(10)
        unfilledTickers = getUnfilledTickers(app, orders)

    utils.log("Cancelling remaining active orders...")
    for ticker in unfilledTickers:
        orderId = app.tickerOrderIdDict.get(ticker)
        if orderId is not None:
            utils.log(f"Cancelling order for {ticker} (orderId={orderId})")
            app.cancelOrder(orderId)
    utils.log(f"Unfilled tickers: {unfilledTickers}")

    time.sleep(5)
    app.disconnect()
    utils.log("IB API Application stopped\n")


# orders = [
#      {
#           "ticker": "AAPL",
#           "action": "LONG",
#           "price": 350.00
#      },
#      {
#           "ticker": "GOOGL",
#           "action": "SHORT",
#           "price": 150.00
#      },
# ]

# start([])
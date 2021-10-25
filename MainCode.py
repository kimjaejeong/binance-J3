# -*- coding: utf-8 -*-
"""
Created on Sun Oct 24 16:58:45 2021

@author: 아승
"""

import ccxt
import ta
import pandas as pd
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import pprint
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import *
import sys
from PyQt5 import uic


form_class = uic.loadUiType("MainGUI.ui")[0]

with open("api.txt") as f:
    lines = f.readlines()
    api_key = lines[0].strip()
    secret = lines[1].strip()
    
binance = ccxt.binance(config={'apiKey':api_key,'secret':secret,'enableRateLimit':True,'options':{'defaultType': 'future'}})
balance = binance.fetch_balance(params={"type":"future"})
markets = binance.load_markets()

class MainWindow(QMainWindow, form_class):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        
        
        self.fig = plt.Figure()
        self.canvas = FigureCanvas(self.fig)
        layout = self.ChartLayout
        layout.addWidget(self.canvas)
        self.layout = layout

        

        self.TradeButton.clicked.connect(self.TradeStart)
        self.CoinListWidget.itemSelectionChanged.connect(self.CoinSearch)

        
    def openPosition(self,name,marketprice,amount,ordertype):
        usd = float(balance['USDT']['free'])
        usd = 1000 #test (지갑잔고)
        price = float(marketprice)
        lev = self.LeverageSpinBox.value()
        
        #사용가능 자산 없으면 주문 x
        if usd == 0:
            return
        
        #하나도 못살 돈이면 주문 x
        orderamount = (usd*lev)/price * amount
        if orderamount == 0:
            return
    
        
        if ordertype == "short":
            orderamount = orderamount*-1
        
        print("주문 가능 수량 : ",orderamount)
        #################################################
        #주문 orderamount만큼 생성
        if orderamount > 0:
            # order = binance.create_market_buy_order(symbol=name,amount=orderamount)
            print("long으로 주문")
        else:
            # order = binance.create_market_sell_order(symbol=name,amount=orderamount)
            print("short으로 주문")
        #################################################
        return
        
        
    def closePosition(self,name):
        balance = binance.fetch_balance(params={"type":"future"})
        # 현재 포지션
        positions = balance['info']['positions']
        closeAmount = .0
        
        for position in positions:
            if position["symbol"] == name:
                closeAmount = float(position["positionAmt"])*-1
        
        # 청산주문
        print("청산주문 수량 : ",closeAmount)
        #################################################
        #주문 closeAmount만큼 생성
        if closeAmount > 0:
            # order = binance.create_market_buy_order(symbol=name,amount=orderamount)
            print("long으로 주문")
        else:
            # order = binance.create_market_sell_order(symbol=name,amount=orderamount)
            print("short으로 주문")
        
        #################################################
        return
    
    def CoinSearch(self):
        self.fig.clear()
        priceData = binance.fetch_ohlcv(str(self.CoinListWidget.currentItem().text()),str(self.TimeComboBox.currentText()))
        df = pd.DataFrame(priceData, columns=['datetime','open','high','low','close','volume'])
        df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
        df.set_index('datetime', inplace = True)
        
        #조건식 설정
        
        bol_h = ta.volatility.bollinger_hband(df['close'])
        bol_l = ta.volatility.bollinger_lband(df['close'])
        bol_m = (bol_h+bol_l)/2
        
        
        chart = self.fig.add_subplot(111)
        
        
        
        chart.plot(df['close'],c='k')
        chart.plot(bol_h,c='r',label = 'Bolinger High')
        chart.plot(bol_m,c='g',label = 'Bolinger Mid')
        chart.plot(bol_l,c='b',label = 'Bolinger Low')
        
        chart.set_title(str(self.CoinListWidget.currentItem().text())+', '+str(self.TimeComboBox.currentText()))
        chart.legend()
        
        self.canvas.draw()
        
    def Searching(self):
        markets = binance.load_markets()
        for markets in markets.keys():
            if markets.endswith("USDT"):
                priceData = binance.fetch_ohlcv(markets,str(self.TimeComboBox.currentText()))
                df = pd.DataFrame(priceData, columns=['datetime','open','high','low','close','volume'])
                #조건식 설정
                bol_h = ta.volatility.bollinger_hband(df['close'])
                bol_l = ta.volatility.bollinger_lband(df['close'])
                bol_m = (bol_h+bol_l)/2
                price = float(binance.fetch_ticker(markets)['last'])
                gap = 100.
                if price > float(bol_m[499]):
                    gap = price - float(bol_l[499])
                else:
                    gap = price - float(bol_h[499])
                    
                print("gap : ",gap)
                if gap < 0:
                    self.CoinListWidget.addItem(markets)               
        return

    def TradeStart(self):
        
        symbol = str(self.CoinComboBox.currentText())
        market = binance.market(symbol)



        amount = float(self.AmountSpinBox.value()/100)

        btc = binance.fetch_ticker(symbol)
        print("현재가 : ", btc['last'])

        self.Searching()
        # self.openPosition(symbol,btc['last'],amount,'long')
        # self.closePosition("BTCUSDT")
    
    
    



if __name__ == "__main__":
    app = QApplication(sys.argv)
    MainWindow = MainWindow()
    MainWindow.show()
    app.exec_()
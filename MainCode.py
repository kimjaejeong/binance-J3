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
import win32con, win32api, win32gui
import threading, schedule, time


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
        
        self.Trading = False
        self.Calculating = False
        self.fig = plt.Figure()
        self.canvas = FigureCanvas(self.fig)
        layout = self.ChartLayout
        layout.addWidget(self.canvas)
        self.layout = layout
        
        self.kakao_opentalk_name = '코인알리미'
        self.hwndMain = win32gui.FindWindow( None, self.kakao_opentalk_name)
        self.hwndEdit = win32gui.FindWindowEx( self.hwndMain, None, "RICHEDIT50W", None)
        self.hwndListControl = win32gui.FindWindowEx( self.hwndMain, None, "EVA_VH_ListControl_Dblclk", None)

        
        self.TradeButton.setStyleSheet("background-color: rgb(0, 255, 0)")
        self.StatusLabel.setStyleSheet("color: rgb(255, 85, 0)")
        self.TradeButton.clicked.connect(self.TradeStart)
        self.TradeButton_2.clicked.connect(self.Sorting)
        self.CoinListWidget.itemSelectionChanged.connect(self.CoinSearch)
        self.CoinListWidget_2.itemSelectionChanged.connect(self.CoinSearch15m)

    
    def kakao_sendtext(self,text):
        win32api.SendMessage(self.hwndEdit, win32con.WM_SETTEXT, 0, text)
        self.SendReturn(self.hwndEdit)

    # # 엔터
    def SendReturn(self,hwnd):
        win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
        time.sleep(0.5)
        win32api.PostMessage(hwnd, win32con.WM_KEYUP, win32con.VK_RETURN, 0)       
    

    def openPosition(self,name,marketprice,amount,ordertype):
        usd = float(balance['USDT']['free'])
        usd = 1000 #test (지갑잔고 실제로는 없애야하는 부분)
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
        
        
    def CoinSearch15m(self):
        self.fig.clear()
        priceData = binance.fetch_ohlcv(str(self.CoinListWidget_2.currentItem().text()),'15m')
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
        
        chart.set_title(str(self.CoinListWidget_2.currentItem().text())+', 15m')
        chart.legend()
        
        self.canvas.draw()
        
    def Searching(self):
        if self.Calculating:
            return
        self.Calculating = True
        if self.Trading == False:
            self.Calculating = False
            return
        self.CoinListWidget.clear()
        markets = binance.load_markets()
        for markets in markets.keys():
            if markets.endswith("USDT"):
                priceData = binance.fetch_ohlcv(markets,str(self.TimeComboBox.currentText()))
                df = pd.DataFrame(priceData, columns=['datetime','open','high','low','close','volume'])
                #조건식 설정
                bol_h = ta.volatility.bollinger_hband(df['close'])
                bol_l = ta.volatility.bollinger_lband(df['close'])
                bol_m = (bol_h+bol_l)/2
                price = 0.
                if  binance.fetch_ticker(markets)['last'] is None:
                    self.Calculating = False
                    print("none")
                    return
                else:
                    price = float(binance.fetch_ticker(markets)['last'])
                
                gap = 100.
                if price > float(bol_m[len(bol_m)-1]):
                    gap = price - float(bol_l[len(bol_m)-1])
                else:
                    gap = price - float(bol_h[len(bol_m)-1])
                print("gap : ",gap)
                if gap < 0:
                    self.CoinListWidget.addItem(markets)           
        self.Calculating = False
        return
    
    def Sorting(self):
        if self.Calculating:
            return
        self.Calculating = True
        if self.Trading == False:
            self.Calculating = False
            return
        self.CoinListWidget_2.clear()
        items = []
        buysell = 'buy'
        types = []
        volumes = []
        for x in range(self.CoinListWidget.count()-1):
            items.append(self.CoinListWidget.item(x).text())
        for item in items:
            priceData = binance.fetch_ohlcv(item,'15m')
            df = pd.DataFrame(priceData, columns=['datetime','open','high','low','close','volume'])
            #조건식 설정
            bol_h = ta.volatility.bollinger_hband(df['close'])
            bol_l = ta.volatility.bollinger_lband(df['close'])
            bol_m = (bol_h+bol_l)/2
            price = float(binance.fetch_ticker(item)['last'])
            gap = 100.

            volumeInc = float(df['volume'][len(bol_m)-1]) / float(df['volume'][len(bol_m)-2])
            if price > float(bol_m[len(bol_m)-1]):
                gap = price - float(bol_l[len(bol_m)-1])
                buysell = 'Short'
            else:
                gap = price - float(bol_h[len(bol_m)-1])
                buysell = 'Long'
            print("15m gap : ",gap)
            print("volumeInc : ",volumeInc)
            if gap < 0:
                if volumeInc > 1:
                    item = QListWidgetItem(item)
                    item.setBackground(QtGui.QColor('red'))
                    self.CoinListWidget_2.addItem(item)
                    types.append(buysell + '!!')
                    volumes.append(round(volumeInc,1))
                    
                else:
                    item = QListWidgetItem(item)
                    item.setBackground(QtGui.QColor('white'))
                    self.CoinListWidget_2.addItem(item)    
                    types.append(buysell)
                    volumes.append(round(volumeInc,1))
                  
        self.Calculating = False
        total_text = ''
        title = '탐지된 종목 소팅 순서'
        for idx, data in enumerate(range(self.CoinListWidget_2.count())):
            text = '\n' + str(idx + 1) + ": " + self.CoinListWidget_2.item(idx).text() + ', '+ types[idx]+", VL : "+str(volumes[idx])
            total_text = total_text + text
        kakao_text = title + '\n' + total_text
        self.kakao_sendtext(kakao_text)
        return

    def TradeStart(self):
        if self.Trading:
            self.Trading = False
            self.TradeButton.setText("조회 시작")
            print("조회중지됨")
            self.TradeButton.setStyleSheet("background-color: rgb(0, 255, 0)")
            self.StatusLabel.setText("미조회중")
            self.StatusLabel.setStyleSheet("color: rgb(255, 85, 0)")
        else:
            self.Trading = True
            self.TradeButton.setText("조회 중지")
            print("시작됨")
            self.TradeButton.setStyleSheet("background-color: rgb(255, 85, 0)")
            self.StatusLabel.setText("조회중")
            self.StatusLabel.setStyleSheet("color: rgb(0, 0, 255)")
            
            # self.Searching_thread1 = threading.Timer(180,self.CoinSearching1)
            # self.Searching_thread1.daemon=True
            # self.Searching_thread1.start()
            
            # self.Searching_thread2 = threading.Timer(20,self.CoinSearching2)
            # self.Searching_thread2.daemon=True
            # self.Searching_thread2.start()
            
        
        # symbol = str(self.CoinComboBox.currentText())
        # market = binance.market(symbol)



        # amount = float(self.AmountSpinBox.value()/100)

        # btc = binance.fetch_ticker(symbol)
        # print("현재가 : ", btc['last'])
        # print(binance.fetch_ticker('BTCUSDT'))
        self.Searching()
        # self.openPosition(symbol,btc['last'],amount,'long')
        # self.closePosition("BTCUSDT")
    
    
 
    # def CoinSearching1(self):
    #     while self.Calculating:
    #         time.sleep(1)
        
    #     print("searching1h")
    #     self.Calculating = True
    #     self.Searching()
    #     time.sleep(60)
    #     print("time passed")
    #     self.Sorting()
    #     time.sleep(10)
    #     self.Calculating = False
        
 
    # def CoinSearching2(self):
    #     time.sleep(2)
    #     while self.Calculating:
    #         time.sleep(1)
        
    #     self.Calculating = True
    #     self.Sorting()
    #     time.sleep(7)
    #     self.Calculating = False

    



if __name__ == "__main__":
    app = QApplication(sys.argv)
    MainWindow = MainWindow()
    MainWindow.show()
    app.exec_()
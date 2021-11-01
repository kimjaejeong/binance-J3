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

from MainGUI import Ui_MainWindow


with open("api.txt") as f:
    lines = f.readlines()
    api_key = lines[0].strip()
    secret = lines[1].strip()
    
binance = ccxt.binance(config={'apiKey':api_key,'secret':secret,'enableRateLimit':True,'options':{'defaultType': 'future'}})
balance = binance.fetch_balance(params={"type":"future"})
markets = binance.load_markets()



class MainWindow(QMainWindow, Ui_MainWindow):
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

        self.calnum = 20 #볼린져 밴드 셋팅
        
        
        self.TradeButton.setStyleSheet("background-color: rgb(0, 255, 0)")
        self.StatusLabel.setStyleSheet("color: rgb(255, 85, 0)")
        self.BalanceGroupBox.setStyleSheet("background-color: rgba(170, 170, 255, 100)")
        
        
        self.TradeButton.clicked.connect(self.TradeStart)
        self.TradeButton_2.clicked.connect(self.Sorting)
        self.TradeButton_3.clicked.connect(self.Sorting2)
        self.CoinListWidget.itemClicked.connect(self.CoinSearch)
        self.CoinListWidget_2.itemClicked.connect(self.CoinSearch1h)
        self.CoinListWidget_3.itemClicked.connect(self.CoinSearch15m)
        self.CoinListWidget_3.itemDoubleClicked.connect(self.openPosition)
        self.PositionButton.clicked.connect(self.position)
        self.PositionListView.itemDoubleClicked.connect(self.closePosition)
        self.BolingerSpinBox.valueChanged.connect(self.bolingerSetting)
        self.position()

    def kakao_sendtext(self,text):
        win32api.SendMessage(self.hwndEdit, win32con.WM_SETTEXT, 0, text)
        self.SendReturn(self.hwndEdit)

    # # 엔터
    def SendReturn(self,hwnd):
        win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
        time.sleep(0.5)
        win32api.PostMessage(hwnd, win32con.WM_KEYUP, win32con.VK_RETURN, 0)       

    def openPosition(self):
        if self.CoinListWidget_3.currentItem().text() == "탐지된 종목 없음":
            return
        name = self.CoinListWidget_3.currentItem().text()
        amount = float(self.AmountSpinBox.value())/100
        marketprice = float(binance.fetch_ticker(name)['last'])
        ordertype = 'long'
        
        priceData = binance.fetch_ohlcv(name,'15m')
        df = pd.DataFrame(priceData, columns=['datetime','open','high','low','close','volume'])
        #조건식 설정
        bol_m = df['close'].rolling(window=self.calnum).mean()
        
        if marketprice < float(bol_m[len(bol_m)-1]):
            ordertype = 'long'
        else:
            ordertype = 'short'
        
        usd = float(balance['USDT']['free'])
        price = float(marketprice)
        lev = self.LeverageSpinBox.value()
        
        print(name+","+str(marketprice)+"에 주문"+ordertype)
        
        #사용가능 자산 없으면 주문 x
        if usd == 0:
            return
        
        #하나도 못살 돈이면 주문 x
        orderamount = (usd*lev)/price * amount
        if orderamount == 0:
            return
    
        
        if ordertype == "short":
            orderamount = orderamount*-1

        market_tmp = binance.market(name)
        print("주문 가능 수량 : ",orderamount)
        #################################################
        resp = binance.fapiPrivate_post_leverage({
            'symbol': market_tmp['id'],
            'leverage': lev
        })
        print("resp: ", resp)
        #주문 orderamount만큼 생성
        if orderamount > 0:
            order = binance.create_market_buy_order(symbol=name,amount=abs(orderamount))
            print("long으로 주문")
        else:
            order = binance.create_market_sell_order(symbol=name,amount=abs(orderamount))
            print("short으로 주문")
        #################################################
        self.position()
        return
        
        
    def closePosition(self):
        if self.PositionListView.currentItem().text() == "보유 포지션 없음":
            return
        temp = self.PositionListView.currentItem().text().split('|')
        name = temp[1]
        print(name)
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
            order = binance.create_market_buy_order(symbol=name,amount=abs(closeAmount))
            print("long으로 주문")
        else:
            order = binance.create_market_sell_order(symbol=name,amount=abs(closeAmount))
            print("short으로 주문")
        
        #################################################
        self.position()
        return
    
    
    def position(self):
        balance = binance.fetch_balance(params={"type":"future"})
        self.TotalLabel.setText(str(balance['USDT']['total']))
        self.UsedLabel.setText(str(balance['USDT']['used']))
        self.FreeLabel.setText(str(balance['USDT']['free']))
        self.PositionListView.clear()
        # 현재 포지션
        positions = balance['info']['positions']
        
        for position in positions:
            if float(position["positionAmt"]) != 0:
                item = "종목 :"+"|"+position["symbol"]+"|"+"  수량 :"+position["positionAmt"]+"  손익 :"+position["unrealizedProfit"]
                if float(position["unrealizedProfit"]) >= 0:
                    item = QListWidgetItem(item)
                    item.setBackground(QtGui.QColor(199,84,80,100))
                    self.PositionListView.addItem(item)
                else:
                    item = QListWidgetItem(item)
                    item.setBackground(QtGui.QColor('skyblue'))
                    self.PositionListView.addItem(item)
        if self.PositionListView.count() == 0:
            print("보유 포지션 없음")
            self.PositionListView.addItem("보유 포지션 없음")
        
    
    def CoinSearch(self):
        self.fig.clear()
        priceData = binance.fetch_ohlcv(str(self.CoinListWidget.currentItem().text()),str(self.TimeComboBox.currentText()))
        df = pd.DataFrame(priceData, columns=['datetime','open','high','low','close','volume'])
        df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
        df.set_index('datetime', inplace = True)
        
        #조건식 설정
        
        ma = df['close'].rolling(window=self.calnum).mean()
        bol_h = ma + 2*df['close'].rolling(window=self.calnum).std()
        bol_l = ma - 2*df['close'].rolling(window=self.calnum).std()
        bol_m = ma
        
        
        chart = self.fig.add_subplot(111)
        
        
        
        chart.plot(df['close'],c='k')
        chart.plot(bol_h,c='r',label = 'Bolinger High')
        chart.plot(bol_m,c='g',label = 'Bolinger Mid')
        chart.plot(bol_l,c='b',label = 'Bolinger Low')
        
        chart.set_title(str(self.CoinListWidget.currentItem().text())+', '+str(self.TimeComboBox.currentText()))
        chart.legend()
        
        self.canvas.draw()
        
        
    def CoinSearch1h(self):
        self.fig.clear()
        priceData = binance.fetch_ohlcv(str(self.CoinListWidget_2.currentItem().text()),'1h')
        df = pd.DataFrame(priceData, columns=['datetime','open','high','low','close','volume'])
        df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
        df.set_index('datetime', inplace = True)
        
        #조건식 설정
        
        ma = df['close'].rolling(window=self.calnum).mean()
        bol_h = ma + 2*df['close'].rolling(window=self.calnum).std()
        bol_l = ma - 2*df['close'].rolling(window=self.calnum).std()
        bol_m = ma
        
        
        chart = self.fig.add_subplot(111)
        
        
        
        chart.plot(df['close'],c='k')
        chart.plot(bol_h,c='r',label = 'Bolinger High')
        chart.plot(bol_m,c='g',label = 'Bolinger Mid')
        chart.plot(bol_l,c='b',label = 'Bolinger Low')
        
        chart.set_title(str(self.CoinListWidget_2.currentItem().text())+', 1h')
        chart.legend()
        
        self.canvas.draw()
        
        
    def CoinSearch15m(self):
        if self.CoinListWidget_3.currentItem().text()== "탐지된 종목 없음":
            return
        self.fig.clear()
        priceData = binance.fetch_ohlcv(str(self.CoinListWidget_3.currentItem().text()),'15m')
        df = pd.DataFrame(priceData, columns=['datetime','open','high','low','close','volume'])
        df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
        df.set_index('datetime', inplace = True)
        
        #조건식 설정
        
        ma = df['close'].rolling(window=self.calnum).mean()
        bol_h = ma + 2*df['close'].rolling(window=self.calnum).std()
        bol_l = ma - 2*df['close'].rolling(window=self.calnum).std()
        bol_m = ma
        
        
        chart = self.fig.add_subplot(111)
        
        
        
        chart.plot(df['close'],c='k')
        chart.plot(bol_h,c='r',label = 'Bolinger High')
        chart.plot(bol_m,c='g',label = 'Bolinger Mid')
        chart.plot(bol_l,c='b',label = 'Bolinger Low')
        
        chart.set_title(str(self.CoinListWidget_3.currentItem().text())+', 15m')
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
        progress = 0
        self.SearchingProgressBar.setValue(progress)
        self.StatusLabel_2.setStyleSheet("color: rgb(255, 85, 0)")
        self.StatusLabel_2.setText('Searghing')
        markets = binance.load_markets()
        for markets in markets.keys():
            progress += 1
            self.SearchingProgressBar.setValue(progress)
            if markets.endswith("USDT"):
                priceData = binance.fetch_ohlcv(markets,str(self.TimeComboBox.currentText()))
                df = pd.DataFrame(priceData, columns=['datetime','open','high','low','close','volume'])
                #조건식 설정
                ma = df['close'].rolling(window=self.calnum).mean()
                bol_h = ma + 2*df['close'].rolling(window=self.calnum).std()
                bol_l = ma - 2*df['close'].rolling(window=self.calnum).std()
                bol_m = ma
                
                price = 0.
                if  binance.fetch_ticker(markets)['last'] is None:
                    self.Calculating = False
                    self.SearchingProgressBar.setValue(100)
                    return
                else:
                    price = float(binance.fetch_ticker(markets)['last'])
                
                gap = 100.
                if price > float(bol_m[len(bol_m)-1]):
                    gap = price - float(bol_h[len(bol_m)-1])
                else:
                    gap = price - float(bol_l[len(bol_m)-1])
                if gap < 0:
                    self.CoinListWidget.addItem(markets)           
        self.Calculating = False
        self.SearchingProgressBar.setValue(100)
        return
    
    def Sorting(self):
        if self.Calculating:
            return
        self.Calculating = True
        if self.Trading == False:
            self.Calculating = False
            return
        self.CoinListWidget_2.clear()
        self.SearchingProgressBar.setValue(0)
        progress = 0
        items = []
        buysell = 'buy'
        types = []
        volumes = []
        self.StatusLabel_2.setStyleSheet("color: rgb(255, 85, 0)")
        self.StatusLabel_2.setText('1st Sorting')
        for x in range(self.CoinListWidget.count()):
            items.append(self.CoinListWidget.item(x).text())
        for item in items:
            progress += 2
            self.SearchingProgressBar.setValue(progress)
            priceData = binance.fetch_ohlcv(item,'1h')
            df = pd.DataFrame(priceData, columns=['datetime','open','high','low','close','volume'])
            #조건식 설정
            ma = df['close'].rolling(window=self.calnum).mean()
            bol_h = ma + 2*df['close'].rolling(window=self.calnum).std()
            bol_l = ma - 2*df['close'].rolling(window=self.calnum).std()
            bol_m = ma
            price = float(binance.fetch_ticker(item)['last'])
            gap = 100.

            volumeInc = float(df['volume'][len(bol_m)-1]) / float(df['volume'][len(bol_m)-2])
            if price > float(bol_m[len(bol_m)-1]):
                gap = price - float(bol_h[len(bol_m)-1])
                buysell = 'Short'
            else:
                gap = price - float(bol_l[len(bol_m)-1])
                buysell = 'Long'
            if gap < 0:
                if volumeInc > 1:
                    item = QListWidgetItem(item)
                    item.setBackground(QtGui.QColor('yellow'))
                    self.CoinListWidget_2.addItem(item)
                    types.append(buysell + '!!')
                    volumes.append(round(volumeInc,1))
                    
                else:
                    item = QListWidgetItem(item)
                    item.setBackground(QtGui.QColor('white'))
                    self.CoinListWidget_2.addItem(item)    
                    types.append(buysell)
                    volumes.append(round(volumeInc,1))
                  
        self.SearchingProgressBar.setValue(100)            
        self.Calculating = False
        self.Sorting2()
        return
    
    
    def Sorting2(self):
        if self.Calculating:
            return
        self.Calculating = True
        if self.Trading == False:
            self.Calculating = False
            return
        if self.CoinListWidget_2.count() == 0:
            return
        self.SearchingProgressBar.setValue(0)
        self.CoinListWidget_3.clear()
        progress = 0
        items = []
        buysell = 'buy'
        types = []
        volumes = []
        trend = 1
        self.StatusLabel_2.setStyleSheet("color: rgb(255, 85, 0)")
        self.StatusLabel_2.setText('2nd Sorting')
        for x in range(self.CoinListWidget_2.count()):
            items.append(self.CoinListWidget_2.item(x).text())
        for item in items:
            progress += 5
            self.SearchingProgressBar.setValue(progress)
            priceData = binance.fetch_ohlcv(item,'15m')
            df = pd.DataFrame(priceData, columns=['datetime','open','high','low','close','volume'])
            #조건식 설정
            ma = df['close'].rolling(window=self.calnum).mean()
            bol_h = ma + 2*df['close'].rolling(window=self.calnum).std()
            bol_l = ma - 2*df['close'].rolling(window=self.calnum).std()
            bol_m = ma
            price = float(binance.fetch_ticker(item)['last'])
            gap = 100.

            volumeInc = float(df['volume'][len(bol_m)-1]) / float(df['volume'][len(bol_m)-2])
            if price > float(bol_m[len(bol_m)-1]):
                gap = price - float(bol_h[len(bol_m)-1])
                buysell = 'Short'
            else:
                gap = price - float(bol_l[len(bol_m)-1])
                buysell = 'Long'
            print("15m gap : ",gap)
            print("volumeInc : ",volumeInc)
            if gap < 0:
                trend = self.VolumeSpinBox.value()
                if volumeInc > trend:
                    item = QListWidgetItem(item)
                    if buysell == 'Long':
                        item.setBackground(QtGui.QColor('green'))
                    else:
                        item.setBackground(QtGui.QColor('red'))
                    self.CoinListWidget_3.addItem(item)
                    types.append(buysell + '가능성 높음')
                    volumes.append(round(volumeInc,1))
                    
                # else:
                #     item = QListWidgetItem(item)
                #     item.setBackground(QtGui.QColor('white'))
                #     self.CoinListWidget_3.addItem(item)    
                #     types.append(buysell)
                #     volumes.append(round(volumeInc,1))
        self.SearchingProgressBar.setValue(100)      
        self.StatusLabel_2.setStyleSheet("color: rgb(0, 0, 255)")
        self.StatusLabel_2.setText('검색 완료')
        self.Calculating = False
        
        
        
        
        total_text = ''
        title = '탐지된 종목 리스트'
        for idx, data in enumerate(range(self.CoinListWidget_3.count())):
            text = '\n' + str(idx + 1) + ": " + self.CoinListWidget_3.item(idx).text() + ', '+ types[idx]+", VL : "+str(volumes[idx])
            total_text = total_text + text
        kakao_text = title + '\n' + total_text
        
        if self.CoinListWidget_3.count() == 0:
            print("탐지된 종목 없음")
            self.CoinListWidget_3.addItem("탐지된 종목 없음")
            return
        self.kakao_sendtext(kakao_text)
        print(kakao_text)
        self.position()
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

    

    def bolingerSetting(self):
        self.calnum = self.BolingerSpinBox.value()
        print("볼린져 밴드 설정 변경됨")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    MainWindow = MainWindow()
    MainWindow.show()
    app.exec_()
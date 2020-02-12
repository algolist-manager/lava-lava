import pandas as pd
import requests
import json
from datetime import datetime, timedelta
from ast import literal_eval
import numpy as np
import matplotlib.pyplot as plt
from krxpricereader import krxpricereader
import finance_util
import numpy_financial as npf
from datamanager import datamanager


class backtester():
    """
    order와 data를 받아서 backtest를 돌린다.
    order, data : input이면서 instance 변수.
    portfolio, cash_expense, portfolio_value, porfolio_growth, stocks_return, portfolio_return, irr_return, cum_return :
    instance 내부에서 만드는 변수
    """
    def __init__(self, order): ## 여기서의 order는 거래 날짜만 표시해둠.
        self.order = order
        fromdate = self.order.index[0]
        todate = self.order.index[-1]
        self.data = dict()
        price_data = pd.read_pickle('../Database/10year.pickle')
        for stock in self.order.columns:
            self.data[stock] = price_data[price_data['short_code']==stock]['close'].loc[fromdate:todate].copy()


    def get_portfolio(self):
        order_tmp = self.order.copy()
        for col in order_tmp.columns:
            new = []
            for idx in range(len(order_tmp[col])):
                new.append(sum(order_tmp[col][:idx + 1]))
            order_tmp[col] = new
        self.portfolio = order_tmp

        return self.portfolio

    def get_cash_expense(self):
        order_tmp = self.order.copy()
        data_tmp = self.data.copy()
        close_price_list = []
        for code in order_tmp.columns:
            close_prices = list(data_tmp[code])
            close_price_list.append(close_prices)
        df_close = pd.DataFrame(close_price_list).T

        cash_expense = []
        for i in range(len(order_tmp)): ### 여기에서 버그가 상당히 자주 발생한다. order와 data의 양식이 항상 잘 맞지 않기 때문이다.
            stocks = np.array(order_tmp.iloc[i])
            prices = np.array(df_close.iloc[i])
            cash = stocks.dot(prices)
            cash_expense.append(cash)

        self.cash_expense = pd.DataFrame(cash_expense, index=order_tmp.index, columns=['cash_expense'])

        return self.cash_expense

    def get_portfolio_value(self):
        order_tmp = self.order.copy()
        data_tmp = self.data.copy()
        portfolio = self.get_portfolio()
        close_price_list = []
        for code in portfolio.columns:
            close_prices = list(data_tmp[code])
            close_price_list.append(close_prices)
        df_close = pd.DataFrame(close_price_list).T

        value_list = []
        for i in range(len(portfolio)):
            stocks = np.array(portfolio.iloc[i])
            prices = np.array(df_close.iloc[i])
            value = stocks.dot(prices)
            value_list.append(value)
        self.portfolio_value = pd.DataFrame(value_list, index=order_tmp.index, columns=['portfolio_value'])

        return self.portfolio_value

    def get_porfolio_growth(self):
        portfolio_value = self.get_portfolio_value()
        shift1 = portfolio_value['portfolio_value'].shift(1)
        shift0 = portfolio_value['portfolio_value']
        portfolio_growth = pd.DataFrame(index=portfolio_value.index, columns=['portfolio_growth'])
        for i in range(len(portfolio_value)):
            portfolio_growth.iloc[i, 0] = shift0[i] / shift1[i]
        portfolio_growth = (portfolio_growth - 1) * 100
        self.portfolio_growth = portfolio_growth

        return self.portfolio_growth

    def get_stocks_return(self):
        order_tmp = self.order.copy()
        data_tmp = self.data.copy()
        stocks_return_list = []
        for code in order_tmp.columns:
            stock = data_tmp[code]
            return_stock = stock / stock.shift(1)
            return_stock = (return_stock - 1) * 100
            stocks_return_list.append(return_stock)

        stocks_return = pd.DataFrame(stocks_return_list).T

        stocks_return.columns = finance_util.naming_return(order_tmp.columns)
        stocks_return.index = order_tmp.index
        self.stocks_return = stocks_return

        return self.stocks_return

    def get_portfolio_return(self):
        order_tmp = self.order.copy()
        portfolio = self.get_portfolio()
        df_return = self.get_stocks_return()

        wgt_return_list = [np.nan]
        for i in range(1, len(portfolio.index)):
            sum_stocks = np.array([portfolio.iloc[i]]).sum()
            wgt = np.array(portfolio.iloc[i]) / sum_stocks
            returns = np.array(df_return.iloc[i])
            wgt_return = wgt.dot(returns)
            wgt_return_list.append(wgt_return)

        self.portfolio_return = pd.DataFrame(wgt_return_list, index=order_tmp.index, columns=['portfolio_return'])

        return self.portfolio_return

    def get_irr_return(self):
        order_tmp = self.order.copy()
        portfolio_value = self.get_portfolio_value()
        cash_expense = self.get_cash_expense()
        irr_list = []
        irr_return = []
        for idx, val in enumerate(list(portfolio_value['portfolio_value'])):
            money = cash_expense['cash_expense'][idx]
            irr_list.append(-money)
            return_measure = npf.irr(irr_list[:-1] + [irr_list[-1] + val])
            irr_return.append(return_measure)

        self.irr_return = pd.DataFrame(irr_return, index=order_tmp.index, columns=['irr_return'])

        return self.irr_return

    def get_cum_return(self):
        order_tmp = self.order.copy()
        irr = self.get_irr_return() + 1
        cum_return = [np.nan]
        for i in range(2, len(irr) + 1):
            cum_return.append(finance_util.seq_mul(list(irr['irr_return'])[1:i]))

        self.cum_return = pd.DataFrame(cum_return, index=order_tmp.index, columns=['cum_return'])

        return self.cum_return

    def run(self):
        """
        portfolio, cash_expense, portfolio_value, portfolio_growth, stocks_return, portfolio_return, irr_return, cum_return
        이 모든 정보를 다 얻는 것.
        """
        portfolio = self.get_portfolio()
        cash_expense = self.get_cash_expense()
        stocks_return = self.get_stocks_return()
        portfolio_value = self.get_portfolio_value()
        portfolio_return = self.get_portfolio_return()
        portfolio_growth = self.get_porfolio_growth()
        irr_return = self.get_irr_return()
        cum_return = self.get_cum_return()

        self.summary = pd.concat([portfolio, cash_expense, stocks_return, portfolio_value,
                                  portfolio_return, portfolio_growth, irr_return, cum_return], axis=1)

        return self.summary


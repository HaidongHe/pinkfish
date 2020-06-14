"""
stategy
---------
"""

# other imports
import pandas as pd
import matplotlib.pyplot as plt
import datetime
from talib.abstract import *

# project imports
import pinkfish as pf

pf.DEBUG = False


class Strategy():

    def __init__(self, symbol, capital, start, end, use_adj=False,
                 period=7, max_positions=4):
        self._symbol = symbol
        self._capital = capital
        self._start = start
        self._end = end
        self._use_adj = use_adj
        self._period = period
        self._max_positions = max_positions
        
    def _algo(self):
        """ Algo:
            1. The SPY is above its 200-day moving average
            2. The SPY closes at a X-day low, buy some shares.
               If it falls further, buy some more, etc...
            3. If the SPY closes at a X-day high, sell your entire long position.
        """
        self._tlog.initialize(self._capital)

        for i, row in enumerate(self._ts.itertuples()):

            date = row.Index.to_pydatetime()
            high = row.high; low = row.low; close = row.close; 
            end_flag = pf.is_last_row(self._ts, i)
            shares = 0

            # buy
            if (self._tlog.num_open_trades() < self._max_positions
                and close > row.sma200
                and close == row.period_low
                and not end_flag):
                
                # calc number of shares
                cash = self._tlog._cash / (self._max_positions - self._tlog.num_open_trades())
                shares = self._tlog.calc_shares(price=close, cash=cash)
                # enter buy in trade log
                self._tlog.enter_trade(date, close, shares)                

            # sell
            elif (self._tlog.num_open_trades() > 0
                  and (close == row.period_high
                       or end_flag)):

                # enter sell in trade log
                shares = self._tlog.exit_trade(date, close)

            if shares > 0:
                pf.DBG("{0} BUY  {1} {2} @ {3:.2f}".format(
                    date, shares, self._symbol, close))
            elif shares < 0:
                pf.DBG("{0} SELL {1} {2} @ {3:.2f}".format(
                    date, -shares, self._symbol, close))
            else:
                pass  # HOLD

            # record daily balance
            self._dbal.append(date, high, low, close, self._tlog.shares)

    def run(self):
        self._ts = pf.fetch_timeseries(self._symbol)
        self._ts = pf.select_tradeperiod(self._ts, self._start,
                                         self._end, use_adj=False)

        # Add technical indicator: 200 day sma
        sma200 = SMA(self._ts, timeperiod=200)
        self._ts['sma200'] = sma200

        # Add technical indicator: X day high, and X day low
        period_high = pd.Series(self._ts.close).rolling(self._period).max()
        period_low = pd.Series(self._ts.close).rolling(self._period).min()
        self._ts['period_high'] = period_high
        self._ts['period_low'] = period_low
        
        self._ts, self._start = pf.finalize_timeseries(self._ts, self._start)
        
        self._tlog = pf.TradeLog()
        self._dbal = pf.DailyBal()

        self._algo()

    def get_logs(self, merge_trades=False):
        """ return DataFrames """
        self.rlog = self._tlog.get_log_raw()
        self.tlog = self._tlog.get_log(merge_trades)
        self.dbal = self._dbal.get_log(self.tlog)
        return self.rlog, self.tlog, self.dbal

    def get_stats(self):
        # call get_logs before calling this function
        stats = pf.stats(self._ts, self.tlog, self.dbal, self._capital)
        return stats

def summary(strategies, *metrics):
    """ Stores stats summary in a DataFrame.
        stats() must be called before calling this function """
    index = []
    columns = strategies.index
    data = []
    # add metrics
    for metric in metrics:
        index.append(metric)
        data.append([strategy.stats[metric] for strategy in strategies])

    df = pd.DataFrame(data, columns=columns, index=index)
    return df


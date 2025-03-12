import pandas as pd
import numpy as np
from statsmodels.tsa.stattools import adfuller
import warnings
import pandas as pd
warnings.filterwarnings("ignore", category=RuntimeWarning, message="divide by zero encountered in log")

from .direction import Direction
from .order import Order

class Strategy:
    def __init__(self, significance=0.025, lookback=30):
        self.significance = significance
        self.lookback = lookback
        self.prices = {}
        self.orders = {}
        self.price_df = pd.DataFrame()
        self.positions_df = pd.DataFrame()
    
    def check_cointegration(self):
        keys = self.price_df.dropna(axis=1).columns

        if len(keys) < 2:
            return []  

        n = len(keys)
        cointegrated_pairs = []
        
        for i in range(n):
            R1 = self.price_df[keys[i]]
            for j in range(i + 1, n):
                R2 = self.price_df[keys[j]]
                X = np.vstack([np.ones(self.lookback), R2]).T
                b, a = np.linalg.lstsq(X, R1, rcond=None)[0]
                residuals = R1 - (b * R2 + a)
                if np.allclose(np.var(residuals),0): 
                    continue
                p_value = adfuller(residuals)[1]
                if p_value < self.significance:
                    cointegrated_pairs.append((keys[i], keys[j]))
        
        return cointegrated_pairs  
    
    def generate_trading_signal(self, data):
        df = pd.DataFrame(data).T[['bid_price', 'ask_price', 'mid_price']]
        df.columns = ['bid_price', 'ask_price', 'mid_price']
        self.price_df = pd.concat([self.price_df, df[['mid_price']].T], axis=0).ffill().tail(self.lookback)

        if len(self.price_df) < self.lookback:
            return
        
        cointegrated_pairs = self.check_cointegration()
        price_matrix = self.price_df.values
        spread_matrix = price_matrix[:, None, :] - price_matrix[:, :, None]
        mean_spread = np.mean(spread_matrix, axis=0)
        var_spread = np.var(spread_matrix, axis=0)
        z_scores = (spread_matrix[-1] - mean_spread) / (np.sqrt(var_spread) + 1e-8)
        
        self.orders.clear()
        
        if self.positions_df.empty:
            self.positions_df = pd.DataFrame(0, index=[0], columns=self.price_df.columns)
        missing_assets = set(self.price_df.columns) - set(self.positions_df.columns)
        if missing_assets:
            for asset in missing_assets:
                self.positions_df[asset] = 0
                
        for (s1, s2) in cointegrated_pairs:
            idx1, idx2 = self.price_df.columns.get_loc(s1), self.price_df.columns.get_loc(s2)
            z_score = z_scores[idx1, idx2]
            
            conditions_buy = (self.positions_df[s1].iloc[-1] == 0) & (z_score > 1)
            conditions_sell = (self.positions_df[s1].iloc[-1] == 0) & (z_score < -1)
            conditions_close_buy = (self.positions_df[s1].iloc[-1] == 1) & (z_score < 0)
            conditions_close_sell = (self.positions_df[s1].iloc[-1] == -1) & (z_score > 0)
            
            self.positions_df[s1] = np.where(conditions_buy, 1, 
                                       np.where(conditions_sell, -1, 
                                       np.where(conditions_close_buy | conditions_close_sell, 0, 
                                       self.positions_df[s1].iloc[-1])))
            
            if conditions_buy.any():
                self.orders[s1] = Order(asset=s1, price=df.loc[s1, 'bid_price'], direction=Direction.BUY, quantity=1)
                self.orders[s2] = Order(asset=s2, price=df.loc[s2, 'bid_price'], direction=Direction.SELL, quantity=1)
            elif conditions_sell.any():
                self.orders[s2] = Order(asset=s2, price=df.loc[s2, 'bid_price'], direction=Direction.BUY, quantity=1)
                self.orders[s1] = Order(asset=s1, price=df.loc[s1, 'bid_price'], direction=Direction.SELL, quantity=1)
            elif conditions_close_buy.any() or conditions_close_sell.any():
                self.orders[s1] = Order(asset=s1, price=df.loc[s1, 'bid_price'], direction=Direction.SELL, quantity=1)
                self.orders[s2] = Order(asset=s2, price=df.loc[s2, 'bid_price'], direction=Direction.BUY, quantity=1)
        
        return self.orders
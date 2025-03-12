import pandas as pd
import numpy as np
from tqdm import tqdm

from .direction import Direction

class Backtest:
    def __init__(self, fx_data, strategy, filename, stop_event):
        self.fx_data = fx_data
        self.strategy = strategy
        self.filename = filename
        self.stop_event = stop_event
        self.results = pd.DataFrame()
        self.hanging_orders = {}
        
    def save_results(self):
        if not self.results.empty:
            self.results.to_csv(self.filename, index=True)
    
    
    def execute(self):
        print("Starting backtest...")
        timestamps = pd.Index(sorted(set().union(*[self.fx_data[fx].index for fx in self.fx_data])))
        
        with tqdm(total=len(timestamps), desc="Backtest Progress", ncols=100, dynamic_ncols=True) as pbar:
            for timestamp in timestamps:
                if self.stop_event and self.stop_event.is_set():
                    print("Backtest stopped by user.")
                    break
                
                row_data = {fx: {'bid_price': self.fx_data[fx].loc[timestamp, 'bid_price'], 
                                 'ask_price': self.fx_data[fx].loc[timestamp, 'ask_price'], 
                                 'mid_price': (self.fx_data[fx].loc[timestamp, 'bid_price'] + self.fx_data[fx].loc[timestamp, 'ask_price'])/2} 
                            if timestamp in self.fx_data[fx].index 
                            else {'bid_price': np.nan, 'ask_price':np.nan, 'mid_price': np.nan} 
                            for fx in self.fx_data}
                orders = self.strategy.generate_trading_signal(row_data)
                if not orders:
                    pbar.update(1)
                    continue
                
                row_returns = {"Datetime": timestamp}
                for asset, order in orders.items():
                    if asset in self.hanging_orders:
                        entry_price = self.hanging_orders.pop(asset)
                        exit_price = order.price
                        asset_return = (exit_price - entry_price) / entry_price if order.direction == Direction.SELL else (entry_price - exit_price) / entry_price
                        row_returns[asset] = asset_return * 100
                    else:
                        self.hanging_orders[asset] = order.price
                
                self.results = pd.concat([self.results, pd.DataFrame([row_returns]).set_index("Datetime")], ignore_index=False).fillna(0)
                self.save_results()
                pbar.update(1)
        
        print("Backtest completed.")
        self.save_results()
        return pd.DataFrame(self.results)

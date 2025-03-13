import os
import glob
import zipfile
import logging
from pathlib import Path
import pandas as pd
import concurrent.futures
from histdata import download_hist_data as dl
from histdata.api import Platform as P, TimeFrame as TF

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler() 
    ]
)

class DataManager:
    def __init__(self, fx_pairs, years, folder='data'):
        self.fx_pairs = fx_pairs
        self.years = years
        self.folder = folder
    
    def check_missing_files(self):
        missing_files = []
        for pair in self.fx_pairs:
            pair_path = os.path.join(self.folder, pair)
            os.makedirs(pair_path, exist_ok=True)
            for year in self.years:
                expected_file = os.path.join(pair_path, f'{pair}_{year}.csv')
                if not os.path.exists(expected_file):
                    missing_files.append((pair, year))
        return missing_files
    
    def download_and_extract(self, pair, year):
        pair_folder = os.path.join(self.folder, pair)
        os.makedirs(pair_folder, exist_ok=True)
        all_bid_data, all_ask_data = [], []
        
        for month in range(1, 13):
            logging.debug(f"Downloading data for {pair} {year}-{month}")
            try:
                bid_zip_folder = dl(year=str(year), month=str(month).zfill(2), pair=pair, platform=P.NINJA_TRADER, time_frame=TF.TICK_DATA_BID)
                ask_zip_folder = dl(year=str(year), month=str(month).zfill(2), pair=pair, platform=P.NINJA_TRADER, time_frame=TF.TICK_DATA_ASK)                
            except Exception as e:
                logging.error(f"Failed to download bid data for {pair} {year}-{month}: {e}")
                return None
            bid_zip_folder = dl(year=str(year), month=str(month).zfill(2), pair=pair, platform=P.NINJA_TRADER, time_frame=TF.TICK_DATA_BID)
            ask_zip_folder = dl(year=str(year), month=str(month).zfill(2), pair=pair, platform=P.NINJA_TRADER, time_frame=TF.TICK_DATA_ASK)
            
            if bid_zip_folder and os.path.exists(bid_zip_folder):
                try:
                    with zipfile.ZipFile(bid_zip_folder, 'r') as zip_ref:
                        for file in zip_ref.namelist():
                            if file.endswith('.csv'):
                                bid_data = pd.read_csv(zip_ref.open(file), sep=';', header=None, usecols=[0, 1])
                                all_bid_data.append(bid_data)
                    os.remove(bid_zip_folder)
                except Exception as e:
                    logging.error(f"Error processing bid data for {pair} {year}-{month}: {e}")
            
            if ask_zip_folder and os.path.exists(ask_zip_folder):
                try:
                    with zipfile.ZipFile(ask_zip_folder, 'r') as zip_ref:
                        for file in zip_ref.namelist():
                            if file.endswith('.csv'):
                                ask_data = pd.read_csv(zip_ref.open(file), sep=';', header=None, usecols=[0, 1])
                                all_ask_data.append(ask_data)
                    os.remove(ask_zip_folder)
                except Exception as e:
                    logging.error(f"Error processing ask data for {pair} {year}-{month}: {e}")
        
        if all_bid_data and all_ask_data:
            bid_data = pd.concat(all_bid_data, ignore_index=True)
            ask_data = pd.concat(all_ask_data, ignore_index=True)
            bid_data.columns = ['Datetime', 'bid_price']
            ask_data.columns = ['Datetime', 'ask_price']
            
            try:
                bid_data['Datetime'] = pd.to_datetime(bid_data['Datetime'], format='%Y%m%d %H%M%S%f')
                ask_data['Datetime'] = pd.to_datetime(ask_data['Datetime'], format='%Y%m%d %H%M%S%f')
            except Exception as e:
                logging.error(f"Error parsing datetime for {pair} {year}: {e}")
                return
            
            merged_data = pd.merge(bid_data, ask_data, on='Datetime', how='inner')
            merged_file_path = os.path.join(pair_folder, f'{pair}_{year}.csv')
            merged_data.to_csv(merged_file_path, index=False)
            logging.info(f"Successfully saved {pair}_{year}.csv")
    
    def download_missing_files(self):
        missing_files = self.check_missing_files()
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:  # Use ThreadPoolExecutor for I/O tasks
            futures = {executor.submit(self.download_and_extract, pair, year): (pair, year) for pair, year in missing_files}
            
            for future in concurrent.futures.as_completed(futures):
                pair, year = futures[future]
                try:
                    future.result()  # Ensure any exception inside threads is caught
                    logging.info(f"Successfully downloaded and processed {pair} {year}")
                except Exception as e:
                    logging.error(f"Error processing {pair} {year}: {e}")
    
    def load_fx_data(self):
        logging.info("Loading FX data...")
        fx_data = {}
        for pair in self.fx_pairs:
            pair_path = os.path.join(self.folder, pair)
            files_to_process = []
            for year in self.years:
                file = os.path.join(pair_path, f'{pair}_{year}.csv')
                if os.path.exists(file) :
                    files_to_process.append(file)
            # files_to_process = [file for year in self.years for file in glob.glob(os.path.join(pair_path, f'*{year}*.csv'))]
            
            logging.info(f"Processing : {pair}")  
            all_data_frames = []

            for file in files_to_process:
                df = pd.read_csv(
                    file, 
                    names=['Datetime', 'bid_price', 'ask_price'], 
                    skiprows=1, 
                    dtype={'bid_price': 'float64', 'ask_price': 'float64'}, 
                    low_memory=False
                )
                all_data_frames.append(df)

            all_data = pd.concat(all_data_frames, ignore_index=True)              
            # all_data = pd.concat(
            #     (pd.read_csv(file, names=['Datetime', 'bid_price', 'ask_price'], skiprows=1, dtype={'bid_price': 'float64', 'ask_price': 'float64'}, low_memory=False)
            #      for file in files_to_process), ignore_index=True)
            all_data['Datetime'] = pd.to_datetime(all_data['Datetime'])
            all_data.set_index('Datetime', inplace=True)
            fx_data[pair] = all_data
        logging.info("Finished loading FX data.")
        return fx_data

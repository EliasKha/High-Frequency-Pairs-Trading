from dataclasses import dataclass
from enum import Enum
from histdata import download_hist_data as dl
from histdata.api import Platform as P, TimeFrame as TF
import zipfile
import concurrent.futures
import pandas as pd
import logging
logging.basicConfig(level=logging.DEBUG)




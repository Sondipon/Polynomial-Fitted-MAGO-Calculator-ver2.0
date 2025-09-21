import os
import csv
import time as tm
import subprocess
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import pyhecdss
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from Read_OracleDB_Windows import get_cursor, read_daily_data


def main():
    try:
        # Test breakpoint stage data extraction
        # FAKI75 = read_breakpoint_data(station_id = 'FAKI75+H', start_time = '20-Jul-2025', end_time = '21-Jul-2025', header_name = 'FAKI75', datum='NAVD88')
        # print(FAKI75)
        # FAKI75 = read_breakpoint_data(station_id = 'FAKI75+H', start_time = '20-Jul-2025', end_time = '21-Jul-2025', header_name = 'FAKI75', datum='NGVD29')
        # print(FAKI75)
        
        # Test daily stage data extraction
        # FAKI75_MQ907 = read_daily_data(dbkey = 'MQ907', start_time = '01-Jul-2025', end_time = '21-Jul-2025',header_name = 'FAKI75', datum='NGVD29')
        # print (FAKI75_MQ907)
        FAKI75_MQ907 = read_daily_data(dbkey = 'MQ907', start_time = '01-Jul-2025', end_time = '21-Jul-2025', header_name = 'FAKI75', datum='NAVD88')
        # print (FAKI75_MQ907)
        FAKI75_MQ907.to_csv('FAKI75_1.csv', index=True)
        
        # # Test daily pumping rate data extraction
        # S487_P = read_daily_data(dbkey = 'AM695', start_time = '01-Jul-2025', end_time = '21-Jul-2025', header_name = 'S487_P')
        # print (S487_P)
        # # Test breakpoint pumping rate data extraction
        # S487_P = read_breakpoint_data(station_id = 'S487-P-Q', start_time = '20-Jul-2025', end_time = '23-Jul-2025', header_name = 'S487_P')
        # print(S487_P)        
        
        # # Test daily flow data extraction
        # S61_S = read_daily_data(dbkey = '91625', start_time = '01-Jul-2025', end_time = '21-Jul-2025', header_name = 'S61_S_Q')
        # print (S61_S)
        # # Test breakpoint pumping rate data extraction
        # S61_S = read_breakpoint_data(station_id = 'S61-S-Q', start_time = '20-Jul-2025', end_time = '23-Jul-2025', header_name = 'S61_S_Q')
        # print(S61_S)
        
    except Exception as e:
        print(e)

if __name__ == "__main__":
    main()


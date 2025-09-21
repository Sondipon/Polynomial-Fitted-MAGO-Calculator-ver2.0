# -*- coding: utf-8 -*-
"""
Created on Tue Jul 22 07:40:51 2025

@author: sonpaul
"""
import pandas as pd
import numpy as np
import oracledb
from datetime import datetime

oracledb.init_oracle_client() # to get thick client

def get_cursor():
    oracledb.init_oracle_client() # for windows version
    host = "wrepdb"
    port = 1521
    sid = "wrep"
    username = "pub"
    password = "pub"

    dsn = oracledb.makedsn(host, port, sid=sid)
    connection = oracledb.connect(user=username, password=password, dsn=dsn)
    cursor = connection.cursor()
    return connection, cursor

def read_breakpoint_data(station_id, start_time, end_time, header_name, datum=None):
    """
    Reads stage breakpoint data from TIME_SERIES_VW based on the selected datum.
    
    Parameters:
        cursor (cx_Oracle.Cursor): Oracle DB cursor
        station_id (str): Station ID to query (it is the 'Source Timeseries' from DBHYDRO Insight)
        start_time (str): Start date in 'DD-MON-YYYY'
        end_time (str): End date in 'DD-MON-YYYY'
        datum (str): None (for flow/pumping rate) or 'NAVD88' or 'NGVD29' (default: None)
        
    Returns:
        pd.DataFrame: DataFrame with date_time and value columns
        
    Additional info:
        🔍 Columns in TIME_SERIES_VW:
                STATION_ID
                DATE_TIME
                VALUE
                VALUE29
                VALUE88
                TAG
                QA_FLAG
                APPROVED_BY
    """
    # Connect to DBHYdro database
    connection, cursor = get_cursor()
    
    # Determine which value column to use
    if datum is None:
        value_column = 'VALUE'
    elif datum.upper() == 'NAVD88':
        value_column = 'VALUE88'
    elif datum.upper() == 'NGVD29':
        value_column = 'VALUE29'
    else:
        raise ValueError(f"Unsupported datum: {datum}")

    # # Define SQL
    # sql = f"""
        # SELECT DATE_TIME, NVL({value_column}, -901) AS VALUE
        # FROM TIME_SERIES_VW
        # WHERE STATION_ID = :station_id
        # AND DATE_TIME BETWEEN TO_DATE(:start_date, 'DD-MON-YYYY') AND TO_DATE(:end_date, 'DD-MON-YYYY')
        # ORDER BY DATE_TIME
    # """

    # # Execute the query
    # cursor.execute(sql, station_id=station_id, start_date=start_time, end_date=end_time)

    # # Load results into a DataFrame
    # df = pd.DataFrame(cursor.fetchall(), columns=['date_time', header_name])
    
    # cursor.close()
    # connection.close()

    # return df
    
    # Define SQL
    sql = f"""
        SELECT DATE_TIME, NVL({value_column}, -99999) AS VALUE
        FROM TIME_SERIES_VW
        WHERE STATION_ID = :station_id
        AND DATE_TIME BETWEEN TO_DATE(:start_date, 'DD-MON-YYYY') AND TO_DATE(:end_date, 'DD-MON-YYYY')
        ORDER BY DATE_TIME
    """

    # Execute the query
    cursor.execute(sql, station_id=station_id, start_date=start_time, end_date=end_time)

    # Load results into a DataFrame
    df = pd.DataFrame(cursor.fetchall(), columns=['DATETIME', header_name])
    df['DATETIME'] = pd.to_datetime(df['DATETIME'])  # Convert to datetime if needed
    df.set_index('DATETIME', inplace=True)
    df[header_name] = df[header_name].replace(-99999, np.nan)
    
    cursor.close()
    connection.close()

    return df    

def read_daily_data(dbkey, start_time, end_time, header_name, datum=None):
    """
    Reads stage breakpoint data from TIME_SERIES_VW based on the selected datum.
    
    Parameters:
        cursor (cx_Oracle.Cursor): Oracle DB cursor
        dbkey (str): DBKEY to query (it is the 'Timeseries ID' from DBHYDRO Insight)
        start_time (str): Start date in 'DD-MON-YYYY'
        end_time (str): End date in 'DD-MON-YYYY'
        datum (str): None (for flow/pumping rate) or 'NAVD88' or 'NGVD29' (default: None)
        
    Returns:
        pd.DataFrame: DataFrame with date_time and value columns
        
    Additional info:
        🔍 Columns in DM_DAILY_DATA_VW:
                DBKEY
                DAILY_DATE
                CODE
                VALUE
                VALUE29
                VALUE88
                VALUE2020
                REVISION_DATE
                USER_OSID
                DERIVED_FROM
                DERIVED_METHOD
                DAILY_RESULT_DATA_ID
                INDEX_ID
                QUALITY_CODE
                STATION_ID
                SITE
                DATA_TYPE
    """
    # Connect to DBHYDRO database
    connection, cursor = get_cursor()
    
    # Determine which value column to use
    if datum is None:
        value_column = 'VALUE'
    elif datum.upper() == 'NAVD88':
        value_column = 'VALUE88'
    elif datum.upper() == 'NGVD29':
        value_column = 'VALUE29'
    else:
        raise ValueError(f"Unsupported datum: {datum}")
    
    
    # # define sql
    # sql = f"""
        # SELECT DAILY_DATE, NVL({value_column}, -901) AS VALUE
        # FROM DM_DAILY_DATA_VW
        # WHERE DBKEY = :dbkey
        # AND DAILY_DATE BETWEEN TO_DATE(:start_date, 'DD-MON-YYYY') AND TO_DATE(:end_date, 'DD-MON-YYYY')
        # ORDER BY DAILY_DATE
    # """
    # cursor.execute(sql, DBKEY=dbkey, start_date=start_time, end_date=end_time)    

    # # Load results into a DataFrame
    # df = pd.DataFrame(cursor.fetchall(), columns=['daily_date', header_name])
    # cursor.close()
    # connection.close()
    # return df
    
    # define sql
    sql = f"""
        SELECT DAILY_DATE, NVL({value_column}, -99999) AS VALUE
        FROM DM_DAILY_DATA_VW
        WHERE DBKEY = :dbkey
        AND DAILY_DATE BETWEEN TO_DATE(:start_date, 'DD-MON-YYYY') AND TO_DATE(:end_date, 'DD-MON-YYYY')
        ORDER BY DAILY_DATE
    """
    cursor.execute(sql, DBKEY=dbkey, start_date=start_time, end_date=end_time)    

    # Load results into a DataFrame
    df = pd.DataFrame(cursor.fetchall(), columns=['DATE', header_name])
    df['DATE'] = pd.to_datetime(df['DATE'])  # Convert to datetime if needed
    df.set_index('DATE', inplace=True)
    df[header_name] = df[header_name].replace(-99999, np.nan)
    cursor.close()
    connection.close()
    return df    


def read_database_column_header(cursor):
    # Breakpoint data table
    cursor.execute("SELECT * FROM TIME_SERIES_VW WHERE ROWNUM = 1")
    columns = [desc[0] for desc in cursor.description]
    print("🔍 Columns in TIME_SERIES_VW:")
    for col in columns:
        print(col)
    
    # Daily mean data table
    cursor.execute("SELECT * FROM DM_DAILY_DATA_VW WHERE ROWNUM = 1")
    columns = [desc[0] for desc in cursor.description]
    print("🔍 Columns in DM_DAILY_DATA_VW:")
    for col in columns:
        print(col)


def main():
    
    # Test breakpoint stage data extraction
    FAKI75 = read_breakpoint_data(station_id = 'FAKI75+H', start_time = '12-Sep-2025', end_time = '12-Sep-2025', header_name = 'FAKI75', datum='NAVD88')
    print(FAKI75)
    
    S40H = read_breakpoint_data(station_id = 'S40-H', start_time = '12-Sep-2025', end_time = '13-Sep-2025', header_name = 'S40-H', datum='NAVD88')
    print(S40H)
    
    
    # FAKI75 = read_breakpoint_data(station_id = 'FAKI75+H', start_time = '20-Jul-2025', end_time = '21-Jul-2025', header_name = 'FAKI75', datum='NGVD29')
    # print(FAKI75)
    
    # # Test daily stage data extraction
    # FAKI75_MQ907 = read_daily_data(dbkey = 'MQ907', start_time = '01-Jul-2025', end_time = '21-Jul-2025',header_name = 'FAKI75', datum='NGVD29')
    # print (FAKI75_MQ907)
    # FAKI75_MQ907 = read_daily_data(dbkey = 'MQ907', start_time = '01-Jul-2025', end_time = '21-Jul-2025',header_name = 'FAKI75', datum='NAVD88')
    # print (FAKI75_MQ907)
    
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
    
    
if __name__ == "__main__":
    main()


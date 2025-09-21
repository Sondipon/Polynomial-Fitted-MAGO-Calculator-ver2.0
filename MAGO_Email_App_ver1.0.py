import os
import sys
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from scipy.interpolate import griddata
from scipy.spatial import Delaunay

import time as tm
import subprocess
from datetime import datetime, timedelta


import win32com.client as client
import logging

from Read_OracleDB_Windows import get_cursor, read_daily_data, read_breakpoint_data



# Create a file to log the hydrograph plotting process.
def create_log(logfile):
    # Remove all existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename=logfile,
        filemode='w'  # overwrite each run
    )

def get_date():
    try:

        dict_month = {
            '1': "Jan",
            '2': "Feb",
            '3': "Mar",
            '4': "Apr",
            '5': "May",
            '6': "Jun",
            '7': "Jul",
            '8':"Aug",
            '9': "Sep",
            '10': "Oct",
            '11': "Nov",
            '12': "Dec"}
        start = datetime.today()
        day = start.day
        month = start.month
        year = start.year
        start_datetime = f"{day:02d}-{dict_month[str(month)]}-{year}"
        
        end = datetime.today() + timedelta(days = 1)
        day = end.day
        month = end.month
        year = end.year
        end_datetime = f"{day:02d}-{dict_month[str(month)]}-{year}"
        
        return start_datetime, end_datetime
    
    except Exception as e:
        logging.error("Get header date error: {}".format(e))

def get_last_valid(df, max_back=10):
    """
    Return last valid (datetime, value) pair from df,
    searching backwards up to max_back rows.
    """
    if df.empty:
        return None, None
    
    # Look backwards up to max_back rows
    for i in range(1, max_back+1):
        if len(df) >= i:
            row = df.iloc[-i]
            val = row.values[0]
            if pd.notna(val):  # found valid value
                return row.name, val
    return None, None  # if no valid value found

def send_email(df, subject="Daily MAGO Report using MAGO Curves"):
    outlook = client.Dispatch("Outlook.Application")
    message = outlook.CreateItem(0)
    # message.To = "tdessale@sfwmd.gov; sonpaul@sfwmd.gov; zli@sfwmd.gov"
    message.To = "sonpaul@sfwmd.gov"
    # message.CC = "sonpaul@sfwmd.gov"
    message.Subject = subject
    
    # Build custom HTML table
    table_html = "<h3 style='font-family:Consolas;'>MAGO Evaluation Report</h3>"    
    table_html += "<table style='border-collapse:collapse; font-family:Consolas; font-size:10pt;'>"

    # Header row
    table_html += "<tr>"
    for col in df.columns:
        table_html += f"<th style='border:1px solid #888; padding:4px; max-width:150px; word-wrap:break-word; white-space:normal;'>{col}</th>"
    table_html += "</tr>"

    # Data rows
    for idx, row in df.iterrows():
        table_html += "<tr>"
        for item in row:
            # Convert to string for safe comparison
            if pd.isna(item) or str(item).lower() == "nan":
                val = ""
            else:
                val = item
            table_html += f"<td style='border:1px solid #ccc; padding:4px; text-align:center;'>{val}</td>"
        table_html += "</tr>"


    # Add to email body
    message.HTMLBody = f"""
    <html>
      <body>
        {table_html}
      </body>
    </html>
    """

    message.Send()
    logging.info("✅ Email report was sent successfully.")


def main():
    try:
        # Define work directory
        workdir = r"Q:\Tools_Apps\MAGO_Checks\MAGO_Curve_Check_Automation"        
        
        # Initiate log file
        logfile = os.path.join(workdir, "magoapprun.log")       
        create_log(logfile)
        
        # List of stations for MAGO calculation
        stationnames = os.path.join(workdir, "structureList.csv")
        df_sta = pd.read_csv(stationnames)
        logging.info("List of stations for MAGO calculation")
        logging.info(df_sta.to_string()) #print entire df
        logging.info(len(df_sta))
        
        # Define start and end date
        start_datetime, end_datetime = get_date()
        logging.info(f"start date:{start_datetime}, end date:{end_datetime}")
        
        # Extract data from dbhydro
        results = []
        for idx, row in df_sta.iterrows():
            structure = row["Structure"]
        
            # Get Headwater data
            HW = read_breakpoint_data(
                station_id=row["Headwater"],
                start_time=start_datetime,
                end_time=end_datetime,
                header_name=row["Headwater"],
                datum="NAVD88"
            )
        
            # Get Tailwater data
            TW = read_breakpoint_data(
                station_id=row["Tailwater"],
                start_time=start_datetime,
                end_time=end_datetime,
                header_name=row["Tailwater"],
                datum="NAVD88"
            )
        
            datetime_val, hw_val = get_last_valid(HW, max_back=10)
            _, tw_val = get_last_valid(TW, max_back=10)
        
            if datetime_val is None:
                logging.info(f"⚠️ No valid data for {structure}")
                continue
        
            # Build row dictionary
            row_result = {
                "Structure": structure,
                "Date and Time": datetime_val,
                "Headwater (ft-NAVD88)": round(hw_val,2),
                "Tailwater (ft-NAVD88)": round(tw_val,2),
                "Gates": row["Gate_No"]
            }
        
            # Add gates dynamically
            for i in range(row["Gate_No"]):
                gate_id = f"Gate{i+1}"
                gate_opening_ts = read_breakpoint_data(
                    station_id=row[gate_id],
                    start_time=start_datetime,
                    end_time=end_datetime,
                    header_name=row[gate_id],
                )
                _, gate_opening = get_last_valid(gate_opening_ts, max_back=10)
        
                if gate_opening is None:
                    logging.info(f"⚠️ No valid data for {gate_id}")
                    row_result[gate_id+" (ft)"] = "N/A"
                else:
                    row_result[gate_id+" (ft)"] = round(gate_opening,1)
        
            # Append final row for structure
            results.append(row_result)

            # print(results)
        
        # Build final dataframe
        df_bkpt_data = pd.DataFrame(results) # bkpt = breakpoint/instantaneous
        logging.info("Printing Breakpoint Data")
        logging.info(df_bkpt_data.to_string()) # print entire df
        logging.info(len(df_bkpt_data))
        
        
        
        # Reading MAGO curve dataset
        magodataset = os.path.join(workdir, "MAGO.csv")
        # Check if CSV file exists
        if not os.path.exists(magodataset):
            logging.error(f"CSV file not found at: {magodataset}")
        # Load the dataset
        df_magodataset = pd.read_csv(magodataset) 
        
        logging.info("MAGO dataset")
        logging.info(df_magodataset)
        
 
        # create predicted MAGO table
        df_predictedmago = df_bkpt_data.copy() # copy breakpoint table
        df_predictedmago['MAGO (ft)'] = None # add a column 'MAGO (ft')
        

        for idx, row in df_predictedmago.iterrows():
            structure = row['Structure']
        
            # Filter MAGO dataset for this structure
            filtered_data = df_magodataset[df_magodataset['Structure'] == structure]
            X = filtered_data[['HW_NAVD88', 'TW_NAVD88']].values
            y = filtered_data['GO_feet'].values
        
            if len(y) == 0:
                logging.warning(f"No MAGO data for {structure}")
                predicted_mago = np.array([None])
                continue
        
            min_go, max_go = y.min(), y.max()
        


            hw = row['Headwater (ft-NAVD88)']
            tw = row['Tailwater (ft-NAVD88)']
        
            try:
                # Build convex hull of gridded data
                hull = Delaunay(X)
    
                if hull.find_simplex([(hw, tw)]) >= 0:
                    # Inside gridded data → interpolate
                    predicted_mago = griddata(X, y, [(hw, tw)], method='cubic')
                    if np.isnan(predicted_mago[0]):
                        predicted_mago = griddata(X, y, [(hw, tw)], method='linear')
    
                    # Clamp numeric values inside min/max GO
                    if isinstance(predicted_mago[0], (int, float, np.floating)):
                        if predicted_mago[0] < min_go:
                            predicted_mago = np.array([min_go])
                        elif predicted_mago[0] > max_go:
                            predicted_mago = np.array([max_go])
                    zone = "Gridded data zone"
    
                else:
                    # Outside gridded data → assign < MAGO min/No MAGO
                    if hw < X[:,0].min() or tw < X[:,1].min():
                        predicted_mago = np.array([f"<{min_go}"])
                        zone = "Left of gridded data"
                    else:
                        predicted_mago = np.array(["No MAGO"])
                        zone = "Right of gridded data"
                if isinstance(predicted_mago[0], str):
                    df_predictedmago.loc[idx,'MAGO (ft)'] = predicted_mago[0]
                else:
                    df_predictedmago.loc[idx,'MAGO (ft)'] = round(predicted_mago[0], 1) # round for numeric value
                
            except Exception as e:
                logging.warning(f"{structure} interpolation failed: {e}")
                predicted_mago = np.array([None])
                zone = None
            

        
        for idx, row in df_predictedmago.iterrows():
            for i in range(1, 7):
                column_header = f"Gate{i} (ft)"
                if isinstance(row[column_header], (int, float, np.floating)) and isinstance(row["MAGO (ft)"], (int, float, np.floating)):
                    if row[column_header] > row["MAGO (ft)"]:
                        df_predictedmago.loc[idx, "MAGO Exceeded?"] = "X"
                    else:
                        df_predictedmago.loc[idx, "MAGO Exceeded?"] = ""
                else:
                    df_predictedmago.loc[idx, "MAGO Exceeded?"] = ""


        logging.info("Printing Predicted MAGO Table")
        logging.info(df_predictedmago.to_string()) # print entire df

        send_email(df_predictedmago)
        
    except Exception as e:
        logging.error(f"This is an error: {e}")
        raise
        
if __name__ == "__main__":
    main()



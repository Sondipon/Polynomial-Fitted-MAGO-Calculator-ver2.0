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


#import win32com.client as client
import logging



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



def main():
    try:
        # Define work directory
        # Determine the correct base path for accessing files
        if getattr(sys, 'frozen', False):
            workdir = sys._MEIPASS  # PyInstaller temp directory
        else:
            workdir = os.path.dirname(os.path.abspath(__file__))
        # workdir = r"Q:\Tools_Apps\MAGO_Checks\MAGO_Curve_Check_Automation"        
        
        # Initiate log file
        logfile = os.path.join(workdir, "magowebapprun.log")       
        create_log(logfile)
        
        # List of stations for MAGO calculation
        stationnames = os.path.join(workdir, "structureList.csv")
        df_sta = pd.read_csv(stationnames)
        logging.info("List of stations for MAGO calculation")
        logging.info(df_sta.to_string()) #print entire df
        logging.info(len(df_sta))
        
        
        # Reading MAGO curve dataset
        magodataset = os.path.join(workdir, "MAGO.csv")
        # Check if CSV file exists
        if not os.path.exists(magodataset):
            logging.error(f"CSV file not found at: {magodataset}")
        # Load the dataset
        df_magodataset = pd.read_csv(magodataset) 
        
        logging.info("MAGO dataset")
        logging.info(df_magodataset)
        
        # Sidebar: Structure selection
        st.sidebar.header("Select Structure")
        structurelist = df_sta['Structure'].unique()
        print(structurelist)
        selected_structure = st.sidebar.selectbox("Choose a structure:", structurelist)
        
        #Filter data for selected structure
        filtered_data = df_magodataset[df_magodataset['Structure'] == selected_structure]
        X = filtered_data[['HW_NAVD88', 'TW_NAVD88']].values
        y = filtered_data['GO_feet'].values
        if len(y) == 0:
            logging.warning(f"No MAGO data for {structure}")
        
        min_go, max_go = y.min(), y.max()
        
        st.sidebar.header("Enter HW & TW Conditions")


        #hw = st.sidebar.number_input("Headwater Level (HW)", value=current_hw, step=0.1)
        #tw = st.sidebar.number_input("Tailwater Level (TW)", value=current_tw, step=0.1)

        hw = st.sidebar.number_input("Headwater Level (HW)", min_value=float(filtered_data["HW_NAVD88"].min()), max_value=float(filtered_data["HW_NAVD88"].max()), step=0.1)
        tw = st.sidebar.number_input("Tailwater Level (TW)", min_value=float(filtered_data["TW_NAVD88"].min()), max_value=float(filtered_data["TW_NAVD88"].max()), step=0.1)

            
        
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

        except Exception as e:
            logging.error(f"This is an error: {e}")
            raise
        
        st.title("Polynomial-Fitted MAGO Calculator")
        if isinstance(predicted_mago[0], str):
            st.subheader(f"Calculated Maximum Allowable Gate Opening (MAGO) for {selected_structure}: {predicted_mago[0]}")
            # df_predictedmago.loc[idx,'MAGO (ft)'] = predicted_mago[0]
        else:
            # df_predictedmago.loc[idx,'MAGO (ft)'] = round(predicted_mago[0], 1) # round for numeric value
            st.subheader(f"Calculated Maximum Allowable Gate Opening (MAGO) for {selected_structure}: {round(predicted_mago[0], 1)} feet")
            
            
        
        # Batch Processing Section
        st.sidebar.header("Batch Processing")
        uploaded_file = st.sidebar.file_uploader("Upload CSV file with HW_NAVD88 & TW_NAVD88", type=["csv"])
        
        if uploaded_file is not None:
            try:
                
                
                input_data = pd.read_csv(uploaded_file)
                
                if {'HW_NAVD88', 'TW_NAVD88'}.issubset(input_data.columns):
                    
                    # List to store results
                    results = []
        
                    # Iterate over each row
                    for idx, row in input_data.iterrows():
                        hw = row['HW_NAVD88']
                        tw = row['TW_NAVD88']     
        
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
    
                        else:
                            # Outside gridded data → assign < MAGO min/No MAGO
                            if hw < X[:,0].min() or tw < X[:,1].min():
                                predicted_mago = np.array([f"<{min_go}"])
                            else:
                                predicted_mago = np.array(["No MAGO"])
    
                        # Append to results
                        if isinstance(predicted_mago[0], str):
                            mago = predicted_mago[0]
                        else:
                            mago = round(predicted_mago[0], 1)
                        results.append({
                            "Structure": selected_structure,
                            "HW_NAVD88": hw,
                            "TW_NAVD88": tw,
                            "MAGO (ft)": mago
                        })
        
                    # Build new DataFrame
                    df_output = pd.DataFrame(results)
        
                    # Save file name with datetime of selected structure
                    datetime = datetime.now()
                    formatted_datetime = datetime.strftime("%d-%m-%Y-%H%M")
                    output_file = f"{selected_structure}_HW_TW_MAGO_{formatted_datetime}.csv"
        
                    # Download button
                    st.download_button(
                        label="Download Processed Data",
                        data=df_output.to_csv(index=False),
                        file_name=output_file,
                        mime="text/csv"
                    )
                    st.success("Batch processing completed successfully!")
        
                else:
                    st.error("Uploaded CSV must contain 'HW_NAVD88' and 'TW_NAVD88' columns.")
            except Exception as e:
                st.error(f"Error processing file: {str(e)}")  
        
        
        # Plot interpolated surface
        fig, ax = plt.subplots()
        tw_values = np.linspace(filtered_data["TW_NAVD88"].min(), filtered_data["TW_NAVD88"].max(), 100)
        hw_values = np.linspace(filtered_data["HW_NAVD88"].min(), filtered_data["HW_NAVD88"].max(), 100)
        tw_grid, hw_grid = np.meshgrid(tw_values, hw_values)
        go_grid = griddata(X, y, (hw_grid, tw_grid), method='cubic')

        # Set colorbar range using vmin and vmax
        levels = np.arange(min_go, max_go + 0.001, 0.2)  # add tiny offset to include max_go        
        # Create contour plot
        contour = ax.contourf(tw_grid, hw_grid, go_grid, levels=levels, cmap="viridis", extend='both')
        cbar = plt.colorbar(contour, ax=ax)
        cbar.set_label("MAGO feet")  # Label for colorbar
        ax.set_xlabel("Tailwater Level (TW) feet NAVD88")
        ax.set_ylabel("Headwater Level (HW) feet NAVD88")
        ax.set_title(f"Interpolated MAGO Curve for {selected_structure}")

        # Mark user input
        ax.scatter(tw, hw, color='red', label="User Input")
        ax.legend()

        st.pyplot(fig)
        
        
    except Exception as e:
        logging.error(f"This is an error: {e}")
        raise
        
if __name__ == "__main__":
    main()








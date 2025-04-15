# Author: Roden Derveni

# Creates a web-based data visualiser by setting up a server with Flask and presenting data using Dash (in a simple table)

from   flask import Flask
from   dash  import Dash, dcc, html, Input, Output, State, dash_table, exceptions

import pandas as pd
import numpy as np

from   io import StringIO
import base64
import datetime

# To check external package versions
# from importlib.metadata import version
# for p in ['flask', 'dash', 'pandas', 'numpy']: print(f'{p} {version(p)}')

# Set fixed seed for reproducibility of randomised events
np.random.seed(12345)

# Flask server instance
server = Flask(__name__)
app    = Dash(__name__, server=server, suppress_callback_exceptions=True)


# Global variables for dataset
def ResetGlobal():
    global df, filename
    df               = None
    filename         = ""
    # This should have just been class-based
ResetGlobal() # Set the values now

# Some tester non-deterministic function
def non_det_func(data): 
    return data * np.random.random()

# The HTML state return for failed file suploads
def ErrorReturn(message):
    #      File status              Apply, Save, Upload, Clear Table
    return message,                 True,  True, False,   html.Div()

# The HTML state return for successful file uploads
def SuccessReturn(message, table):
    #      File status              Apply, Save,  Upload,  Set Table
    return message,                 False, False, False,   table

# Format visuals for data table
def dash_table_formatter(df):

    df = df.reset_index() # Give the data an index (TODO: This should be resetting with current behaviour, fix)

    # Parameters to virtualise the DashTable instance for better resource handling for very large datasets
    virtualization = (df.shape[0] > 100)
    page_action    = 'none' if virtualization else 'native'

    table = dash_table.DataTable(
        columns        = [{"name": col, "id": col} for col in df.columns], # Is only necessary because I want to show the rowID
        data           = df.to_dict('records'),
        style_table    = {'overflowX': 'auto', 'height': '400px', 'overflowY': 'scroll'},
        style_cell     = {'minWidth': '100px', 'width': '150px', 'maxWidth': '200px', \
                          'textOverflow': 'ellipsis', 'overflow': 'hidden'},
        style_header   = {'fontWeight': 'bold'},
        fixed_rows     = {'headers': True},
        virtualization = virtualization,
        page_action    = page_action,
        editable       = False # Interactivity hurts CPU
    )
    return [table]

# 'Unit test' input data
def DFTester(df):
    # If data is not at least a 1 x 1, raise error
    if df.empty or df.shape[0] < 1 or df.shape[1] < 1:
        raise ValueError("Dataset must have at least 1 row and 1 column, and a header.")
    
    # If any of data is not numerical, raise error
    if df.select_dtypes(exclude=[np.number]).shape[1] > 0:
        raise ValueError("Dataset must be entirely numerical, except for the header.")

# Apply layout of page - default stacks from top to bottom in order of initialisation
app.layout = html.Div([
    dcc.Upload(id        = 'upload-data',                     # (local) File upload search
               children  = html.Button('Upload Data File'),
               multiple  = False
    ),
    html.Div(id          = 'file-status', 
             children    = 'No file uploaded'
    ),
    html.Button('Apply Function',                            # Apply function button
                id       = 'apply-func', 
                n_clicks = 0, 
                disabled = True
    ),
    html.Button('Save Data',                                 # Save data button (as csv)
                id       = 'save-btn', 
                n_clicks = 0, 
                disabled = True
    ),
    html.Div(id='data-table-container')                      # Visible data table
])

@app.callback(
    [Output('file-status', 'children'),
     Output('apply-func', 'disabled', allow_duplicate=True),
     Output('save-btn', 'disabled'),
     Output('upload-data', 'disabled'),
     Output('data-table-container', 'children')
    ],
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    prevent_initial_call=True
)
def load_file(file_contents, uploaded_filename):
    global df, filename
    
    # Reset behaviour if a new file is uploaded on the same page
    ResetGlobal()

    if not uploaded_filename.lower().endswith('.csv'):
        return ErrorReturn(f'Error: {uploaded_filename} is not a CSV file.')

    if file_contents:
        content_type, content_string = file_contents.split(',')

        # Try to read file, and test its contents for validity
        try:
            decoded = base64.b64decode(content_string) # DataTable requires base64 data
            df = pd.read_csv(StringIO(decoded.decode('utf-8')))
            DFTester(df)
        except pd.errors.EmptyDataError:                     return ErrorReturn('Error: Uploaded file is empty.')
        except (UnicodeDecodeError, pd.errors.ParserError):  return ErrorReturn('Error: Invalid file contents.')
        except (ValueError, Exception) as e:                 return ErrorReturn(f'Error: {str(e)}')

        filename         = uploaded_filename # Needed for save_data
        table            = dash_table_formatter(df)

        return SuccessReturn(f'{uploaded_filename} uploaded successfully', table)

    return ErrorReturn('Failed to upload file') # In case something else goes wrong while parsing 

# Apply Function, and return table
@app.callback(
    [Output('apply-func', 'disabled', allow_duplicate=True),
     Output('data-table-container', 'children', allow_duplicate=True)
    ],
    Input('apply-func', 'n_clicks'),
    prevent_initial_call = True
)
def apply_function(n_clicks):
    global df
    if df is not None:
        df    = df.map(non_det_func)
        table = dash_table_formatter(df)
        return False, table
    raise exceptions.PreventUpdate # If unsuccessful, prevent further updates

# Save the current data state to a time-stamped file
@app.callback(
    [Output('apply-func', 'disabled'),
     Output('file-status', 'children', allow_duplicate=True)
    ],
    Input('save-btn', 'n_clicks'),
    prevent_initial_call = True
)
def save_data(n_clicks):
    global df, filename
    if df is not None:
        timestamp     = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        save_filename = f"{timestamp}_{filename}"
        df.to_csv(save_filename, index=False)  # Save without rowID

        return False, f"Data saved as {save_filename}"
    
    raise dash.exceptions.PreventUpdate

# Run program
if __name__ == '__main__':
    port = 8000
    app.run(port=port, debug=True)

    # or run this and find whatever port it provides
    # app.run()
    # and open "http://localhost:XXXX" directly

    # or if the default port is being used, sorry just change the port directly
    # There are ways to automate this though, just keeping it simple.
    # opening the browser automatically depends on GTK/atk nativity

    # Errors can be removed on-screen by removing `debug=True`,
    # leaving them on for stress-testing

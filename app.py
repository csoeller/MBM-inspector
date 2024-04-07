from dash import Dash, html, dcc, callback, Output, Input, State
import dash
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc # we pip installed this one
import numpy as np

import base64
import io
import json

from MBMcollection import MBMCollectionDF
# print(dash.__version__)

datasources = { 'data 1' : 'assets/240328-142406_sE_3D_U2OS_NPC_560_blank__MBM-beads.npz',
                'data 2' : 'assets/240328-105801_sB_3D_U2OS_NPC_560_blank__MBM-beads.npz' }

app = Dash(__name__, external_stylesheets=[dbc.themes.UNITED])

# at startup run with local data
# note that we make the app for now run with a "global" variable mbm
# NOTE: this will break running several tabs with different data sets
# but is deemed ok for now as a proof of concept
mbm = MBMCollectionDF(name=datasources['data 1'],
                      fileinput=datasources['data 1'],
                      plotbad=True)
beads = list(mbm.beadisgood.keys())

app.layout = html.Div(style={'padding': '2rem'},
                      children=[
                          html.H1(children='MBM Inspector', style={'textAlign':'center'}),
                          dcc.Upload(
                              id='upload-data',
                              children=html.Div([
                                  'Drag and Drop or ',
                                  html.A('Select File')
                              ]),
                              style={
                                  'width': '100%',
                                  'height': '60px',
                                  'lineHeight': '60px',
                                  'borderWidth': '1px',
                                  'borderStyle': 'dashed',
                                  'borderRadius': '5px',
                                  'textAlign': 'center',
                                  'margin': '10px'
                              },
                          ),
                          html.H3(children='FILENAME', style={'textAlign':'center'}, id='filename-label'),
                          html.P("Median Filter"),
                          html.Div( # placing it in a Div allows us to set the width as a percentage of window width
                              dcc.Slider(0, 21, 1,
                                         value=5,
                                         id='median-slider'
                                         ),
                              style={'width':'25%'}),
                          dbc.Checklist(beads, beads,
                                        inline=True,
                                        id='bead-selection'),
                          dbc.RadioItems(
                              id="axes",
                              options=["x", "y", "z"],
                              value="x",
                              inline=True,
                          ),
                          html.Button("Download JSON", id="btn_json"),
                          dcc.Download(id="download-json"),
                          dcc.Graph(id='main-graph'),
                          dcc.Graph(id='stddev-graph')
                      ])

# call back when any of the bead, axis or median filter selection changes
@callback(
    Output('main-graph', 'figure'),
    Output('stddev-graph', 'figure'),
    Input('bead-selection', 'value'),
    Input('axes','value'),
    Input('median-slider','value'),
)
def update_graph(selectedbeads,axis,median_window):
    mbm.markasgood_only(*selectedbeads)
    mbm.median_window = median_window
    mainfig = mbm.plot_tracks(axis)
    stddevfig = mbm.plot_tracks("std_%s" % axis)
    return (mainfig,stddevfig)

# call back that updates the bead list and also the filename when new data is uploaded
# updating the bead list will in turn trigger the callback above which will generate a new set of plots
@callback(
    Output('bead-selection', 'options'),
    Output('bead-selection', 'value'),
    Output('filename-label', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
    prevent_initial_call=True,
)
def update_output(contents, filename):
    global mbm
    
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    
    try:
        if 'npz' in filename:
            # Assume that the user uploaded an npz file
            mbm = MBMCollectionDF(name=filename,fileinput=io.BytesIO(decoded),
                                  plotbad=True)
    except Exception as e:
        print(e)

    options = []
    for bead in mbm.beadisgood:
        options.append(bead)

    return (options,options,filename)    

# this callback is triggered when the Download JSON button is pressed
# and generates a JSON file that is downloaded to disk
@callback(
    Output("download-json", "data"),
    Input("btn_json", "n_clicks"),
    prevent_initial_call=True,
)
def btnfunc(n_clicks):
    fname = "%s-settings.json" % mbm.name
    settings = {}
    settings['beads'] = mbm.beadisgood.copy()
    settings['Median_window'] = mbm.median_window
    settings['Filename'] = mbm.name
    return dict(content=json.dumps(settings, indent=4),filename=fname)

if __name__ == '__main__':
    app.run(debug=True)

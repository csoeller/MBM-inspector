from dash import Dash, html, dcc, callback, Output, Input, State
import dash
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc # we pip installed this one
import numpy as np
import logging

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
                          html.Div([ # placing it in a Div allows us to set the width as a percentage of window width
                              dcc.Slider(0.025, 0.2, 0.025,
                                         value=0.1,
                                         id='lowess-slider'
                                         ),
                              html.Button("Lowess Filter", id="btn_lowess"),],
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
#                          html.Div(
#                              html.Button("Lowess Filter", id="btn_lowess"),
#                              ),
                          html.Button("Download JSON Settings", id="btn_json"),
                          dcc.Download(id="download-json"),
                          dcc.Upload(
                              id='upload-json',
                              children=html.Div([
                                  'Drag and Drop or ',
                                  html.A('Select JSON Settings File')
                              ]),
                              style={
                                  'width': '30%',
                                  'height': '60px',
                                  'lineHeight': '60px',
                                  'borderWidth': '1px',
                                  'borderStyle': 'dashed',
                                  'borderRadius': '5px',
                                  'textAlign': 'center',
                                  'margin': '10px'
                              },
                              # single file to be uploaded
                              multiple=False
                          ),
                          dcc.Graph(id='main-graph'),
                          dcc.Graph(id='stddev-graph')
                      ])

# call back when any of the bead, axis or median filter selection changes
@callback(
    Output('main-graph', 'figure', allow_duplicate=True),
    Output('stddev-graph', 'figure', allow_duplicate=True),
    Input('bead-selection', 'value'),
    Input('axes','value'),
    Input('median-slider','value'),
    prevent_initial_call='initial_duplicate',
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
    Output('bead-selection', 'value', allow_duplicate=True),
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

# call back that updates the bead list from a saved JSON settings file
# updating the bead list will in turn trigger the applicable callback above which will generate a new set of plots
@callback(
    Output('bead-selection', 'value'),
    Input('upload-json', 'contents'),
    State('upload-json', 'filename'),
    prevent_initial_call=True,
)
def update_output_json(contents, filename):
    global mbm

    # print(contents)
    
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)

    if filename.endswith('.json'): # should probably also check for 'mbm-beads.npz-settings' in filename
        settings = json.loads(decoded)
        if 'beads' in settings:
            # need to add check that beads match the beads in this mbm dataset
            return [bead for bead in settings['beads'] if settings['beads'][bead]]
        else:
            logging.warn('no beads in settings')
            return dash.no_update
    else:
        logging.warn('%s is not a JSON file' % filename)
        return dash.no_update

# this callback is triggered when the Download JSON button is pressed
# and generates a JSON settings file that is downloaded to disk
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

# this callback is triggered when the lowess button is pressed
# and generates a new output that is new graphs that will
# now contain a lowess smoothed version of the mean curve
@callback(
    Output('main-graph', 'figure'),
    Output('stddev-graph', 'figure'),
    Input("btn_lowess", "n_clicks"),
    State('bead-selection', 'value'),
    State('axes','value'),
    State('median-slider','value'),
    State('lowess-slider','value'),
    prevent_initial_call=True,
)
def update_graph_lowess(n_clicks,selectedbeads,axis,median_window,lowess_fraction):
    mbm.markasgood_only(*selectedbeads)
    mbm.median_window = median_window
    mainfig = mbm.plot_tracks(axis,lowess_frac=lowess_fraction)
    stddevfig = mbm.plot_tracks("std_%s" % axis)
    return (mainfig,stddevfig)



if __name__ == '__main__':
    app.run(debug=True)

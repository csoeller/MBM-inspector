from dash import Dash, html, dcc, callback, Output, Input, State
import dash
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc # we pip installed this one

import base64
import io

from MBMcollection import MBMCollectionDF
# print(dash.__version__)

datasources = { 'data 1' : 'assets/240328-142406_sE_3D_U2OS_NPC_560_blank__MBM-beads.npz',
                'data 2' : 'assets/240328-105801_sB_3D_U2OS_NPC_560_blank__MBM-beads.npz' }

app = Dash(__name__, external_stylesheets=[dbc.themes.COSMO])
#app = Dash(__name__)

# temporary way of running with local data
mbm = MBMCollectionDF(filename='assets/240328-142406_sE_3D_U2OS_NPC_560_blank__MBM-beads.npz',
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
                          dbc.Checklist(beads, beads,
                                        inline=True,
                                        id='bead-selection'),
                          dbc.RadioItems(
                              id="axes",
                              options=["x", "y", "z"],
                              value="x",
                              inline=True,
                          ),
                          dcc.Graph(id='main-graph'),
                          dcc.Graph(id='stddev-graph')
                      ])

@callback(
    Output('main-graph', 'figure'),
    Output('stddev-graph', 'figure'),
    Input('bead-selection', 'value'),
    Input('axes','value')
)
def update_graph(selectedbeads,axis):
    mbm.markasgood_only(*selectedbeads)
    mainfig = mbm.plot_tracks(axis)
    stddevfig = mbm.plot_tracks("std_%s" % axis)
    return (mainfig,stddevfig)

# @callback(
#     Output('bead-selection', 'options'),
#     Output('bead-selection', 'value'),
#     Input('dropdown', 'value'),
# )
# def update_dataset(datasource_key):
#     global mbm
#     mbm = MBMCollectionDF(filename=datasources[datasource_key],
#                       plotbad=True)
#     options = []
#     for bead in mbm.beadisgood:
#         options.append(bead)

#     return (options,options)

@callback(
    Output('bead-selection', 'options'),
    Output('bead-selection', 'value'),
    Output('filename-label', 'children'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
)
def update_output(contents, filename):
    global mbm
    
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    
    try:
        if 'npz' in filename:
            # Assume that the user uploaded an npz file
            mbm = MBMCollectionDF(filename=io.BytesIO(decoded),
                                  plotbad=True)
    except Exception as e:
        print(e)

    options = []
    for bead in mbm.beadisgood:
        options.append(bead)

    return (options,options,filename)    

if __name__ == '__main__':
    app.run(debug=True)

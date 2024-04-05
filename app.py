from dash import Dash, html, dcc, callback, Output, Input, State
import dash
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc # we pip installed this one
import numpy as np

import base64
import io

from MBMcollection import MBMCollectionDF
# print(dash.__version__)

datasources = { 'data 1' : 'assets/240328-142406_sE_3D_U2OS_NPC_560_blank__MBM-beads.npz',
                'data 2' : 'assets/240328-105801_sB_3D_U2OS_NPC_560_blank__MBM-beads.npz' }

app = Dash(__name__, external_stylesheets=[dbc.themes.JOURNAL])
#app = Dash(__name__)

# temporary way of running with local data
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
                          html.Div(
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
                          dcc.Download(id="download-dataframe-json"),
                          dcc.Graph(id='main-graph'),
                          dcc.Graph(id='stddev-graph')
                      ])

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

@callback(
    Output("download-dataframe-json", "data"),
    Input("btn_json", "n_clicks"),
    prevent_initial_call=True,
)
def btnfunc(n_clicks):
    fname = "%s-settings.json" % mbm.name
    dfsettings = pd.DataFrame(mbm.beadisgood, index=np.array([0]))
    dfsettings['median_window'] = mbm.median_window
    dfsettings['Filename'] = mbm.name
    return dcc.send_data_frame(dfsettings.to_json,fname)


if __name__ == '__main__':
    app.run(debug=True)

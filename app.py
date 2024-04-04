from dash import Dash, html, dcc, callback, Output, Input
import dash
import plotly.express as px
import pandas as pd
import dash_bootstrap_components as dbc # we pip installed this one

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
                          html.P("Select dataset:"),
                          dcc.Dropdown(
                              id="dropdown",
                              options=list(datasources.keys()),
                              value=list(datasources.keys())[0],
                              clearable=False,
                          ),
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

@callback(
    Output('bead-selection', 'options'),
    Output('bead-selection', 'value'),
    Input('dropdown', 'value'),
)
def update_dataset(datasource_key):
    global mbm
    mbm = MBMCollectionDF(filename=datasources[datasource_key],
                      plotbad=True)
    options = []
    for bead in mbm.beadisgood:
        options.append(bead)

    return (options,options)

if __name__ == '__main__':
    app.run(debug=True)

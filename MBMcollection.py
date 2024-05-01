###############################################
### A class definition for basic MBM processing
### and analysis
###############################################
import numpy as np
import pandas as pd
from warnings import warn

def interp_bead(tnew, bead, customdict=None, extrapisnan=False):
    ibead = {}
    if customdict is None:
        for i,axis in enumerate(['x','y','z']):
            if extrapisnan:
                ibead[axis] = np.interp(tnew, bead['tim'], 1e9*bead['pos'][:,i], right=np.nan) # everything in nm
            else:
                ibead[axis] = np.interp(tnew, bead['tim'], 1e9*bead['pos'][:,i]) # everything in nm
            #ibead[axis][tnew>bead['tim'].max()] = 0
    else:
        for key,value in customdict.items():
            if extrapisnan:
                ibead[key] = np.interp(tnew, bead['tim'], bead[value], right=np.nan)
            else:
                ibead[key] = np.interp(tnew, bead['tim'], bead[value])
            #ibead[key][tnew>bead['tim'].max()] = 0

    ibead['t'] = tnew
    return ibead

def stdev_bead(bead,samplewindow=9):
    sbead = {}
    for i,axis in enumerate(['x','y','z']):
        sbead["std_%s" % axis] = pd.Series(1e9*bead['pos'][:,i]).rolling(window=samplewindow).std() # everything in nm
    sbead['std'] = np.sqrt(sbead['std_x']**2 + sbead['std_y']**2 + sbead['std_z']**2)
    sbead['tim'] = bead['tim']
    return sbead

def stdev_beads(beads,samplewindow=9):
    sbeads = {}
    for bead in beads:
        sbeads[bead] = stdev_bead(beads[bead],samplewindow=samplewindow)
    return sbeads

def interp_sbeads(sbeads,extrapisnan=False):
    return interp_beads(sbeads,customdict=dict(std='std',std_x='std_x',
                                               std_y='std_y',std_z='std_z'),
                        extrapisnan=extrapisnan)

def interp_beads(beads,customdict=None,extrapisnan=False):
    mint = 1e6
    for bead in beads:
        mincur = beads[bead]['tim'].min()
        if mincur < mint:
            mint = mincur

    maxt = 0
    for bead in beads:
        maxcur = beads[bead]['tim'].max()
        if maxcur > maxt:
            maxt = maxcur

    # here we may need some checks if some bead tracks are a lot shorter than others (does this occur)?
    # this could lead to issues with interpolation unless these go to zero
    # so watch out for cases like that and consider code tweaks if needed

    # note that by default we interpolate all tracks onto a 1 s spaced time series
    # we could make the interpolation sampling rate a varaibale but for now 1 s spacing seems ok
    tnew = np.arange(np.round(mint),np.round(maxt)+1)
    ibeads = {}

    for bead in beads:
        ibeads[bead] = interp_bead(tnew,beads[bead],customdict=customdict,extrapisnan=extrapisnan)

    return ibeads

import pandas as pd
def df_from_interp_beads(beads,customdict=None):
    ibeads = interp_beads(beads,customdict=customdict,extrapisnan=True)
    dictbeads = {}
    for axis in ['x','y','z','std_x','std_y','std_z','std']:
        dictbeads[axis] = {}
        
    for bead in ibeads:
        for axis in ['x','y','z']:
            dictbeads[axis][bead] = ibeads[bead][axis]
        t = ibeads[bead]['t'] # this is actually always the same t

    dfbeads = {}
    for axis in ['x','y','z']:
        dfbeads[axis] = pd.DataFrame(dictbeads[axis],index=t)

    sbeads = stdev_beads(beads)
    sibeads = interp_sbeads(sbeads,extrapisnan=True)
    for bead in sibeads:
        for axis in ['std_x','std_y','std_z','std']:
            dictbeads[axis][bead] = sibeads[bead][axis]
    for axis in ['std_x','std_y','std_z','std']:
        dfbeads[axis] = pd.DataFrame(dictbeads[axis],index=t)
    
    return dfbeads


# the code below would only be used if we implement caching some of the calculations
# for now not used but leave in for now if we run into performance issues at some stage
import hashlib
import json
# we use this function to generate a unique hash from a dictionary
# see also https://stackoverflow.com/questions/16092594/how-to-create-a-unique-key-for-a-dictionary-in-python
# this will be used further below to check if our cached value of the mean is still usable
def hashdict(dict):
    hashkey = hashlib.sha1(json.dumps(dict, sort_keys=True).encode()).hexdigest()
    return hashkey
# we use this function to generate a unique hash from a dataframe
# need to check if this is necessary or if it is ok to make the the filter settimngs into a unique hash for caching
def hashdf(df):
    return hashlib.sha1(pd.util.hash_pandas_object(df).values).hexdigest()
    

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
# pandas dataframe based handling of MBM bead trajectories
# the good support for missing values, averaging across columns and rolling filters
# makes this quite a neat way to handle the basic calculations that we typically need
class MBMCollectionDF(object): # collection based on dataframe objects
    def __init__(self,name=None,fileinput=None,variance_window = 9, plotbad = False):
        self.mbms = {}
        self.beadisgood = {}
        self.t = None
        self.tperiod = None
        self._trange= (None,None)
        self.variance_window = variance_window # by default use last 9 localisations for variance/std calculation
        self.median_window = 0 # 0 for median window means "no median filtering"
        self.lowess_fraction = 0.1
        self.plotbad = plotbad
        
        self.name = name
        if fileinput is not None:
            self.populate_df_from_npz(fileinput)

    def populate_df_from_npz(self,fileinput):
        # this is a MBM bead file with raw bead tracks
        self._raw_beads = np.load(fileinput)
        self.beads = df_from_interp_beads(self._raw_beads)
        self.t = self.beads['x'].index
        
        for bead in self.beads['x']:
            self.beadisgood[bead] = True

    def markasbad(self,*beads): # mark a bead as bad
        for bead in beads:
            if bead in self.beads['x']:
                self.beadisgood[bead] = False

    def markasgood_only(self,*beads):
        for bead in self.beadisgood:
            self.beadisgood[bead] = False
        self.markasgood(*beads)

    def markasgood(self,*beads): # if currently bad, mark as good
        for bead in beads:
            if bead in self.beads['x']:
                self.beadisgood[bead] = True

    def plot_tracks(self,axis,unaligned=False,tmin=None,tmax=None,lowess_frac=None):
        if tmin is None:
            tmin=self._trange[0]
        if tmax is None:
            tmax=self._trange[1]

        if tmin is None:
            tmin = self.t.min()
        if tmax is None:
            tmax = self.t.max()

        if axis.startswith('std'):
            unaligned = True # not sensible to align the std devs

        if self.median_window > 0:
            startdf = self.beads[axis].rolling(self.median_window).median()
        else:
            startdf = self.beads[axis]
        if not unaligned:
            startdfg = startdf[[bead for bead in self.beadisgood if self.beadisgood[bead]]]
            dfplotg = startdfg-startdfg.loc[tmin:tmax].mean(axis=0)
            has_bads = not np.all(list(self.beadisgood.values())) # we have at least a single bad bead
            if has_bads:
                dfplotb = startdf[[bead for bead in self.beadisgood if not self.beadisgood[bead]]]
                dfplotb = dfplotb - dfplotb.loc[tmin:tmax].mean(axis=0)
            emptybeads = dfplotg.columns[dfplotg.isnull().all(axis=0)]
            if len(emptybeads)>0:
                warn('removing beads with no valid info after alignment %s...' % emptybeads)
                dfplotg = dfplotg[dfplotg.columns[~dfplotg.isnull().all(axis=0)]]
                
            fig1 = px.line(dfplotg)
            fig1.add_trace(go.Scatter(x=self.t, y=dfplotg.mean(axis=1), name='Mean',
                                     line=dict(color='firebrick', dash='dash')))
            if not lowess_frac is None:
                from statsmodels.nonparametric.smoothers_lowess import lowess
                ltrace = lowess(dfplotg.mean(axis=1), self.t, frac=lowess_frac, return_sorted=False)
                fig1.add_trace(go.Scatter(x=self.t, y=ltrace, name='Lowess',
                                     line=dict(color='yellow', dash='dash')))
            fig2 = px.line(dfplotg.sub(dfplotg.mean(axis=1),axis=0)) # subtract the mean from all the good traces to get the deviation from the mean

            fig = make_subplots(rows=2, cols=1)

            # most of the code below is to tweak the plotly trace coloring and legend making, overplotting etc
            # so things look good and clear eventually
            #
            # we use explicit trace coloring and legend ranking to "survive" the trace reordering below when 'bad' beads are plotted as well
            col_dict = px.colors.qualitative.Plotly
            dict_len = len(col_dict)
            tracenum = 0
            
            for d in fig1.data:
                fig.add_trace((go.Scatter(x=d['x'], y=d['y'], name = d['name'], line=dict(color=col_dict[tracenum % dict_len]),
                                          legendrank=tracenum+1)), row=1, col=1)
                tracenum += 1               
            
            if self.plotbad and has_bads:
                fig.data = fig.data[::-1] # here we initially reverse the plotting sequence of the fig1 traces, but see below
                for column in dfplotb:
                    # print("adding bad trace %s" % column)
                    fig.add_trace((go.Scatter(x=self.t, y=dfplotb[column], name="%s - bad" % column, opacity=0.2,
                                              line=dict(color=col_dict[tracenum % dict_len]),
                                              legendrank=tracenum+1)), row=1, col=1)
                    tracenum += 1
                fig.data = fig.data[::-1] # now we reverse again so that the 'bad traces' are plotted first (and thus at bottom)
                # the original reversal at the top of this block (fig 1 traces) is now reversed so that the mean is plotted last

            colnum = 0 # we start colors again at position 0 for the second subplot                    
            for d in fig2.data:
                fig.add_trace((go.Scatter(x=d['x'], y=d['y'],  name = d['name'], line=dict(color=col_dict[colnum % dict_len]),
                                          legendrank=tracenum+1)), row=2, col=1)
                tracenum += 1
                colnum += 1

            fig.update_layout(autosize=False, height=700,title_text="aligned MBM tracks along %s" % axis,
                              legend_title_text='Bead Selection') # we set a "long" legend title so that the legend does not change width when we change beads etc
            # Update axes properties
            fig.update_xaxes(title_text="time (s)", row=1, col=1)
            fig.update_xaxes(title_text="time (s)", row=2, col=1)
            fig.update_yaxes(title_text="drift (nm)", range=[np.min([-15.0,dfplotg.min().min()]),np.max([15.0,dfplotg.max().max()])], row=1, col=1)
            fig.update_yaxes(title_text="deviation (nm)", range=[-10,10], row=2, col=1)

            return fig
        
        else:
            if axis.startswith('std'):
                yaxis_title = "std dev (nm)"
                title = 'MBM localisation precisions (%s)' % axis
            else:
                title = 'tracks along %s, not aligned' % axis
                yaxis_title = "distance (nm)"
            dfplot = startdf
            dfplotg = dfplot[[bead for bead in self.beadisgood if self.beadisgood[bead]]]
            fig = px.line(dfplotg)
            fig.update_layout(xaxis_title="time (s)", yaxis_title=yaxis_title, title_text=title, height=300,
                              legend_title_text='Bead Selection') # we set a "long" legend title so that the legend does not change width when we change beads etc
            if axis.startswith('std'):
                fig.update_yaxes(range = (0,np.max([10.0,dfplotg.max().max()])))

            return fig
        

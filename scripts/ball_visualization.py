import pandas as pd
from .utils import x_stats_to_track, y_stats_to_track
import plotly.graph_objects as go
import numpy as np


class BallVisualization():
    def __init__(self, match_tracking, pass_events, period) -> None:
        
        self.match_tracking = match_tracking
        self.pass_events = pass_events
        self.pitchLength = match_tracking.pitchLength
        self.pitchWidth = match_tracking.pitchWidth
        self.df_merged = self.merge_sources(period)
        self._df_merged = self.df_merged.copy()

    def merge_sources(self, period):
        df_pass = self.pass_events.df_pass.copy()
        df_tracking = self.match_tracking.BallTracking.df_tracking.copy()
        df_pass = df_pass[df_pass['period']==period]
        df_tracking = df_tracking[df_tracking['period']==period]

        df_pass['x'] = df_pass['x'].apply(x_stats_to_track, pitchLength = self.pitchLength)
        df_pass['y'] = df_pass['y'].apply(y_stats_to_track, pitchWidth = self.pitchWidth)

        df_pass['type'] = 'pass'
        df_tracking['type'] = 'ball'
        df_pass = df_pass[['gameClock','x','y','type']]
        df_tracking = df_tracking[['gameClock','x','y','type']]
        df_viz = pd.concat([df_pass,df_tracking])
        df_viz = df_viz.sort_values('gameClock')
        df_viz['color'] = df_viz['type'].map({'ball' : '#000000', 'pass' : '#FFB600', 'reception' : '#010101'})

        return df_viz
    
    def reset_lag(self):
        self.df_merged = self._df_merged.copy()
    
    def lag_pass(self, lag):
        self.df_merged.loc[self.df_merged['type']=='pass','gameClock'] +=0.1
        self.df_merged = self.df_merged.sort_values('gameClock')

    def plot(self, start, end, plot_step):
        # Create figure
        fig = go.Figure()

        # Add traces, one for each slider step
        for step in np.arange(start,end,plot_step):
            x = self.df_merged.loc[(self.df_merged['gameClock']>=start) & (self.df_merged['gameClock']<=step),'x'].to_list()
            y = self.df_merged.loc[(self.df_merged['gameClock']>=start) & (self.df_merged['gameClock']<=step),'y'].to_list()
            c = self.df_merged.loc[(self.df_merged['gameClock']>=start) & (self.df_merged['gameClock']<=step),'color'].to_list()
            fig.add_trace(
                go.Scatter(
                    visible=False,
                    x=x,
                    y=y,
                    mode = 'markers',
                    marker_color=c))
            
        fig.update_layout(yaxis_range=[-self.pitchWidth/2,self.pitchWidth/2])
        fig.update_layout(xaxis_range=[-self.pitchLength/2,self.pitchLength/2])
        fig.update_layout(
            autosize=False,
            width=self.pitchLength*10,
            height=self.pitchWidth*10,
            plot_bgcolor = '#09CE00'
        )

        # Make 10th trace visible
        fig.data[0].visible = True
        fig.update_layout(xaxis_showgrid=False, yaxis_showgrid=False)
        fig.update_layout(yaxis_zeroline=False)
        fig.update_polars(radialaxis_showline=False)
        fig.add_shape(type="line", x0=-self.pitchLength/2, y0=40.3/2, x1=-self.pitchLength/2+16.5, y1=40.3/2, line_color="white")
        fig.add_shape(type="line", x0=-self.pitchLength/2, y0=-40.3/2, x1=-self.pitchLength/2+16.5, y1=-40.3/2, line_color="white")
        fig.add_shape(type="line", x0=self.pitchLength/2-16.5, y0=40.3/2, x1=self.pitchLength/2, y1=40.3/2, line_color="white")
        fig.add_shape(type="line", x0=self.pitchLength/2-16.5, y0=-40.3/2, x1=self.pitchLength/2, y1=-40.3/2, line_color="white")
        fig.add_shape(type="line", x0=-self.pitchLength/2+16.5, y0=-40.3/2, x1=-self.pitchLength/2+16.5, y1=40.3/2, line_color="white")
        fig.add_shape(type="line", x0=self.pitchLength/2-16.5, y0=-40.3/2, x1=self.pitchLength/2-16.5, y1=40.3/2, line_color="white")

        fig.add_shape(type="line", x0=-self.pitchLength/2, y0=18.3/2, x1=-self.pitchLength/2+5.5, y1=18.3/2, line_color="white")
        fig.add_shape(type="line", x0=-self.pitchLength/2, y0=-18.3/2, x1=-self.pitchLength/2+5.5, y1=-18.3/2, line_color="white")
        fig.add_shape(type="line", x0=self.pitchLength/2-5.5, y0=18.3/2, x1=self.pitchLength/2, y1=18.3/2, line_color="white")
        fig.add_shape(type="line", x0=self.pitchLength/2-5.5, y0=-18.3/2, x1=self.pitchLength/2, y1=-18.3/2, line_color="white")
        fig.add_shape(type="line", x0=-self.pitchLength/2+5.5, y0=-18.3/2, x1=-self.pitchLength/2+5.5, y1=18.3/2, line_color="white")
        fig.add_shape(type="line", x0=self.pitchLength/2-5.5, y0=-18.3/2, x1=self.pitchLength/2-5.5, y1=18.3/2, line_color="white")

        # Create and add slider
        steps = []
        for i in range(len(fig.data)):
            step = dict(
                method="update",
                args=[{"visible": [False] * len(fig.data)},
                    {"title": "Slider switched to step: " + str(i)}],  # layout attribute
            )
            step["args"][0]["visible"][i] = True  # Toggle i'th trace to "visible"
            steps.append(step)

        sliders = [dict(
            active=0,
            currentvalue={"prefix": "Frequency: "},
            pad={"t": 50},
            steps=steps
        )]

        fig.update_layout(
            sliders=sliders
        )

        fig.show()
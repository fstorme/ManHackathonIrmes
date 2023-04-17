import pandas as pd
import scipy.signal as signal
import numpy as np
import json
import sys
import os
from .utils import timestamp_to_seconds

class PassEvents():
    def __init__(self, tracking_file_path = None):
        """Objet représentant les données de tracking de SecondSpectrum pour une équipe donnée."""
        f = open(tracking_file_path)
        data = json.load(f)
        df_pass = pd.json_normalize(data)
        self.df_pass  = self.unstructured_data_to_structured_data(df_pass)
        

    def unstructured_data_to_structured_data(self, df):
        """Retourne un dataframe des données de tracking structureé à partir d'un dataframe de données détsructurées"""
        df = df.loc[df['type.name']=='Pass', ['timestamp','team.name','period','location','duration','pass.end_location','pass.outcome.name']]
        df['x'] = df['location'].apply(lambda x: x[0])
        df['y'] = df['location'].apply(lambda x: x[1])
        df = df.drop(columns = ['location'])
        #TODO : change with home or away, find a way to map it with the team's names
        df.loc[df['team.name']=="Manchester City WFC",'x'] = 120 - df.loc[df['team.name']=="Manchester City WFC",'x']
        df.loc[df['team.name']=="Manchester City WFC",'y'] = 80 - df.loc[df['team.name']=="Manchester City WFC",'y']
        df['x'] = 60 - df['x']
        df['y'] = df['y'] - 40
        df['gameClock'] = df['timestamp'].apply(timestamp_to_seconds)
        return df[['period', 'gameClock', 'team.name', 'duration', 'pass.end_location',	'pass.outcome.name','x','y']]
        
    




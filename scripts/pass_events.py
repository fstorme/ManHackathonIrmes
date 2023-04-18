import pandas as pd
import scipy.signal as signal
import numpy as np
import json
import sys
import os
from .utils import timestamp_to_seconds


class PassEvents():
    def __init__(self, tracking_file_path=None):
        """Objet représentant les données de tracking de SecondSpectrum pour une équipe donnée."""
        f = open(tracking_file_path)
        data = json.load(f)
        df_pass = pd.json_normalize(data)
        self._mapping_jersey = self.set_mapping_jersey(tracking_file_path)
        self.df_pass_home, self.df_pass_away = self.unstructured_data_to_structured_data(df_pass)

    def unstructured_data_to_structured_data(self, df):
        """Retourne un dataframe des données de tracking structureé à partir d'un dataframe de données détsructurées"""
        df = df.loc[
            df['type.name'] == 'Pass', ['timestamp', 'team.name', 'period',
                                        'player.id', 'player.name',
                                        'pass.recipient.id', 'pass.recipient.name',
                                        'pass.end_location', 'pass.height.name',
                                        'location', 'duration',
                                        'pass.body_part.name', 'pass.outcome.name']]
        df['x'] = df['location'].apply(lambda x: x[0])
        df['y'] = df['location'].apply(lambda x: x[1])
        df['end_location_x'] = df['pass.end_location'].apply(lambda x: x[0])
        df['end_location_y'] = df['pass.end_location'].apply(lambda x: x[1])
        df = df.drop(columns=['location', 'pass.end_location'])
        # TODO : change with home or away, find a way to map it with the team's names
        df.loc[df['team.name'] == "Manchester City WFC", 'x'] = 120 - df.loc[
            df['team.name'] == "Manchester City WFC", 'x']
        df.loc[df['team.name'] == "Manchester City WFC", 'y'] = 80 - df.loc[
            df['team.name'] == "Manchester City WFC", 'y']
        df['x'] = 60 - df['x']
        df['y'] = df['y'] - 40
        df.loc[df['team.name'] == "Manchester City WFC", 'end_location_x'] = 120 - df.loc[
            df['team.name'] == "Manchester City WFC", 'end_location_x']
        df.loc[df['team.name'] == "Manchester City WFC", 'end_location_y'] = 80 - df.loc[
            df['team.name'] == "Manchester City WFC", 'end_location_y']
        df['end_location_x'] = 60 - df['end_location_x']
        df['end_location_y'] = df['end_location_y'] - 40
        df['gameClock'] = df['timestamp'].apply(timestamp_to_seconds)
        df['player.jersey_nb'] = df['player.name'].map(self._mapping_jersey)
        df['pass.recipient.jersey_nb'] = df['pass.recipient.name'].map(self._mapping_jersey)
        df = df[['period', 'gameClock', 'team.name',
                 'duration',
                 'x', 'y',
                 'end_location_x', 'end_location_y',
                 'player.id', 'player.name',
                 'pass.recipient.id', 'pass.recipient.name',
                 'player.jersey_nb', 'pass.recipient.jersey_nb',
                 'pass.body_part.name', 'pass.outcome.name']]
        return df[df['team.name'] == "Manchester City WFC"], df[df['team.name'] != "Manchester City WFC"]

    def set_mapping_jersey(self, tracking_file_path):
        f = open(tracking_file_path.replace('events', 'lineups'))
        data = json.load(f)
        mapping_jersey = pd.json_normalize(data, "lineup")
        return dict(zip(mapping_jersey.player_name, mapping_jersey.jersey_number))

    def update_position(self, match_tracking):
        self.df_pass_home = self.add_passer_and_recipient_location(self.df_pass_home,
                                                                   match_tracking.HomeTracking.df_tracking)
        self.df_pass_away = self.add_passer_and_recipient_location(self.df_pass_away,
                                                                   match_tracking.AwayTracking.df_tracking)

    def update_dataset_with_position(self, match_tracking):
        df_coord_home = self.merge_features(match_tracking.HomeTracking.df_tracking)
        df_coord_away = self.merge_features(match_tracking.AwayTracking.df_tracking)
        self.df_pass_home = pd.merge_asof(self.df_pass_home.sort_values(by = ['gameClock', 'period']),
                                          df_coord_home.sort_values(by = ['gameClock', 'period']),
                                          on = "gameClock", by = "period", direction = 'nearest').sort_values(by = [ 'period'])

        self.df_pass_away = pd.merge_asof(self.df_pass_away.sort_values(by = ['gameClock', 'period']),
                                          df_coord_away.sort_values(by = ['gameClock', 'period']),
                                          on = "gameClock", by = "period", direction = 'nearest').sort_values(by = [ 'period'])

    def add_passer_and_recipient_location(self, df_pass, df_track):
        df_pass['player.jersey_nb'] = df_pass['player.jersey_nb'].astype('Int32')
        df_pass['pass.recipient.jersey_nb'] = df_pass['pass.recipient.jersey_nb'].astype('Int32')
        df_track['jersey_number'] = df_track['jersey_number'].astype('Int32')
        df_merge = pd.merge_asof(df_pass.sort_values('gameClock'),
                                 df_track[['gameClock', 'period', 'jersey_number', 'x', 'y']].sort_values('gameClock'),
                                 on='gameClock', left_by=['period', 'player.jersey_nb'],
                                 right_by=['period', 'jersey_number'], suffixes=['', '_passer'])
        df_merge = pd.merge_asof(df_merge.sort_values('gameClock'),
                                 df_track[['gameClock', 'period', 'jersey_number', 'x', 'y']].sort_values('gameClock'),
                                 on='gameClock', left_by=['period', 'pass.recipient.jersey_nb'],
                                 right_by=['period', 'jersey_number'], suffixes=['', '_recipient'])
        df_merge.loc[df_merge['period'] == 2, 'x'] *= -1
        df_merge.loc[df_merge['period'] == 2, 'y'] *= -1
        df_merge['err'] = np.sqrt(
            (df_merge['x'] - df_merge['x_passer']) ** 2 + (df_merge['y'] - df_merge['y_passer']) ** 2)
        #df_merge = df_merge[df_merge['err'] < 15]
        #df_merge = df_merge[['period', 'gameClock', 'team.name', 'duration',
        #                     'pass.outcome.name', 'x', 'y', 'x_passer', 'y_passer', 'x_recipient', 'y_recipient']]
        df_merge = df_merge.sort_values(['period', 'gameClock'])
        return df_merge


    def merge_features(self, df_track):
        df_track['coord'] = df_track[['x', 'y']].values.tolist()
        df_coord = df_track.groupby(['period', 'gameClock']).apply(
            lambda x: dict(zip(x.jersey_number, x.coord))).reset_index()
        df_coord.rename(columns={0: "coord_all"}, inplace=True)
        return df_coord
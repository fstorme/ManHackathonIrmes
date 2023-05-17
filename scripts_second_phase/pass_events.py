import pandas as pd
import scipy.signal as signal
import numpy as np
import json
import sys
import os
from .utils import timestamp_to_seconds
from .utils import flip_coord_team
from .utils import count_adversary_closer_to_goal
from .utils import bypassed_opponents
from .utils import angle
from .utils import opponents_in_path
from .utils import nearest_defender_pass_line
from .utils import flip_dictionnary

class PassEvents():
    def __init__(self, event_file):
        """Objet représentant les données de tracking de SecondSpectrum pour une équipe donnée."""
        data_directory = '../data/statsbomb'
        file = f'{event_file}_events.json'
        events_path = os.path.join(data_directory, file)
        f = open(events_path)
        data = json.load(f)
        df_pass = pd.json_normalize(data)
        self._mapping_jersey = self.set_mapping_jersey(events_path)
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
        df['x'] = df['x'] - 60
        #Y de statsbomb en miroir par rapport aux données tracking, jsp pq, mais on flip ça
        df['y'] = 40 - df['y']
        df['end_location_x'] = df['end_location_x'] - 60
        #idem
        df['end_location_y'] = 40 - df['end_location_x']
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
                 'pass.body_part.name', 'pass.height.name',
                 'pass.outcome.name']]
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
        
    def add_passer_and_recipient_location(self, df_pass, df_track):
        df_pass['player.jersey_nb'] = df_pass['player.jersey_nb'].astype('Int32')
        df_pass['pass.recipient.jersey_nb'] = df_pass['pass.recipient.jersey_nb'].astype('Int32')
        df_track['jersey_number'] = df_track['jersey_number'].astype('Int32')
        df_merge = pd.merge_asof(df_pass.sort_values(by = ['gameClock']),
                                 df_track[['gameClock', 'period', 'jersey_number', 'x', 'y']].sort_values('gameClock'),
                                 on='gameClock', left_by=['period', 'player.jersey_nb'],
                                 right_by=['period', 'jersey_number'], suffixes=['', '_passer'], direction= 'nearest')
        df_merge = pd.merge_asof(df_merge.sort_values(by = ['gameClock']),
                                 df_track[['gameClock', 'period', 'jersey_number', 'x', 'y']].sort_values('gameClock'),
                                 on='gameClock', left_by=['period', 'pass.recipient.jersey_nb'],
                                 right_by=['period', 'jersey_number'], suffixes=['', '_recipient'], direction= 'nearest')
        df_merge['err'] = np.sqrt(
            (df_merge['x'] - df_merge['x_passer']) ** 2 + (df_merge['y'] - df_merge['y_passer']) ** 2)
        df_merge = df_merge[df_merge['err'] < 15]
        df_merge = df_merge.drop(columns=['err'])
        df_merge = df_merge[['period', 'gameClock', 'team.name', 'duration',
                            'pass.outcome.name', 'x', 'y', 'x_passer', 'y_passer', 'x_recipient', 'y_recipient', 'player.jersey_nb', 'pass.recipient.jersey_nb']]
        df_merge = df_merge.sort_values(['period', 'gameClock'])
        return df_merge
    
    def merge_features(self, df_track):
        df_track['coord'] = df_track[['x', 'y','speed']].values.tolist()
        df_coord = df_track.groupby(['period', 'gameClock']).apply(
            lambda x: dict(zip(x.jersey_number, x.coord))).reset_index()
        df_coord.rename(columns={0: "coord_all"}, inplace=True)
        return df_coord
    
    def update_dataset_with_position(self, match_tracking):
        df_coord_home = self.merge_features(match_tracking.HomeTracking.df_tracking)
        df_coord_away = self.merge_features(match_tracking.AwayTracking.df_tracking)
        #home
        self.df_pass_home = pd.merge_asof(self.df_pass_home.sort_values(by = ['gameClock']),
                                          df_coord_home.sort_values(by = ['gameClock', 'period']),
                                          on = "gameClock", by = "period", direction = 'nearest').sort_values(by = [ 'gameClock'])
        self.df_pass_home = pd.merge_asof(self.df_pass_home.sort_values(by = ['gameClock']),
                                          df_coord_away.sort_values(by = ['gameClock', 'period']),
                                          on = "gameClock", by = "period", direction = 'nearest', suffixes = ('_team','_adversary')).sort_values(by = [ 'gameClock'])

        self.df_pass_away = pd.merge_asof(self.df_pass_away.sort_values(by = ['gameClock', 'period']),
                                          df_coord_away.sort_values(by = ['gameClock', 'period']),
                                          on = "gameClock", by = "period", direction = 'nearest').sort_values(by = [ 'gameClock'])
        self.df_pass_away = pd.merge_asof(self.df_pass_away.sort_values(by = ['gameClock', 'period']),
                                          df_coord_home.sort_values(by = ['gameClock', 'period']),
                                          on = "gameClock", by = "period", direction = 'nearest', suffixes = ('_team','_adversary')).sort_values(by = [ 'gameClock'])
        
    def flip_coord_adversary(self):
        self.df_pass_home['coord_all_adversary'] = self.df_pass_home['coord_all_adversary'].apply(flip_dictionnary)
        self.df_pass_away['coord_all_adversary'] = self.df_pass_away['coord_all_adversary'].apply(flip_dictionnary)
        
    
    # Ajout approximatif Nathan 
        
    def clean_dataset(self):
        # Step 1: remove pass events we don't want
        modelling_df_home = self.df_pass_home.loc[
            ~self.df_pass_home['pass.outcome.name'].isin(['Injury Clearance', 'Pass Offside', 'Unknown'])
        ].copy()
        modelling_df_away = self.df_pass_away.loc[
            ~self.df_pass_away['pass.outcome.name'].isin(['Injury Clearance', 'Pass Offside', 'Unknown'])
        ].copy()

        #Step 3: 
        modelling_df_home.loc[:,'completed'] = 0
        modelling_df_away.loc[:,'completed'] = 0

        modelling_df_home.loc[modelling_df_home['pass.outcome.name'].isna(), 'completed'] = 1
        modelling_df_away.loc[modelling_df_away['pass.outcome.name'].isna(), 'completed'] = 1

        #Remove when no recipient info
        modelling_df_home = modelling_df_home.loc[~modelling_df_home['x_recipient'].isna()]
        modelling_df_away = modelling_df_away.loc[~modelling_df_away['x_recipient'].isna()]

        self.df_pass_home = modelling_df_home
        self.df_pass_away = modelling_df_away

    def set_df_for_model(self):
        self._df_concat_raw = pd.concat([self.df_pass_home, self.df_pass_away])
        self.df_model  = self._df_concat_raw[[
            'period', 
            'gameClock',
            'team.name', 
            'x_passer',
            'y_passer',
            'x_recipient',
            'y_recipient',
            'player.jersey_nb',
            'pass.recipient.jersey_nb',
            'coord_all_team', 
            'coord_all_adversary',
            'completed'
        ]].copy()
        self.compute_distance_sideline()
        self.compute_distance_goal()
        self.compute_distance_opponent()
        self.speed_passer()
        self.compute_opponents_closer_to_goal()
        self.compute_distance_receiver_sideline()
        self.compute_distance_receiver_goal()
        self.compute_distance_receiver_opponent()
        self.compute_opponents_closer_to_goal_receiver()
        self.compute_speed_receiver()
        self.compute_bypassed_opponents()
        self.compute_angle()
        self.compute_opponents_in_path()
        self.compute_nearest_defender_pass_line()
        self.compute_distance_pass()

    def compute_distance_sideline(self):
        self.df_model['dist_x'] = 60 - self.df_model['x_passer'].abs()
        self.df_model['dist_y'] = 40 - self.df_model['y_passer'].abs()
        self.df_model['distance_sideline'] = self.df_model[['dist_x','dist_y']].min(axis = 1)
        self.df_model = self.df_model[self.df_model['distance_sideline']>=0] #Pour enlever les touches ?
        self.df_model = self.df_model.drop(columns = ['dist_x','dist_y'])

    def compute_distance_goal(self):
        self.df_model['distance_goal'] = np.sqrt((60 - self.df_model['x_passer'])**2 + self.df_model['y_passer']**2)

    def compute_distance_opponent(self):
        self.df_model['distance_opponent'] = self.df_model.apply(lambda row: np.min([np.sqrt((row['x_passer']-values[0])**2+(row['y_passer']-values[1])**2) for _, values in row['coord_all_adversary'].items()]), axis = 1)

    def speed_passer(self):
        self.df_model['speed_passer'] = self.df_model.apply(lambda row: row['coord_all_team'][row['player.jersey_nb']][2], axis = 1)

    def compute_opponents_closer_to_goal(self):
        self.df_model['opponents_closer_to_goal'] = self.df_model.apply(lambda row : count_adversary_closer_to_goal(row['coord_all_adversary'], row['distance_goal']), axis = 1)

    def compute_distance_receiver_sideline(self):
        self.df_model['dist_x'] = 60 - self.df_model['x_recipient'].abs()
        self.df_model['dist_y'] = 40 - self.df_model['y_recipient'].abs()
        self.df_model['distance_receiver_sideline'] = self.df_model[['dist_x','dist_y']].min(axis = 1)
        self.df_model = self.df_model[self.df_model['distance_sideline']>=0] #Pour enlever les touches ?
        self.df_model = self.df_model.drop(columns = ['dist_x','dist_y'])

    def compute_distance_receiver_goal(self):
        self.df_model['distance_receiver_goal'] = np.sqrt((60 - self.df_model['x_recipient'])**2 + self.df_model['y_recipient']**2)

    def compute_distance_receiver_opponent(self):
        self.df_model['distance_receiver_opponent'] = self.df_model.apply(lambda row: np.min([np.sqrt((row['x_recipient']-values[0])**2+(row['y_recipient']-values[1])**2) for _, values in row['coord_all_adversary'].items()]), axis = 1)
        
    def compute_opponents_closer_to_goal_receiver(self):
        self.df_model['opponents_closer_to_goal_receiver'] = self.df_model.apply(lambda row : count_adversary_closer_to_goal(row['coord_all_adversary'], row['distance_receiver_goal']), axis = 1)

    def compute_speed_receiver(self):
        self.df_model['speed_receiver'] = self.df_model.apply(lambda row: row['coord_all_team'][row['pass.recipient.jersey_nb']][2], axis = 1)

    def compute_bypassed_opponents(self):
        self.df_model['bypassed_opponents'] = self.df_model.apply(lambda row: bypassed_opponents(row['coord_all_adversary'],row['x_passer'],row['x_recipient']), axis = 1)

    def compute_angle(self):
        self.df_model['angle'] = self.df_model.apply(lambda row: angle(row['x_passer'],row['y_passer'],row['x_recipient'],row['y_recipient']), axis = 1)

    def compute_opponents_in_path(self):
        self.df_model['opponents_in_path'] = self.df_model.apply(lambda row: opponents_in_path(row['x_passer'],row['y_passer'],row['x_recipient'],row['y_recipient'],row['coord_all_adversary']), axis = 1)

    def compute_nearest_defender_pass_line(self):
        self.df_model['nearest_defender_pass_line'] = self.df_model.apply(lambda row: nearest_defender_pass_line(row['x_passer'],row['y_passer'],row['x_recipient'],row['y_recipient'],row['coord_all_adversary']), axis=1)

    def compute_distance_pass(self):
        self.df_model['distance_pass'] = self.df_model.apply(lambda row: np.sqrt((row['x_recipient']-row['x_passer'])**2 + (row['y_recipient']-row['y_passer'])**2), axis = 1)

    def delete_columns(self):
        self.df_model = self.df_model.drop(columns = ['team.name','player.jersey_nb', 'pass.recipient.jersey_nb', 'coord_all_team', 'coord_all_adversary'])
        self.df_model = self.df_model[[c for c in self.df_model if c not in ['completed']] + ['completed']]
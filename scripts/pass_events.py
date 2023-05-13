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


class PassEvents():
    def __init__(self, tracking_file_path=None):
        """Objet représentant les données de tracking de SecondSpectrum pour une équipe donnée."""
        if tracking_file_path:
            f = open(tracking_file_path)
            data = json.load(f)
            df_pass = pd.json_normalize(data)
            self._mapping_jersey = self.set_mapping_jersey(tracking_file_path)
            self.df_pass_home, self.df_pass_away = self.unstructured_data_to_structured_data(df_pass)
        else :
            pass

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
        df.loc[df['team.name'] != "Manchester City WFC", 'x'] = 120 - df.loc[
            df['team.name'] != "Manchester City WFC", 'x']
        df.loc[df['team.name'] != "Manchester City WFC", 'y'] = 80 - df.loc[
            df['team.name'] != "Manchester City WFC", 'y']
        df['x'] = 60 - df['x']
        df['y'] = df['y'] - 40
        df.loc[df['team.name'] != "Manchester City WFC", 'end_location_x'] = 120 - df.loc[
            df['team.name'] != "Manchester City WFC", 'end_location_x']
        df.loc[df['team.name'] != "Manchester City WFC", 'end_location_y'] = 80 - df.loc[
            df['team.name'] != "Manchester City WFC", 'end_location_y']
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

    def update_dataset_with_position(self, match_tracking):
        df_coord_home = self.merge_features(match_tracking.HomeTracking.df_tracking)
        df_coord_away = self.merge_features(match_tracking.AwayTracking.df_tracking)
        #home
        self.df_pass_home = pd.merge_asof(self.df_pass_home.sort_values(by = ['gameClock', 'period']),
                                          df_coord_home.sort_values(by = ['gameClock', 'period']),
                                          on = "gameClock", by = "period", direction = 'nearest').sort_values(by = [ 'period'])
        self.df_pass_home = pd.merge_asof(self.df_pass_home.sort_values(by = ['gameClock', 'period']),
                                          df_coord_away.sort_values(by = ['gameClock', 'period']),
                                          on = "gameClock", by = "period", direction = 'nearest', suffixes = ('_team','_adversary')).sort_values(by = [ 'period'])

        self.df_pass_away = pd.merge_asof(self.df_pass_away.sort_values(by = ['gameClock', 'period']),
                                          df_coord_away.sort_values(by = ['gameClock', 'period']),
                                          on = "gameClock", by = "period", direction = 'nearest').sort_values(by = [ 'period'])
        self.df_pass_away = pd.merge_asof(self.df_pass_away.sort_values(by = ['gameClock', 'period']),
                                          df_coord_home.sort_values(by = ['gameClock', 'period']),
                                          on = "gameClock", by = "period", direction = 'nearest', suffixes = ('_team','_adversary')).sort_values(by = [ 'period'])

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
        df_merge = df_merge[df_merge['err'] < 15]
        df_merge = df_merge.drop(columns=['err'])
        #df_merge = df_merge[['period', 'gameClock', 'team.name', 'duration',
        #                     'pass.outcome.name', 'x', 'y', 'x_passer', 'y_passer', 'x_recipient', 'y_recipient']]
        df_merge = df_merge.sort_values(['period', 'gameClock'])
        return df_merge


    def merge_features(self, df_track):
        df_track['coord'] = df_track[['x', 'y','speed']].values.tolist()
        df_coord = df_track.groupby(['period', 'gameClock']).apply(
            lambda x: dict(zip(x.jersey_number, x.coord))).reset_index()
        df_coord.rename(columns={0: "coord_all"}, inplace=True)
        return df_coord

    def prepare_dataset_for_statsbomb_model(self):
        coord_home = pd.DataFrame([*self.df_pass_home['coord_all_team']], self.df_pass_home.index).stack() \
            .rename_axis([None, 'jersey_number_recipient']).reset_index(1, name='coord')
        coord_away = pd.DataFrame([*self.df_pass_away['coord_all_team']], self.df_pass_away.index).stack() \
            .rename_axis([None, 'jersey_number_recipient']).reset_index(1, name='coord')

        split_df_home = self.df_pass_home[['gameClock', 'period']].join(coord_home).reset_index(drop=True)
        split_df_away = self.df_pass_away[['gameClock', 'period']].join(coord_away).reset_index(drop=True)

        df_coord_all_home = pd.DataFrame(split_df_home.coord.tolist(), columns=['x_recipient', 'y_recipient'],
                                           index=split_df_home.index)
        df_coord_all_away = pd.DataFrame(split_df_away.coord.tolist(), columns=['x_recipient', 'y_recipient'],
                                         index=split_df_away.index)


        df_final_v0_home = pd.concat([split_df_home[['gameClock', 'period', 'jersey_number_recipient']], df_coord_all_home],
                             axis=1)
        df_final_v0_away = pd.concat([split_df_away[['gameClock', 'period', 'jersey_number_recipient']], df_coord_all_away],
                                     axis=1)
        self.df_pass_home = self.df_pass_home[
            self.df_pass_home.columns.difference(['jersey_number_recipient', 'x_recipient', 'y_recipient', 'coord_all'],
                                     sort=False)].merge(df_final_v0_home, on=['gameClock', 'period'])

        self.df_pass_away = self.df_pass_away[
            self.df_pass_away.columns.difference(['jersey_number_recipient', 'x_recipient', 'y_recipient', 'coord_all'],
                                                 sort=False)].merge(df_final_v0_away, on=['gameClock', 'period'])

        # Step 1: remove pass events we don't want
        modelling_df_home = self.df_pass_home.loc[
            ~self.df_pass_home['pass.outcome.name'].isin(['Injury Clearance', 'Pass Offside', 'Unknown'])
        ]
        modelling_df_away = self.df_pass_away.loc[
            ~self.df_pass_away['pass.outcome.name'].isin(['Injury Clearance', 'Pass Offside', 'Unknown'])
        ]

        # Step 2: create one hot variables
        # pass height and body part
        one_hot_pass_height_variables_home = pd.get_dummies(modelling_df_home['pass.height.name'])
        one_hot_pass_height_variables_away = pd.get_dummies(modelling_df_away['pass.height.name'])

        one_hot_body_part_variables_home = pd.get_dummies(modelling_df_home['pass.body_part.name'])
        one_hot_body_part_variables_away = pd.get_dummies(modelling_df_away['pass.body_part.name'])

        # tidies up naming before appending row wise
        one_hot_pass_height_variables_home.columns = [
            col.lower().replace(' ', '_') for col in one_hot_pass_height_variables_home.columns
        ]

        one_hot_pass_height_variables_away.columns = [
            col.lower().replace(' ', '_') for col in one_hot_pass_height_variables_away.columns
        ]

        one_hot_body_part_variables_home.columns = [
            col.lower().replace(' ', '_') for col in one_hot_body_part_variables_home.columns
        ]

        one_hot_body_part_variables_away.columns = [
            col.lower().replace(' ', '_') for col in one_hot_body_part_variables_away.columns
        ]
        modelling_df_home = pd.concat([modelling_df_home, one_hot_pass_height_variables_home], axis=1)
        modelling_df_away = pd.concat([modelling_df_away, one_hot_pass_height_variables_away], axis=1)


        modelling_df_home = pd.concat([modelling_df_home, one_hot_body_part_variables_home], axis=1)
        modelling_df_away = pd.concat([modelling_df_away, one_hot_body_part_variables_away], axis=1)


        # Step 3: create binary pass complete column
        modelling_df_home['completed'] = 0
        modelling_df_away['completed'] = 0

        modelling_df_home.loc[modelling_df_home['pass.outcome.name'].isna(), 'completed'] = 1
        modelling_df_away.loc[modelling_df_away['pass.outcome.name'].isna(), 'completed'] = 1

        self.df_pass_home = modelling_df_home
        self.df_pass_away = modelling_df_away

    def clean_dataset(self):
        # Step 1: remove pass events we don't want
        modelling_df_home = self.df_pass_home.loc[
            ~self.df_pass_home['pass.outcome.name'].isin(['Injury Clearance', 'Pass Offside', 'Unknown'])
        ]
        modelling_df_away = self.df_pass_away.loc[
            ~self.df_pass_away['pass.outcome.name'].isin(['Injury Clearance', 'Pass Offside', 'Unknown'])
        ]

        #Step 3: 
        modelling_df_home.loc[:,'completed'] = 0
        modelling_df_away.loc[:,'completed'] = 0

        modelling_df_home.loc[modelling_df_home['pass.outcome.name'].isna(), 'completed'] = 1
        modelling_df_away.loc[modelling_df_away['pass.outcome.name'].isna(), 'completed'] = 1

        #Remove when no recipient info
        modelling_df_home = modelling_df_home.loc[~modelling_df_home['pass.recipient.id'].isna()]
        modelling_df_away = modelling_df_away.loc[~modelling_df_away['pass.recipient.id'].isna()]

        self.df_pass_home = modelling_df_home
        self.df_pass_away = modelling_df_away

    def get_pitch_dimensions(self, match_tracking):
        self.pitchLength = match_tracking.pitchLength
        self.pitchWidth = match_tracking.pitchWidth

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
        self.flip_coordinates()
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
        # self.delete_columns()


    def flip_coordinates(self):
        self.df_model.loc[(self.df_model['team.name']=='Manchester City WFC') & (self.df_model['period']==2),'x_passer'] *= (-1)
        self.df_model.loc[(self.df_model['team.name']=='Manchester City WFC') & (self.df_model['period']==2),'y_passer'] *= (-1)
        self.df_model.loc[(self.df_model['team.name']=='Manchester City WFC') & (self.df_model['period']==2),'coord_all_team'] = \
            self.df_model.loc[(self.df_model['team.name']=='Manchester City WFC') & (self.df_model['period']==2),'coord_all_team'].apply(flip_coord_team)
        self.df_model.loc[(self.df_model['team.name']=='Manchester City WFC') & (self.df_model['period']==2),'coord_all_adversary'] = \
            self.df_model.loc[(self.df_model['team.name']=='Manchester City WFC') & (self.df_model['period']==2),'coord_all_adversary'].apply(flip_coord_team)

        self.df_model.loc[(self.df_model['team.name']!='Manchester City WFC') & (self.df_model['period']==1),'x_passer'] *= (-1)
        self.df_model.loc[(self.df_model['team.name']!='Manchester City WFC') & (self.df_model['period']==1),'y_passer'] *= (-1)
        self.df_model.loc[(self.df_model['team.name']!='Manchester City WFC') & (self.df_model['period']==1),'coord_all_team'] = \
            self.df_model.loc[(self.df_model['team.name']!='Manchester City WFC') & (self.df_model['period']==1),'coord_all_team'].apply(flip_coord_team)
        self.df_model.loc[(self.df_model['team.name']!='Manchester City WFC') & (self.df_model['period']==1),'coord_all_adversary'] = \
            self.df_model.loc[(self.df_model['team.name']!='Manchester City WFC') & (self.df_model['period']==1),'coord_all_adversary'].apply(flip_coord_team)
        # self.df_model = self.df_model.drop(columns = 'period')


    def compute_distance_sideline(self):
        self.df_model['dist_x'] = self.pitchLength/2 - self.df_model['x_passer'].abs()
        self.df_model['dist_y'] = self.pitchWidth/2 - self.df_model['y_passer'].abs()
        self.df_model['distance_sideline'] = self.df_model[['dist_x','dist_y']].min(axis = 1)
        self.df_model = self.df_model[self.df_model['distance_sideline']>=0] #Pour enlever les touches ?
        self.df_model = self.df_model.drop(columns = ['dist_x','dist_y'])

    def compute_distance_goal(self):
        self.df_model['distance_goal'] = np.sqrt((self.pitchLength/2 - self.df_model['x_passer'])**2 + self.df_model['y_passer']**2)

    def compute_distance_opponent(self):
        self.df_model['distance_opponent'] = self.df_model.apply(lambda row: np.min([np.sqrt((row['x_passer']-values[0])**2+(row['y_passer']-values[1])**2) for _, values in row['coord_all_adversary'].items()]), axis = 1)

    def speed_passer(self):
        self.df_model['speed_passer'] = self.df_model.apply(lambda row: row['coord_all_team'][row['player.jersey_nb']][2], axis = 1)

    def compute_opponents_closer_to_goal(self):
        self.df_model['opponents_closer_to_goal'] = self.df_model.apply(lambda row : count_adversary_closer_to_goal(row['coord_all_adversary'], row['distance_goal'], self.pitchLength), axis = 1)

    def compute_distance_receiver_sideline(self):
        self.df_model['dist_x'] = self.pitchLength/2 - self.df_model['x_recipient'].abs()
        self.df_model['dist_y'] = self.pitchWidth/2 - self.df_model['y_recipient'].abs()
        self.df_model['distance_receiver_sideline'] = self.df_model[['dist_x','dist_y']].min(axis = 1)
        self.df_model = self.df_model[self.df_model['distance_sideline']>=0] #Pour enlever les touches ?
        self.df_model = self.df_model.drop(columns = ['dist_x','dist_y'])

    def compute_distance_receiver_goal(self):
        self.df_model['distance_receiver_goal'] = np.sqrt((self.pitchLength/2 - self.df_model['x_recipient'])**2 + self.df_model['y_recipient']**2)

    def compute_distance_receiver_opponent(self):
        self.df_model['distance_receiver_opponent'] = self.df_model.apply(lambda row: np.min([np.sqrt((row['x_recipient']-values[0])**2+(row['y_recipient']-values[1])**2) for _, values in row['coord_all_adversary'].items()]), axis = 1)
        
    def compute_opponents_closer_to_goal_receiver(self):
        self.df_model['opponents_closer_to_goal_receiver'] = self.df_model.apply(lambda row : count_adversary_closer_to_goal(row['coord_all_adversary'], row['distance_receiver_goal'], self.pitchLength), axis = 1)

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
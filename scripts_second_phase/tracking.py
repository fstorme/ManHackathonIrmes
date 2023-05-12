import pandas as pd
import scipy.signal as signal
import numpy as np
import json
import os


class TeamTracking():
    def __init__(self, df_unstructured_tracking, isHomeTeam):
        """Objet représentant les données de tracking de SecondSpectrum pour une équipe donnée."""
        self.isHomeTeam = isHomeTeam
        self.df_tracking = self.unstructured_data_to_structured_data(df_unstructured_tracking)

    def unstructured_data_to_structured_data(self, df):
        """Retourne un dataframe des données de tracking structureé à partir d'un dataframe de données détsructurées"""
        # On ne s'intéresse qu'à l'équipe domicile (resp. extérieure)
        team = 'home' if self.isHomeTeam else 'away'
        not_team = 'away' if self.isHomeTeam else 'home'
        df_tracking_home = df.drop([f'{not_team}Players', 'ball'], axis=1)

        # Transforme la colonne des tableau des joueurs en une ligne par joueur
        df_tracking_home = df_tracking_home.explode(f'{team}Players')
        # print(df_tracking_home[team + 'Players'].iloc[0])
        # Récupère les informations nécessaires dans les dictionnaires
        df_tracking_home.loc[:, 'optaId'] = df_tracking_home[
            f'{team}Players'
        ].apply(lambda x: x['optaId'])
        df_tracking_home['optaId'] = df_tracking_home['optaId'].fillna('1')
        df_tracking_home['optaId'] = df_tracking_home['optaId'].astype(int)
        df_tracking_home.loc[:, 'jersey_number'] = (
            df_tracking_home[f'{team}Players']
            .apply(lambda x: x['number'])
            .astype(int)
        )
        df_tracking_home.loc[:, 'speed'] = df_tracking_home[
            f'{team}Players'
        ].apply(lambda x: x['speed'])
        df_tracking_home.loc[:, 'x'] = df_tracking_home[f'{team}Players'].apply(
            lambda x: x['xyz'][0]
        )
        df_tracking_home.loc[:, 'y'] = df_tracking_home[f'{team}Players'].apply(
            lambda x: x['xyz'][1]
        )
        # df_tracking_home.loc[:, 'z'] = df_tracking_home[team + 'Players'].apply(lambda x: x['xyz'][2]) # z semble tout le temps nulle

        # Drop les colonnes inutiles
        df_tracking_home = df_tracking_home.drop([f'{team}Players'], axis=1)
        return df_tracking_home
    
    def flip(self, home_starts_right):
        if self.isHomeTeam == home_starts_right:
            self.df_tracking.loc[self.df_tracking['period']==2,'x'] *= -1
            self.df_tracking.loc[self.df_tracking['period']==2,'y'] *= -1
        else :
            self.df_tracking.loc[self.df_tracking['period']==1,'x'] *= -1
            self.df_tracking.loc[self.df_tracking['period']==1,'y'] *= -1

    def rescale(self, pitchLength, pitchWidth):
        self.df_tracking.loc[:,'x'] *= 120/pitchLength
        self.df_tracking.loc[:,'y'] *= 80/pitchWidth
    
class BallTracking():
    def __init__(self, df_unstructured_tracking):
        self.df_tracking = self.unstructured_data_to_structured_data(df_unstructured_tracking)

    def unstructured_data_to_structured_data(self, df_unstructured_tracking):
        multi_ind = pd.MultiIndex.from_tuples([(row['period'], row['gameClock'])
                                               for i, row in
                                               df_unstructured_tracking[['period', 'gameClock']].iterrows()],
                                              names=["period", "gameClock"])
        df_ball = pd.DataFrame(df_unstructured_tracking['ball'].to_list(),
                               index=multi_ind).reset_index()
        df_ball.loc[:, 'xyz'] = df_ball.apply(np.array)
        df_ball.loc[:, 'x'] = df_ball['xyz'].apply(lambda x: x[0])
        df_ball.loc[:, 'y'] = df_ball['xyz'].apply(lambda x: x[1])
        df_ball.loc[:, 'z'] = df_ball['xyz'].apply(lambda x: x[2])

        return df_ball
    

class MatchTracking():
    def __init__(self, tracking_file, event_file):
        """"Objet représentant les données de tracking de SecondSpectrum pour un match donné."""
        tracking_directory = r'..\data\tracking'
        tracking_file = f'{tracking_file}_SecondSpectrum_tracking-produced.jsonl'
        self.match_tracking_path = os.path.join(tracking_directory, tracking_file)
    

        df_unstructured_tracking = pd.read_json(self.match_tracking_path, lines=True)

        self.HomeTracking = TeamTracking(df_unstructured_tracking=df_unstructured_tracking,
                                         isHomeTeam=True)
        self.AwayTracking = TeamTracking(df_unstructured_tracking=df_unstructured_tracking,
                                         isHomeTeam=False)
        self.BallTracking = BallTracking(df_unstructured_tracking=df_unstructured_tracking)
        #On récupere les dimensions du terrain
        self.set_pitch_dimensions()
        #On détermine quelle équipe attaquait à droite en premier
        self.set_first_team_attacking_to_the_right(event_file = event_file)
        #On flip les coordonnées des équipes en fonction de cela
        #Le but est d'uniformiser pour que dans le dataset de passe l'équipe soit toujours en train d'attaquer vers la droite
        self.HomeTracking.flip(home_starts_right = self.HomeStartstoRight)
        self.AwayTracking.flip(home_starts_right = self.HomeStartstoRight)
        self.HomeTracking.rescale(pitchLength = self.pitchLength, pitchWidth = self.pitchWidth)
        self.AwayTracking.rescale(pitchLength = self.pitchLength, pitchWidth = self.pitchWidth)

    def set_pitch_dimensions(self):
        f = open(self.match_tracking_path.replace('tracking-produced.jsonl', 'meta.json'))
        data = json.load(f)
        self.pitchWidth = data['pitchWidth']
        self.pitchLength = data['pitchLength']

    def set_first_team_attacking_to_the_right(self, event_file):
        # Je n'ai pas trouvé de moyen de savoir dans quel sens la homeTeam commençait à attaquer

        # Idée : utiliser la position moyenne de la gardienne pour savoir dans quel sens l'équipe attaque
        # Pour cela on a besoin du numéro de maillot de la gardienne
        data_directory = r'..\data\statsbomb'
        file = f'{event_file}_lineups.json'
        lineups_path = os.path.join(data_directory, file)
        f = open(lineups_path)
        data = json.load(f)
        lineups = pd.json_normalize(data)
        lineups = lineups.explode('lineup')
        lineups['role'] = lineups['lineup'].apply(lambda x : x['positions'][0]['position'] if len(x['positions'])==1 else '')
        lineups['jersey_number'] = lineups['lineup'].apply(lambda x : x['jersey_number'])
        goal_keepers = lineups[lineups['role']=='Goalkeeper']
        assert len(goal_keepers) == 2
        home_goalkeeper_jersey_number = goal_keepers.loc[goal_keepers['team_name']=='Manchester City WFC','jersey_number'].iloc[0]
        away_goalkeeper_jersey_number = goal_keepers.loc[goal_keepers['team_name']!='Manchester City WFC','jersey_number'].iloc[0]
        #On a récupéré les numéros de maillots des deux gardiennes

        #On regarde leur position moyenne en première et en deuxième mi temps et on compare les deux
        home_goalkeeper_diff_position = self.HomeTracking.df_tracking[
            self.HomeTracking.df_tracking['jersey_number'] == home_goalkeeper_jersey_number].groupby('period').mean().diff()['x'][2]
        away_goalkeeper_diff_position = self.AwayTracking.df_tracking[
            self.AwayTracking.df_tracking['jersey_number'] == away_goalkeeper_jersey_number].groupby('period').mean().diff()['x'][2]

        # Si la gardienne de l'équipe home est plus à droite en deuxième mi temps c'est que la home team a commencé à attaquer à droite
        if home_goalkeeper_diff_position>0 and away_goalkeeper_diff_position<0:
            self.HomeStartstoRight = True
        elif home_goalkeeper_diff_position<0 and away_goalkeeper_diff_position>0:
            self.HomeStartstoRight = False
        else:
            raise Exception("Pas capable de determiner le sens de l'attaque")
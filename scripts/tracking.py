import pandas as pd
import scipy.signal as signal
import numpy as np
import json
import sys
import os

class TeamTracking():
    def __init__(self, tracking_file_path = None, 
                 df_unstructured_tracking = pd.DataFrame(), 
                 isHomeTeam = True, 
                 frequency=0.04):
        """Objet représentant les données de tracking de SecondSpectrum pour une équipe donnée."""
        self.isHomeTeam = isHomeTeam
        self.frequence = frequency

        if tracking_file_path : 
            df_unstructured_tracking = pd.read_json(tracking_file_path, lines = True)
        elif not tracking_file_path and df_unstructured_tracking.empty :
            raise ValueError("L'utilisateur doit fournir au minimum un lien vers un fichier de données .jsonl ou un dataframe de données déstructurées de SecondSpectrum.")
        self.df_tracking = self.unstructured_data_to_structured_data(df_unstructured_tracking)
        

    def unstructured_data_to_structured_data(self, df):
        """Retourne un dataframe des données de tracking structureé à partir d'un dataframe de données détsructurées"""
        # On ne s'intéresse qu'à l'équipe domicile (resp. extérieure)
        team = 'home' if self.isHomeTeam else 'away'
        not_team = 'home' if not self.isHomeTeam else 'away'
        df_tracking_home = df.drop([not_team + 'Players', 'ball'], axis = 1)
       
        # Transforme la colonne des tableau des joueurs en une ligne par joueur
        df_tracking_home = df_tracking_home.explode(team + 'Players')
        # print(df_tracking_home[team + 'Players'].iloc[0])
        # Récupère les informations nécessaires dans les dictionnaires
        df_tracking_home.loc[:, 'optaId'] = df_tracking_home[team + 'Players'].apply(lambda x: x['optaId']).astype(int)
        df_tracking_home.loc[:, 'jersey_number'] = df_tracking_home[team + 'Players'].apply(lambda x: x['number']).astype(int)
        df_tracking_home.loc[:, 'speed'] = df_tracking_home[team + 'Players'].apply(lambda x: x['speed'])
        df_tracking_home.loc[:, 'x'] = df_tracking_home[team + 'Players'].apply(lambda x: x['xyz'][0])
        df_tracking_home.loc[:, 'y'] = df_tracking_home[team + 'Players'].apply(lambda x: x['xyz'][1])
        #df_tracking_home.loc[:, 'z'] = df_tracking_home[team + 'Players'].apply(lambda x: x['xyz'][2]) # z semble tout le temps nulle

        # Drop les colonnes inutiles
        df_tracking_home = df_tracking_home.drop([team + 'Players'], axis = 1)
        return df_tracking_home
    
    def calculate_acceleration(self,smoothing=False, window=7, polyorder=1, maxacceleration = 12):
        """
        Calcule pour chaque individu la valeur de vitesse et d'accélération à chaque instant du match.
        Inspiré de : https://github.com/Friends-of-Tracking-Data-FoTD/LaurieOnTracking/blob/master/Metrica_Velocities.py
        """
        # Vérification que l'échantillonage est constant
        if (self.df_tracking.groupby(['optaId', 'period']).gameClock.diff() >= self.frequence  + .0001).any() :
            raise ValueError(f"L'échantillonage n'est pas toujours égale à {int(1/f)} Hz.")
        
        # Recalcule de la vitesse
        if False :
            # Vecteur vitesse
            self.df_tracking.loc[:, 'vx'] = self.df_tracking.groupby(['optaId', 'period']).x.diff() / self.frequence
            self.df_tracking.loc[:, 'vy'] = self.df_tracking.groupby(['optaId', 'period']).x.diff() / self.frequence

            # Vitesse scalaire
            self.df_tracking.loc[:, 'vx'] = self.df_tracking.groupby(['optaId', 'period']).vx.apply(lambda x : signal.savgol_filter(x, window_length=window,polyorder=polyorder))
            self.df_tracking.loc[:, 'vy'] = self.df_tracking.groupby(['optaId', 'period']).vy.apply(lambda x : signal.savgol_filter(x, window_length=window,polyorder=polyorder))
            
            # Scalaire de la vitesse 
            self.df_tracking.loc[:, 'speed'] = np.sqrt(self.df_tracking.vx ** 2 + self.df_tracking.vy ** 2)
            self.df_tracking.drop(['vx', 'vy'], axis = 1)
        
        self.df_tracking.loc[:, 'acceleration'] = self.df_tracking.groupby(['optaId', 'period']).speed.diff() / self.frequence
        self.df_tracking.loc[self.df_tracking.acceleration > maxacceleration, 'acceleration'] = np.nan 
        # Smoothing
        if smoothing :
            self.df_tracking.loc[:, 'acceleration'] = self.df_tracking.groupby(['optaId', 'period']).acceleration.transform(lambda x : signal.savgol_filter(x, window_length=window,polyorder=polyorder))
        return self.df_tracking
    
    def calculate_metabolic_cost(self, smoothing=False, window=7, polyorder=1):
        """
        Calcule pour chaque individu le coût métabolic de la vitesse et accélération à chaque instant du match.
        Inspiré de : https://soccermatics.readthedocs.io/en/latest/gallery/lesson8/plot_AccDecRatio.html
        """
        if not 'acceleration' in self.df_tracking.columns :
            raise ValueError("Un calcul d'accélération doit être réalisé en amont de l'appel de cette méthode")
        
        self.df_tracking.loc[:, 'metabolic_cost'] = 0.102 * np.sqrt(self.df_tracking.acceleration ** 2 + 96.2)

        # Calcul pour les accélérations positives
        mask_positive_acc = self.df_tracking.acceleration >= 0
        self.df_tracking.loc[mask_positive_acc, 'metabolic_cost'] = self.df_tracking.loc[mask_positive_acc, 'metabolic_cost'] * (4.03 * self.df_tracking.loc[mask_positive_acc, 'acceleration'] + 3.6 * np.exp(-0.408 * self.df_tracking.loc[mask_positive_acc, 'acceleration']))
        
        # Calcul pour les accélérations négatives
        mask_negative_acc = self.df_tracking.acceleration < 0
        self.df_tracking.loc[mask_negative_acc, 'metabolic_cost'] = self.df_tracking.loc[mask_negative_acc, 'metabolic_cost'] * (-0.85 * self.df_tracking.loc[mask_negative_acc, 'acceleration'] + 3.6 * np.exp(1.33 * self.df_tracking.loc[mask_negative_acc, 'acceleration']))
        
        # Smoothing
        if smoothing :
            self.df_tracking.loc[:, 'metabolic_cost'] = self.df_tracking.groupby(['optaId', 'period']).metabolic_cost.transform(lambda x : signal.savgol_filter(x, window_length=window,polyorder=polyorder))
        
        # Calcul de la puissance métabolique
        self.df_tracking.loc[:, 'metabolic_power'] = self.df_tracking.metabolic_cost * self.df_tracking.speed
        return self.df_tracking
    
class BallTracking():
    def __init__(self, tracking_file_path=None, df_unstructured_tracking=pd.DataFrame(), frequency=0.04):
        self.frequence = frequency
        if tracking_file_path : 
            df_unstructured_tracking = pd.read_json(tracking_file_path, lines = True)
        elif not tracking_file_path and df_unstructured_tracking.empty :
            raise ValueError("L'utilisateur doit fournir au minimum un lien vers un fichier de données .jsonl ou un dataframe de données déstructurées de SecondSpectrum.")
        self.df_tracking = self.unstructured_data_to_structured_data(df_unstructured_tracking)
        
    def unstructured_data_to_structured_data(self, df_unstructured_tracking):
        multi_ind = pd.MultiIndex.from_tuples([(row['period'], row['gameClock'])
                                       for i, row in df_unstructured_tracking[['period', 'gameClock']].iterrows()],
                                      names=["period", "gameClock"])
        df_ball = pd.DataFrame(df_unstructured_tracking['ball'].to_list(),
                       index=multi_ind).reset_index()
        df_ball.loc[:, 'xyz'] = df_ball.apply(np.array)
        df_ball.loc[:, 'x'] = df_ball['xyz'].apply(lambda x: x[0])
        df_ball.loc[:, 'y'] = df_ball['xyz'].apply(lambda x: x[1])
        df_ball.loc[:, 'z'] = df_ball['xyz'].apply(lambda x: x[2])
            
        return df_ball
        

    
class MatchTracking():
    def __init__(self, match_id=None, tracking_file_path=None, df_unstructured_tracking=pd.DataFrame(), frequency=0.04):
        """"Objet représentant les données de tracking de SecondSpectrum pour un match donné."""
        
        self.frequency = frequency
        if tracking_file_path : 
            df_unstructured_tracking = pd.read_json(tracking_file_path, lines = True)
        elif not tracking_file_path and df_unstructured_tracking.empty :
            raise ValueError("L'utilisateur doit fournir au minimum un lien vers un fichier de données .jsonl ou un dataframe de données déstructurées de SecondSpectrum.")
            
        
        self.HomeTracking = TeamTracking(df_unstructured_tracking=df_unstructured_tracking, 
                                         frequency=0.04, 
                                         isHomeTeam=True)
        self.AwayTracking = TeamTracking(df_unstructured_tracking=df_unstructured_tracking, 
                                         frequency=0.04, 
                                         isHomeTeam=False)
        self.BallTracking = BallTracking(df_unstructured_tracking=df_unstructured_tracking, 
                                         frequency=0.04)
        
        f = open(tracking_file_path.replace('tracking-produced.jsonl','meta.json'))
        data = json.load(f)

        self.pitchWidth = data['pitchWidth']
        self.pitchLength = data['pitchLength']





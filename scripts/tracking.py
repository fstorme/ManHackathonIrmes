import pandas as pd
import sys
import os

class TeamTracking():
    def __init__(self, tracking_file_path = None, df_unstructured_tracking = pd.DataFrame(), isHomeTeam = True):
        """Objet représentant les données de tracking de SecondSpectrum pour une équipe donnée."""
        self.isHomeTeam = isHomeTeam

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

        # Récupère les informations nécessaires dans les dictionnaires
        df_tracking_home.loc[:, 'optaId'] = df_tracking_home[team + 'Players'].apply(lambda x: x['optaId'])
        df_tracking_home.loc[:, 'speed'] = df_tracking_home[team + 'Players'].apply(lambda x: x['speed'])
        df_tracking_home.loc[:, 'xyz'] = df_tracking_home[team + 'Players'].apply(lambda x: x['xyz'])

        # Drop les colonnes inutiles
        df_tracking_home = df_tracking_home.drop([team + 'Players'], axis = 1)
        return df_tracking_home
    
    def calculate_velocities(self):
        #TODO
        return None
    
    def calculate_accelerations(self):
        #TODO
        return None

    
class MatchTracking():
    def __init__(self, match_id = None):
        """"Objet représentant les données de tracking de SecondSpectrum pour un match donné."""
        #TODO




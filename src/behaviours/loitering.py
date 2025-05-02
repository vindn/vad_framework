from joblib import load
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import sequence
import numpy as np
import movingpandas as mpd
import time
import pandas as pd
import geopandas as gpd
from keras.models import Sequential
from keras.layers import LSTM, Dense, Dropout
from tensorflow.keras import backend as K

max_trajectory_length = 21
# Carregar o modelo do arquivo
# model_fishing_trajectory = load('fishing_trajectorie_gb.joblib')


def create_rnn_model( dropout=0.2, units=50,  recurrent_dropout=0.2 ):
        K.clear_session()
        model = Sequential()
        model.add(LSTM(units, input_shape=(max_trajectory_length, 3), dropout=dropout, recurrent_dropout=recurrent_dropout))
        # model.add(LSTM(units, return_sequences=True, input_shape=(emRNN.max_trajectory_length, 3), dropout=dropout, recurrent_dropout=recurrent_dropout))
        # model.add(LSTM(units, dropout=dropout, recurrent_dropout=recurrent_dropout))
        model.add(Dense(2, activation='softmax'))
        model.compile(optimizer='rmsprop',
                    loss='categorical_crossentropy', metrics=['acc'])
        return model    


class LoiteringTrajectoryDetection:        

    def __init__( self ):
        self.random_state_trajs_encounter_info = 0
        self.random_state_trajs_encounter = 0.1
        self.max_trajectory_length=21

        self.x = None
        self.y = None
        # self.model = load('src/behaviours/loitering_rnn.joblib')
        # self.model = load('src/behaviours/loitering_rnn_500_epochs.joblib')
        # self.model = load('src/behaviours/loitering_rnn_300_epochs.joblib')

        # ['speed_nm', 'ang_diff_cog_calculated', 'aceleration']
        self.model = load('src/behaviours/loitering_rnn_best_model.joblib')

    def angular_diff_for_rnn(self, direction1, direction2):
        """
        Calcula a menor diferença angular entre duas séries de direções.

        Parâmetros:
        direcao1 (pandas.Series ou array-like): Primeira série de direções (em graus).
        direcao2 (pandas.Series ou array-like): Segunda série de direções (em graus).

        Retorna:
        array-like: A menor diferença angular entre as direções.
        """
        # Converter de graus para radianos
        direction1_rad = np.radians(direction1)
        direction2_rad = np.radians(direction2)

        # Calcular a diferença angular em radianos
        difference = np.arctan2(np.sin(direction1_rad - direction2_rad), 
                                np.cos(direction1_rad - direction2_rad))

        # Converter de radianos para graus
        degrees_diff = np.degrees(difference)

        # Ajustar para que o resultado esteja entre -180 e 180 graus
        degrees_diff = (degrees_diff + 180) % 360 - 180

        return degrees_diff
    
    def distance_points_meters( self, p1, p2 ):
        point1_series = gpd.GeoSeries(p1, crs="EPSG:4326")
        point1_meters = point1_series.to_crs(epsg=32619)

        point2_series = gpd.GeoSeries(p2, crs="EPSG:4326")
        point2_meters = point2_series.to_crs(epsg=32619)

        return point1_meters.distance(point2_meters)    

    def transform_trajs_to_rnn_format( self, trajs ):
        x_trajs = []
        for i in range( len(trajs) ):
            rnn_df = trajs.trajectories[i].df
            # rnn_df.rename(columns={'veloc': 'SOG'}, inplace=True)
            # rnn_df['ang_diff'] = rnn_df['ang_diff'] = self.angular_diff_for_rnn( rnn_df['veloc'], rnn_df['veloc'].shift(1))
            # time_difference_seconds = (pd.Series( rnn_df.index ).diff().fillna(pd.Timedelta(seconds=0)).dt.total_seconds().astype(int))
            # rnn_df['time_diff'] = time_difference_seconds.values
            # rnn_df['dist_diff'] = self.distance_points_meters(rnn_df.geometry, rnn_df.geometry.shift(1))
            
            # x_trajs.append( trajs.trajectories[i].df[['veloc', 'rumo']].to_numpy() )
            # x_trajs.append( trajs.trajectories[i].df[['veloc', 'ang_diff', 'time_diff', 'dist_diff']].to_numpy() )
           
            # x_trajs.append( trajs.trajectories[i].df[['speed_nm', 'ang_diff', 'time_diff', 'dist_diff', 'acceleration']].to_numpy() )
            x_trajs.append( trajs.trajectories[i].df[['speed_nm', 'ang_diff_cog_calculated', 'acceleration']].tail(self.max_trajectory_length).to_numpy() )
        return x_trajs

    def predict_rnn( self, trajs ):
        x_trajs = self.transform_trajs_to_rnn_format( trajs )
        X_pred = sequence.pad_sequences(x_trajs, maxlen=self.max_trajectory_length)

        return self.model.predict( X_pred )
    

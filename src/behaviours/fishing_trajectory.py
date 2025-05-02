from joblib import load
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import sequence
import numpy as np
import movingpandas as mpd
import pandas as pd

# Carregar o modelo do arquivo
# model_fishing_trajectory = load('fishing_trajectorie_gb.joblib')

class FishingTrajectoryDetection:        

    def __init__( self, model_type ):
        self.x = None
        self.y = None
        if model_type == "GB" :
            # self.model = load('src/behaviours/fishing_trajectorie_gb.joblib')
            self.model = load('src/behaviours/fishing_trajectories_gb_semisupervisied.joblib')
        else:
            # self.model = load('src/behaviours/fishing_trajectorie_rnn.joblib')            
            self.model = load('src/behaviours/fishing_trajectories_rnn.joblib')


    def predict_gb( self, x_trajs_info ):
        from sklearn.preprocessing import MinMaxScaler
        parameters = ['sog_mean', 'sog_var', 'ang_diff_var', 'area_diff']

        x = x_trajs_info.copy()
        # gb_proba = gb_model.predict_proba(x_test_trajs_info)
        # gb_probs = np.round(gb_proba[:, 1])
        # gb_probs = np.array( [  'fishing' if i == 0 else 'sailing' for i in gb_probs  ] )
        # accuracy_gb = accuracy_score(y_test_trajs_info, gb_probs)
        # scaler = MinMaxScaler()
        x.loc[x['sog_mean'] > 50, 'sog_mean'] = 50
        x.loc[x['sog_var'] > 50, 'sog_var'] = 50
        x.loc[x['ang_diff_var'] > 20000, 'ang_diff_var'] = 20000
        x.loc[x['area_diff'] > 1, 'area_diff'] = 1

        x['sog_mean'] = x['sog_mean'] / 50
        x['sog_var'] = x['sog_var'] / 50
        x['ang_diff_var'] = x['ang_diff_var'] / 20000        
        
        return self.model.predict_proba( x[ parameters] )
        # return self.model.predict_proba( x_trajs_info[ parameters ] )
    
    def transform_trajs_to_rnn_format( self, trajs ):
        x_trajs = []
        for i in range( len(trajs) ):
            rnn_df = trajs.trajectories[i].df
            x_trajs.append( trajs.trajectories[i].df[['speed_nm', 'ang_diff', 'time_diff', 'dist_diff', 'acceleration']].to_numpy() )
        return x_trajs

    def predict_rnn( self, trajs ):
        x_trajs = self.transform_trajs_to_rnn_format( trajs )
        X_pred = sequence.pad_sequences(x_trajs, maxlen=100)

        return self.model.predict( X_pred )
    
    def get_fishing_trajs_rnn( self, trajs ):
        y_pred = self.get_fishing_trajs_rnn( trajs )
        y_predround = np.round(y_pred[:, 1])
        # todos os indices zeros sao fishing
        indices_zero = np.where(y_predround == 0)[0]
        trajs_fishing = []
        for i in indices_zero:
            trajs_fishing.append( self.trajs.trajectories[i] )

        return mpd.TrajectoryCollection( trajs_fishing )



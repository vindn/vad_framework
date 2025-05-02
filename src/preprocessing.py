# Encapsula funcionalidades de limpeza, normalização e preparação dos dados. (Nivel 0)

from src.fusion_base import DataFusionBase
import multiprocessing
import geopandas as gpd
from geopandas import GeoDataFrame, read_file
import movingpandas as mpd
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import pickle
from src.tools.custom_moving_pandas import CustomTrajectoryCollection
from src.rules.distancia_costa import CalcDistanciaCosta
import warnings
from tqdm import tqdm
from geopy.distance import geodesic

# Suprimir todos os avisos (não recomendado em produção)
warnings.filterwarnings('ignore')

class Preprocessing(DataFusionBase):
    # recebe um gdf, processa e retorna um moving pandas trajectory colletion
    def __init__(self, data):
        self.gdf = data
        self.trajs = None
        self.trajs_info = None
        self.min_points = 3

    def run(self):
        print("Dataset with " + str(len(self.gdf)) + " lines.")
        # Processamento dos dados
        print("Cleaning data...")
        self.gdf = self.clean_data( self.gdf )
        print("Applying h3 cells...")
        # antigo era 9
        self.gdf = self.apply_h3_cells_in_gdf( self.gdf, 10 )
        print("Applying distance to coast...")
        self.gdf = self.apply_distance_to_coast_km( self.gdf )
        print("Creating trajectories...")
        self.min_points = 10
        self.trajs = self.create_moving_pandas_trajectories( self.gdf )
        print("Filtering trajectories...")
        self.trajs = self.filter_trajs( )
        print("Creating trajectories info...")
        # self.trajs_info = self.create_trajectory_info( self.trajs )
        self.trajs_info = self.trajs_to_df_agg_data( self.trajs )
        print("Number of trajectories created: " + str(len(self.trajs)))
        return self.trajs, self.trajs_info
    
    def get_trajs( self ):
        return self.trajs

    def get_trajs_info( self ):
        return self.trajs_info
    
    def filter_trajs_info( self ):
        return self.trajs_info[self.trajs_info["n_points"] > self.min_points ]

    def filter_trajs( self ):
        # somente trajetorias com mais de 3 pontos
        # Se a trajetoria estiver fora da ZEE, nao considerar
        # AFAZER: Pq nao fazer o filtro no gdf_sistram??????
        dist = CalcDistanciaCosta( )
        trajs_filter = []
        for i in range(len(self.trajs)):
            if len(self.trajs.trajectories[i].df) > self.min_points:
                # if traj inside EEZ append, else dispose
                # if dist.calc_traj_inside_eez( self.trajs.trajectories[i] ):
                trajs_filter.append( self.trajs.trajectories[i] )
        trajs_filter = mpd.TrajectoryCollection(trajs_filter)
        print(" filtered trajs: " + str(len(trajs_filter)))
        return trajs_filter

    # Métodos e atributos específicos para pré-processamento
    def clean_data(self, gdf):
        # Excluir pontos fora da ZEE
        dist = CalcDistanciaCosta( )
        cleaned_gdf = dist.filter_gdf_inside_eez( gdf )
        print(" gdf size after cleaning: " + str( len(cleaned_gdf) ))

        return cleaned_gdf
        
    def normalize_data(self):
        # Implementação da normalização
        pass
    
    def apply_h3_cells_in_gdf( self, gdf, resolution=9 ):
        import h3
        # Resolução	    Raio (km)
        # 0	    1279.0
        # 1	    483.4
        # 2	    183.0
        # 3	    69.09
        # 4	    26.10
        # 5	    9.87
        # 6	    3.73
        # 7	    1.41
        # 8	    0.53
        # 9 	0.20
        # 10	0.076
        # 11	0.0287
        # 12	0.0109
        # 13	0.00411
        # 14	0.00155
        # 15	0.000587
        # Converta os pontos do gdf para índices H3
        gdf['h3_index'] = gdf.apply(lambda row: h3.geo_to_h3(row['geometry'].y, row['geometry'].x, resolution), axis=1)
        return gdf
    
    def calc_distance_diff_nm( self, df, lat_coluna, lon_coluna):
        """
        Calcula as diferenças de distância entre pares de pontos de latitude e longitude em um DataFrame.
        df: DataFrame contendo as colunas de latitude e longitude
        lat_coluna: Nome da coluna de latitude
        lon_coluna: Nome da coluna de longitude
        Retorna uma lista com as diferenças de distância entre as linhas.
        """
        diferencas = []
        for i in range(len(df) - 1):
            ponto1 = (df[lat_coluna].iloc[i], df[lon_coluna].iloc[i])
            ponto2 = (df[lat_coluna].iloc[i + 1], df[lon_coluna].iloc[i + 1])
            distancia = geodesic(ponto1, ponto2).nautical
            diferencas.append(distancia)

        diferencas.insert(0, diferencas[0])
        return diferencas
    
    def calc_time_diff_h(self, df, coluna_tempo):
        """
        Calcula as diferenças de tempo em horas entre linhas consecutivas de um DataFrame.
        df: DataFrame contendo a coluna de tempo
        coluna_tempo: Nome da coluna de tempo
        Retorna uma lista com as diferenças de tempo em horas entre as linhas.
        """
        diferencas = []
        for i in range(len(df) - 1):
            tempo1 = pd.to_datetime(df[coluna_tempo].iloc[i])
            tempo2 = pd.to_datetime(df[coluna_tempo].iloc[i + 1])
            diferenca = (tempo2 - tempo1).total_seconds() / 3600  # Diferença em horas
            diferencas.append(diferenca)
        
        diferencas.insert(0, diferencas[0])
        return diferencas

    def calculate_compass_bearing(self, pointA, pointB):
        """
        Calcular o azimute entre dois pontos.
        :param pointA: Tuple com latitude e longitude do primeiro ponto (latA, lonA)
        :param pointB: Tuple com latitude e longitude do segundo ponto (latB, lonB)
        :return: Azimute em graus
        """
        if (type(pointA) != tuple) or (type(pointB) != tuple):
            raise TypeError("Only tuples are supported as arguments")

        lat1 = np.radians(pointA[0])
        lat2 = np.radians(pointB[0])

        diffLong = np.radians(pointB[1] - pointA[1])

        x = np.sin(diffLong) * np.cos(lat2)
        y = np.cos(lat1) * np.sin(lat2) - (np.sin(lat1) * np.cos(lat2) * np.cos(diffLong))

        initial_bearing = np.arctan2(x, y)

        # Converte de radianos para graus e ajusta para 0-360°
        initial_bearing = np.degrees(initial_bearing)
        compass_bearing = (initial_bearing + 360) % 360

        return compass_bearing



    def calculate_cog(self, df):
        """
        Calcular o COG para cada ponto de uma trajetória.
        :param df: DataFrame com colunas 'LAT' e 'LON'
        :return: DataFrame com coluna adicional 'COG'
        """
        # Verifica se as colunas 'LAT' e 'LON' existem no DataFrame
        if 'lat' not in df.columns or 'lon' not in df.columns:
            raise KeyError("DataFrame must contain 'LAT' and 'LON' columns")

        # Certifica-se de que os índices do DataFrame são contínuos
        df = df.reset_index(drop=True)

        cogs = [np.nan]  # O primeiro ponto não tem COG

        for i in range(1, len(df)):
            pointA = (df.iloc[i-1]['lat'], df.iloc[i-1]['lat'])
            pointB = (df.iloc[i]['lat'], df.iloc[i]['lon'])        
            cog = self.calculate_compass_bearing(pointA, pointB)
            cogs.append(cog)

        # df['COG'] = cogs
        cogs[0] = cogs[1]
        return cogs


        # Trajectories
    def create_moving_pandas_trajectories(self, gdf, verbose=True, gap_minutes=30, traj_min_size=3):
        import movingpandas as mpd
        import shapely as shp
        import hvplot.pandas
        import time

        try:
            # if dh it's not the index
            gdf['dh'] = pd.to_datetime(gdf['dh'], utc=True)
        except Exception as e:
            # reset index
            gdf = gdf.reset_index()
            gdf['dh'] = pd.to_datetime(gdf['dh'], utc=True)

        # gdf['mmsi'] = gdf['mmsi'].astype(str)
        gdf['traj_id'] = gdf['mmsi']

        start_time = time.time()

        collection = CustomTrajectoryCollection(
            gdf, "traj_id",  t='dh', min_length=0.001, crs='epsg:4326')
               
        print("Spliting trajectories ...")
        collection = mpd.ObservationGapSplitter(
            collection).split(gap=timedelta(minutes=gap_minutes))
        print(" trajectories after spliting: " + str(len(collection)))
        
        print("Creating columns ...")
        trajs_collection = []
        for traj in collection.trajectories:
            if len(traj.df) > traj_min_size:
                traj.df['dist_diff']  = self.calc_distance_diff_nm( traj.df, 'lat', 'lon')
                traj.df['time_diff_h'] = self.calc_time_diff_h( traj.df.reset_index(), 'dh' )
                traj.df['time_diff'] = traj.df['time_diff_h'] * 3600
                traj.df['speed_nm'] = traj.df['dist_diff'] / traj.df['time_diff_h']
                traj.df['speed_nm'].iloc[0] = traj.df['speed_nm'].iloc[1]
                traj.df['ang_diff_cog'] = self.angular_diff( traj.df['rumo'], traj.df['rumo'].shift(1))
                traj.df['cog_calculated'] = self.calculate_cog( traj.df )
                traj.df['ang_diff_cog_calculated'] = self.angular_diff( traj.df['cog_calculated'], traj.df['cog_calculated'].shift(1))
                traj.df['acceleration'] = traj.df['speed_nm'] / traj.df['time_diff_h']
                traj.df['acceleration'].iloc[0] = traj.df['acceleration'].iloc[1]
            # traj.df['speed_nm'] = traj.df['speed_nm'] * 100000
            # traj.df['speed_nm'].iloc[0] = traj.df['speed_nm'].iloc[1]
            # # duration must be greather 30 min
            # if traj.get_duration().seconds > 60*30 and traj.df.speed_nm.mean() > 1 and traj.df.speed_nm.mean() < 50 and len(traj.df) > 5:
            #     traj.df.fillna(0, inplace=True)
            #     traj.df['time_delta'] = pd.to_timedelta(traj.df['time_delta'])
            #     traj.df['time_diff'] = traj.df['time_delta'].dt.total_seconds().astype(int)
            #     traj.df['acceleration'] = traj.df['acceleration'] * 100000
            #     traj.df['acceleration'].iloc[0] = traj.df['acceleration'].iloc[1]
                trajs_collection.append( traj )

        end_time = time.time()
        if verbose:
            print("Time creation trajectories: ", (end_time-start_time)/60,  " min")

        # return collection
        return mpd.TrajectoryCollection( trajs_collection )

    def apply_distance_to_coast_km( self, gdf ):
        # gdf['distance_to_coast'] = gdf['geometry'].apply(self.get_distance_from_coast_km)
        # achar um raster com as distancias dos pixels para a costa
        dc = CalcDistanciaCosta( )
        dist_nm = []
        for i in tqdm( range(len( gdf )) ):
            dist_nm.append( dc.distancia_costa_brasil( gdf.iloc[i].lon, gdf.iloc[i].lat ) )
        
        gdf["distance_to_coast"] = dist_nm

        return gdf
    
    def circular_variance(self, directions):
        """
        Calcula a variância circular para uma série de dados angulares.

        Parâmetros:
        direcoes (pandas.Series): Série contendo os dados angulares (em graus).

        Retorna:
        float: Variância circular dos dados na série.
        """
        # Converter de graus para radianos
        direction_rad = np.radians(directions)

        # Calcular seno e cosseno
        sins = np.sin(direction_rad)
        cossins = np.cos(direction_rad)

        # Calcular médias de seno e cosseno
        mean_sin = np.mean(sins)
        mean_cossin = np.mean(cossins)

        # Calcular a variância circular
        r = np.sqrt(mean_sin**2 + mean_cossin**2)
        circular_variance = 1 - r

        return circular_variance    
    
    def angular_diff(self, direction1, direction2):
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

        # Ajustar o primeiro ponto pra ficar igual ao segundo ponto
        degrees_diff[0] = degrees_diff[1]

        return degrees_diff


    def traj_area_diff( self, traj ):
        a1 = traj.get_mcp( ).area

        # generalize
        traj2 = mpd.DouglasPeuckerGeneralizer(traj).generalize(tolerance=1.0)
        a2 = traj2.get_mcp().area

        return a1-a2

    def trajs_to_df_agg_data( self, trajs ):
        traj_id = []
        mmsi = []
        sog_mean = []
        sog_var = []
        ang_diff_var = []
        total_distance = []
        duration = []
        n_points = []
        area_diff = []

        # agg fishing trajectories
        for traj in trajs.trajectories:
            traj_id.append ( traj.df.iloc[0].traj_id )
            mmsi.append( traj.df.mmsi.iloc[0] )
            sog_mean.append( traj.df['speed_nm'].mean() )
            sog_var.append ( traj.df['speed_nm'].var() )
            squad_sum = (traj.df['ang_diff_cog'] ** 2).sum()
            ang_diff_var.append ( squad_sum )
            p1 = (traj.df['lat'].iloc[0], traj.df['lon'].iloc[0])
            p2 = (traj.df['lat'].iloc[-1], traj.df['lon'].iloc[-1])
            distance = geodesic(p1, p2).nautical
            total_distance.append ( distance )
            duration.append ( traj.get_duration().total_seconds() / 60 )
            n_points.append ( len(traj.df) )
            # area_diff.append( self.traj_area_diff(traj) )
            area_diff.append( traj.get_mcp().area )

        df_agg = pd.DataFrame({
            'traj_id': [],
            'mmsi':[],
            'sog_mean': [],
            'sog_var': [],
            'ang_diff_var': [],
            'total_distance': [],
            'duration': [],
            'n_points': [],
            'area_diff': []
        })            

        df_agg['traj_id'] = traj_id
        df_agg['mmsi'] = mmsi
        df_agg['sog_mean'] = sog_mean
        df_agg['sog_var'] = sog_var
        df_agg['ang_diff_var'] = ang_diff_var
        df_agg['total_distance'] = total_distance
        df_agg['duration'] = duration
        df_agg['n_points'] = n_points
        df_agg['area_diff'] = area_diff

        return df_agg


    def create_trajectory_info(self, collection):
        import movingpandas as mpd
        import shapely as shp
        import hvplot.pandas
        from datetime import datetime, timedelta
        import time

        collection.add_speed(overwrite=True)
        collection.add_direction(overwrite=True)

        # format trajectories to clustering
        lines_traj_id = np.array([])
        mmsi = np.array([])
        area = np.array([])
        varCourse = np.array([])
        varSpeed = np.array([])
        duration = np.array([])
        medshipcourse = np.array([])
        # shipname = np.array([])
        meanShipSpeed = np.array([])
        meanSpeedKnot = np.array([])
        endTrajCoastDist = np.array([])
        # vesseltype = np.array([])
        traj_len = np.array([])
        n_points = np.array([])
        for traj in collection.trajectories:
            traj.df.fillna(0, inplace=True)
            mmsi = np.append( mmsi, traj.df.mmsi.iloc[0] )
            traj_id = traj.df.traj_id.iloc[0]
            lines_traj_id = np.append(lines_traj_id, traj_id)
            area = np.append(area, traj.get_mcp().area)
            varCourse = np.append(varCourse, traj.df.ang_diff.var())
            medshipcourse = np.append(medshipcourse, traj.df.rumo.mean())
            varSpeed = np.append(varSpeed, traj.df.speed.var())
            duration = np.append(duration, traj.get_duration().seconds)
            meanShipSpeed = np.append(meanShipSpeed, traj.df.speed_nm.mean())
            meanSpeedKnot = np.append(meanSpeedKnot, traj.df.speed_nm.mean())
            traj_len = np.append(traj_len, traj.get_length())
            n_points = np.append(n_points, len(traj.df))


        clus_df = pd.DataFrame()
        clus_df["traj_id"] = lines_traj_id
        clus_df["mmsi"] = mmsi
        clus_df["area"] = area
        clus_df["varCourse"] = varCourse
        clus_df["medshipcourse"] = medshipcourse
        clus_df["varSpeed"] = varSpeed
        clus_df["duration"] = duration
        clus_df["meanShipSpeed"] = meanShipSpeed
        clus_df["meanSpeedKnot"] = meanSpeedKnot
        # clus_df["varDirection"] = varDirection
        # clus_df["meanDirection"] = meanDirection
        clus_df["traj_len"] = traj_len
        clus_df["n_points"] = n_points

        return clus_df
    
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
    
    def save_trajs_to_file( self, filepath="data/objects/trajs_sistram.pkl" ):
        # Salvando as variáveis em um arquivo
        with open(filepath, 'wb') as f:
            pickle.dump(self.trajs, f)

    def save_trajs_info_to_file( self, filepath="data/objects/trajs_info_sistram.pkl" ):
        # Salvando as variáveis em um arquivo
        with open(filepath, 'wb') as f:
            pickle.dump(self.trajs_info, f)


    def load_trajs_from_file( self, filepath="data/objects/trajs_sistram.pkl" ):
        # Load variables
        with open(filepath, 'rb') as f:
            self.trajs = pickle.load(f)
        

    def load_trajs_info_from_file( self, filepath="data/objects/trajs_info_sistram.pkl" ):
        # Load variables
        with open(filepath, 'rb') as f:
            self.trajs_info = pickle.load(f)





###
## Preprocessing Stream
###

class PreprocessingStream(Preprocessing):

    def __init__( self, data ):
        super().__init__( data )

    # Create Trajectories from Stream AIS
    def create_moving_pandas_trajectories(self, gdf, verbose=True, gap_minutes=90, traj_min_size=3):
        import movingpandas as mpd
        import shapely as shp
        import hvplot.pandas
        import time

        try:
            # if dh it's not the index
            gdf['dh'] = pd.to_datetime(gdf['dh'], utc=True)
        except Exception as e:
            # reset index
            gdf = gdf.reset_index()
            gdf['dh'] = pd.to_datetime(gdf['dh'], utc=True)

        gdf['traj_id'] = gdf['mmsi']

        start_time = time.time()

        # Specify minimum length for a trajectory (in meters)
        minimum_length = 0
        collection = CustomTrajectoryCollection(
            gdf, "traj_id",  t='dh', min_length=0.001, crs='epsg:4326')
        


        # set time gap between trajectories for split
        # collection = mpd.ObservationGapSplitter(
        #     collection).split(gap=timedelta(minutes=90))
        print("Number of unique trajs: " + str( len(collection)) )
        print("Splitting trajectories ...")
        collection = mpd.ObservationGapSplitter(
            collection).split(gap=timedelta(minutes=gap_minutes))
        # collection = mpd.StopSplitter(collection).split(max_diameter=200, min_duration=timedelta(minutes=30))

        print("Number of splitted trajs: " + str( len(collection)) )
        print("Creating columns ...")
        trajs_collection = []
        for traj in collection.trajectories:
            traj.df['dist_diff']  = self.calc_distance_diff_nm( traj.df, 'lat', 'lon')
            traj.df['time_diff_h'] = self.calc_time_diff_h( traj.df.reset_index(), 'dh' )
            traj.df['time_diff'] = traj.df['time_diff_h'] * 3600
            traj.df['speed_nm'] = traj.df['dist_diff'] / traj.df['time_diff_h']
            traj.df['speed_nm'].iloc[0] = traj.df['speed_nm'].iloc[1]
            traj.df['ang_diff_cog'] = self.angular_diff( traj.df['rumo'], traj.df['rumo'].shift(1))
            traj.df['cog_calculated'] = self.calculate_cog( traj.df )
            traj.df['ang_diff_cog_calculated'] = self.angular_diff( traj.df['cog_calculated'], traj.df['cog_calculated'].shift(1))
            traj.df['acceleration'] = traj.df['speed_nm'] / traj.df['time_diff_h']
            traj.df['acceleration'].iloc[0] = traj.df['acceleration'].iloc[1]
            trajs_collection.append( traj )

        end_time = time.time()
        if verbose:
            print("Time creation trajectories: ", (end_time-start_time)/60,  " min")

        return mpd.TrajectoryCollection( trajs_collection )



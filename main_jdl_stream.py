# %%
from src.preprocessing import Preprocessing
from src.preprocessing import PreprocessingStream
from src.object_level_fusion import ObjectLevelFusion
from src.impact_assessment import ImpactAssessment
from src.decision_support import DecisionSupport
from src.behaviours.fishing_trajectory import FishingTrajectoryDetection
from src.behaviours.loitering import LoiteringTrajectoryDetection
from src.behaviours.encounter import Encounter
from src.database.metamodel_base import MetamodelDB
from src.rules.distancia_costa import CalcDistanciaCosta
from src.metamodel.active_learning import ActiveLearningModel
from src.behaviours.dark_activity import DarkActivity
from src.behaviours.spoofing import AISSpoofing
from src.tools.web_crawler import WebCrawler
from src.rules.apa import APA
from src.rules.anchorage_zones import AnchorageZone
from src.rules.fpso import FPSO
from src.tools.performance import Performance
from src.situacional_awareness import SituationalAwareness
from multiprocessing import Process, Queue
import multiprocessing
import geopandas as gpd
import pickle
import movingpandas as mpd
import numpy as np
import pandas as pd
from tqdm import tqdm
import time
from datetime import datetime

max_trajectory_length = 21
# ao serializar o modelo de loitering_rnn_best_model.joblib este não guarda
# esta funcao utilizada pelo gridsearcv, portano preciso declara-la nesse escopo
def create_rnn_model( dropout=0.2, units=50,  recurrent_dropout=0.2 ):
        from keras.models import Sequential
        from keras.layers import LSTM, Dense, Dropout
        from tensorflow.keras import backend as K

        K.clear_session()
        model = Sequential()
        model.add(LSTM(units, input_shape=(max_trajectory_length, 3), dropout=dropout, recurrent_dropout=recurrent_dropout))
        # model.add(LSTM(units, return_sequences=True, input_shape=(emRNN.max_trajectory_length, 3), dropout=dropout, recurrent_dropout=recurrent_dropout))
        # model.add(LSTM(units, dropout=dropout, recurrent_dropout=recurrent_dropout))
        model.add(Dense(2, activation='softmax'))
        model.compile(optimizer='rmsprop',
                    loss='categorical_crossentropy', metrics=['acc'])
        return model    


def read_pickle_obj(file_name):
    try:
        with open(file_name, 'rb') as data_file:
            data = pickle.load(data_file)
            return data
    except Exception as e:
        print(e, "File not Found!")

##
## Plot trajectory for use in the paper
##
from shapely.geometry import Point, LineString, Polygon

# plot gdf points
def plot_gdf( gdf, vessel_description ):
    import folium

    latitude_initial = gdf.iloc[0]['lat']
    longitude_initial = gdf.iloc[0]['lon']

    m = folium.Map(location=[latitude_initial, longitude_initial], zoom_start=10)

    for _, row in gdf.iterrows():

        # vessel_description = vessel_type_mapping.get( int( row['VesselType'] ), "Unknown")
        # vessel_description = vessel_type_mapping.get( int( row['VesselType'] ), "Unknown")

        # Concatenar colunas para o popup
        popup_content = f"<b>Timestamp:</b> {row.name}<br><b>VesselName:</b> {row['nome_navio']}<br><b>MMSI</b>: {row['mmsi']}<br><b>LAT:</b> {row['lat']}<br><b>LON:</b> {row['lon']}<br><b>SOG:</b> {row['veloc']}<br><b>Type:</b> {vessel_description}<br><b>COG:</b> {row['rumo']}<br>"
        # color = mmsi_to_color( row['MMSI'] )
        
        folium.CircleMarker(
            location=[row['geometry'].y, row['geometry'].x],
            popup=popup_content,
            radius=1,  # Define o tamanho do ponto
            # color=color,  # Define a cor do ponto
            fill=True,
            fill_opacity=1
        ).add_to(m)            

    return m


def create_linestring(group):        
    # Ordenar por timestamp
    group = group.sort_values(by='dh')      
    # Se há mais de um ponto no grupo, crie uma LineString, caso contrário, retorne None
    return LineString(group.geometry.tolist()) if len(group) > 1 else None


# plot trajectories from points
def plot_trajectory( gdf, vessel_description ):
    import folium

    lines = gdf.groupby('mmsi').apply(create_linestring)

    # Remove possíveis None (se algum grupo tiver apenas um ponto)
    lines = lines.dropna()

    # Crie um novo GeoDataFrame com as LineStrings
    lines_gdf = gpd.GeoDataFrame(lines, columns=['geometry'], geometry='geometry')

    lines_gdf.reset_index(inplace=True)

    # start_point = Point(lines_gdf.iloc[0].geometry.coords[0])
    # m = folium.Map(location=[start_point.y, start_point.x], zoom_start=10)

    m = plot_gdf( gdf, vessel_description )

    for _, row in lines_gdf.iterrows():            
        if row['geometry'].geom_type == 'LineString':
            popup_content = f"{row['mmsi']}"
            coords = list(row['geometry'].coords)
                
            folium.PolyLine(locations=[(lat, lon) for lon, lat in coords], 
                        popup=popup_content,
                        weight=0.5
            ).add_to(m)

    return m



########## MAIN ##################

### Evento de chegada AIS

# %%    
# Preprocessa e retorna trajetorias
# # gdf_sistram = read_pickle_obj("data/sistram/gdf_sistram_1dn_ais_ihs.pkl")    
# # gdf_sistram = read_pickle_obj("data/sintetic/gdf_sintetic.pkl") 
# lembrar de fazer db.update_metamodel_trajectories_synthetic() para os sinteticos
# gdf_sistram = read_pickle_obj("data/sintetic/gdf_sintetic2.pkl") 

gdf_sistram_list = [
    # "data/sintetic/gdf_sintetic2.pkl",
    "data/sistram/gdf_600000000_699999999.pickle",
    # "data/sistram/gdf_500000000_599999999.pickle",
    # "data/sistram/gdf_400000000_499999999.pickle",
    # "data/sistram/gdf_300000000_399999999.pickle",
    # "data/sistram/gdf_200000000_299999999.pickle",
    # "data/sistram/gdf_100000000_199999999.pickle"
]
# gdf_sistram = read_pickle_obj("data/sistram/gdf_600000000_699999999.pickle") 
# gdf_sistram = read_pickle_obj("data/sistram/gdf_500000000_599999999.pickle") 
# gdf_sistram = read_pickle_obj("data/sistram/gdf_400000000_499999999.pickle") 
# gdf_sistram = read_pickle_obj("data/sistram/gdf_300000000_399999999.pickle") 
# gdf_sistram = read_pickle_obj("data/sistram/gdf_200000000_299999999.pickle") 
# gdf_sistram = read_pickle_obj("data/sistram/gdf_100000000_199999999.pickle") 

for str_path in gdf_sistram_list:
    gdf_sistram = read_pickle_obj( str_path ) 
    print("##### FILE " + str_path + " PROCESSING ...")
    # gdf_sistram['mmsi'] = gdf_sistram['mmsi'].fillna(0).astype(int)
    gdf_sistram = gdf_sistram.dropna(subset=['mmsi'])
    gdf_sistram['mmsi'] = gdf_sistram['mmsi'].fillna(0).astype(int)
    # gdf_sistram['mmsi'] = gdf_sistram['mmsi'].astype(str)
    # gdf_sistram['mmsi'] = gdf_sistram['mmsi'].astype(str).str.replace('\.0$', '', regex=True) 
    geometry = [Point(xy) for xy in zip(gdf_sistram['lon'], gdf_sistram['lat'])]
    gdf_sistram = gpd.GeoDataFrame(gdf_sistram, geometry=geometry)
    gdf_sistram = gdf_sistram.reset_index().set_index('dh')
    # gdf_sistram.rename(columns={'rumo': 'shipcourse', 'veloc': 'shipspeed'}, inplace=True)  
    gdf_sistram = gdf_sistram[:1000] # for debug
    print("Number of lines: " + str(len(gdf_sistram)) )

    n_lines = len(gdf_sistram)
    batch_lines = 1000000
    # for begin in range( 0, n_lines, batch_lines ):
    for begin in tqdm( range( 0, n_lines, batch_lines ) ):
        dt_hr_now = datetime.now()
        print("Loop initiated in ", dt_hr_now)
        end = begin + batch_lines
        if end > n_lines:
            end = n_lines
        # pre processing sources
        preprocessing = PreprocessingStream( gdf_sistram[begin:end] )
        trajs, trajs_info = preprocessing.run()
        # build all sources, models and rules
        olf = ObjectLevelFusion( preprocessing )
        olf.build_all_sources( )
        olf.predict_all_behaviors( )
        # apply metamodels
        sa = SituationalAwareness( olf )
        sa.fuse_data( )
        print("end = " + str(end))  
        time.sleep( 60 )


# %%

# # execute this if is first load of syntetic dataset
# carregamento do sintético, primeira carga de dados
# db = MetamodelDB()
# db.update_metamodel_trajectories_synthetic()
# Em seguida lembra de rodar o update do ajuste sintetico do SQL

## Pontos AIS sintéticos 65.551
## Trajetórias sintéticas 2.777
## Pontos AIS do sudeste 2.461.597
## Trajetórias do sudeste 43.744
## Tempo criação 4:40 h

# %%
## Evento de avaliação pelo operador humano (colocar na interface grafica)
#

ia = ImpactAssessment( min_cold_start_rows=100, meta_model=None )
ia.update_all_models( )
# row, prediction = ia.query_instances_and_predict( )

# %%
# Explain models
ia = ImpactAssessment( min_cold_start_rows=100, meta_model=None )
# ia.execute_active_learning_shap()
# ia.execute_active_learning_shap_characteristic( "ft", 2 )
ia.execute_active_learning_shap_class_pt( 3 )

# %%

ds = DecisionSupport( )
# ds.insert_specialist_response_row( row, "atividade_normal", al_prediction=None)
# ds.plot_trajectory_classification( )
# ds.plot_illegal_fishing_trajectories( )
# m = ds.plot_suspected_trajectories( )
# m.save('suspicius_trajectories.html')

# m = ds.plot_encounter_trajectories( )
m = ds.plot_illegal_fishing_trajectories( )
m.save('illegal_fishing_trajectories.html')
# ds.plot_anomalous_trajectories( )

# ds.report_trajectories_by_class( )

# AFAZER: Fazer mapas de predicao com o HDBSCAN e com o K-MEANS!!

# %%
# Export trajectories for plot in qgis
ds = DecisionSupport( )
# ds.export_trajectories_predicted_to_csv( 'trajetorias_normais.csv', 'atividade_normal')
# ds.export_trajectories_predicted_to_csv( 'trajetorias_anomalas.csv', 'atividade_anomala')
# ds.export_trajectories_predicted_to_csv( 'trajetorias_suspeitas.csv', 'atividade_suspeita')
ds.export_trajectories_predicted_to_csv( 'trajetorias_pesca.csv', 'pesca_ilegal')


# %%
## Test performance class
perf = Performance()
# perf.calc_acc_by_class( )
# perf.calc_acc( )
perf.confusion_matrix_plot_pt( op="op1" )
# perf.precision_recall_f1( )
# perf.calculate_metrics( op='op1')
# perf.count(op="op1")

# %%
perf.count(op="op1")

##TESTES
# %%
db = MetamodelDB()
meta_model = db.get_meta_model()

#%% 

Performance.learning_rate( )

# %%

traj = db.get_trajectory(63092)
m = plot_trajectory( traj.df, 'Cargo' )
m.save('trajectory_example.html')

# %%

db = MetamodelDB()
db.update_metamodel_trajectories_synthetic()

# %%

db = MetamodelDB()
traj = db.get_trajectory( '235075027_20' )
traj.df

# %%

# TESTE
encounter = Encounter( trajs )
df_encounters = encounter.detect_encouters()

# %%

encounter.get_encounter_by_mmsi( 277397000  )
# %%

olf.df_metamodelo[ olf.df_metamodelo['traj_id'] == '563071800_0' ]

# %%

db = MetamodelDB()
meta_model = db.get_meta_model( )
mt = ( meta_model["dist_costa"] < 12 ).astype(int)

db.update_metamodel_by_field( meta_model['id'].values.astype(int), mt.values.astype(int), 'dentro_mt')

# %%
db = MetamodelDB()
meta_model = db.get_meta_model( )
meta_model[ meta_model['id'] == '680453' ]

# %%

db = MetamodelDB()
# trajs = db.get_trajectories_by_mmsi( 312262000 )
# BEAGLE FI trawler ingles suspeito!! metaid 883753
traj = db.get_trajectory_by_metamodel_id(1047018)

# %%

# traj.df[traj.df['speed_nm'] > 30]
traj.df

# %% 
# Teste plot trajectory GAP para uma trajetoria
# 740358000
# 701130000
gdfs = db.get_gdf_trajectories_by_mmsi( 710998000 )
da = DarkActivity( gdfs ) 
da.build_trajectories( )
da.plot_gaps_on_map( da.trajs.trajectories[0], 4 )

# %%
da.is_gap_on_trajectory( da.trajs.trajectories[0] )
# %%
all_geohashes = da.get_geohashes_from_linestring(da.trajs.trajectories[0].to_linestring(), 3 )
# %%
da.is_geohash_gap_transmission( 'dbu' )

# %%
db = MetamodelDB()
# trajs = db.get_trajectories_by_mmsi( 312262000 )
traj = db.get_trajectory_by_metamodel_id(354141)
fpso = FPSO()
fpso.is_inside(traj.to_traj_gdf())


# %%
# atualiza coluna fpso para 15000
# AFAZER: mudar na criacao dos comportamentos!
db = MetamodelDB()
# trajs = db.get_trajectories_by_mmsi( 312262000 )
df_metamodel = db.get_meta_model( )
fpso = FPSO(15000)
meta_id_list = []
fpso_col_list = []
for rowid in tqdm( df_metamodel['id'] ):
    try:
        traj = db.get_trajectory_by_metamodel_id( rowid )
        is_inside = fpso.is_inside( traj.to_traj_gdf() )
        meta_id_list.append( rowid )
        fpso_col_list.append( is_inside )
    except Exception as e:
        print("metaid: " + str(rowid) )
        print("traj: " + traj.to_traj_gdf() )
        print(e)
        

# %%

i = 0
for f in meta_id_list:
    if f == 166302:
        print( fpso_col_list[i] )
        break
    i += 1


# %%

db.update_metamodel_by_field( meta_id_list, fpso_col_list, 'in_fpso_area')
# %%
# Corrige encontros
db = MetamodelDB()
# trajs = db.get_trajectories_by_mmsi( 312262000 )
df_metamodel = db.get_meta_model( )
parameters = ["ft", "enc", "loi", "dentro_apa", "spoofing", "out_of_anchor_zone", "dark_ship", "flag_brazil", "flag_unknow", "flag_other", "type_fishing", "type_other", "type_unknow", "dentro_zee", "dentro_mt", "in_fpso_area"]
df_metamodel[ parameters ]

# %%
# Corrige no metamodelo trajetorias com enc nan
# df_enc = df_metamodel[ df_metamodel["enc"].isna() ]
trajs = []
for index, row in tqdm( df_metamodel.iterrows() ):
    traj = db.get_trajectory_by_metamodel_id( row['id'] )
    traj.df['traj_fk'] = row['traj_fk']
    trajs.append( traj )

trajs = mpd.TrajectoryCollection( trajs )

# %%

encounter = Encounter( trajs )
df_encounters = encounter.detect_encouters()
y_pred_encounters = encounter.get_encounters_on_trajs()

# %%



# %%

db.update_metamodel_by_field( df_metamodel['id'], y_pred_encounters, 'enc')

# %%




# %%
# 
db.insert_encounters( df_encounters )

# %%


# %%
# recalcula distancia da costa para trajetorias
db = MetamodelDB()
df_metamodel = db.get_meta_model( )
trajs = []
for index, row in tqdm( df_metamodel.iterrows() ):
    traj = db.get_trajectory_by_metamodel_id( row['id'] )
    # traj.df['traj_fk'] = row['traj_fk']
    trajs.append( traj )

trajs = mpd.TrajectoryCollection( trajs )

dist = CalcDistanciaCosta( )
dist_costa = dist.distancia_costa_brasil_array( trajs )

db.update_metamodel_by_field( df_metamodel['id'], dist_costa, 'dist_costa')

# %%
# Recalcula se navio esta dentro de APA
db = MetamodelDB()
df_metamodel = db.get_meta_model( )
trajs = []
for index, row in tqdm( df_metamodel.iterrows() ):
    traj = db.get_trajectory_by_metamodel_id( row['id'] )
    # traj.df['traj_fk'] = row['traj_fk']
    trajs.append( traj )

trajs = mpd.TrajectoryCollection( trajs )

# %%
apas = APA()
dentro_apa = apas.verifica_trajetorias_dentro_apa_binario( trajs )

db.update_metamodel_by_field( df_metamodel['id'], dentro_apa, 'dentro_apa')

# %%
# Corrige coluna AIS spoofing
aiss = AISSpoofing( trajs )
aiss_verify = np.array( aiss.verify_spoofing_position_trajs() )
spoofing_trajs = [ int(b) for b in aiss_verify]

# %%


# %%
db.update_metamodel_by_field( df_metamodel['id'], spoofing_trajs, 'spoofing')


#
# %%

def rules_cog_diff(  trajs ):
    cog_diff_list = []
    for traj in trajs.trajectories:
        cog_diff_sum = traj.df['ang_diff'].mean( )
        cog_diff_list.append( cog_diff_sum )

    return cog_diff_list

def rules_sog_diff(  trajs ):
    sog_diff_list = []
    for traj in trajs.trajectories:
        sog_var = traj.df['speed_nm'].mean( )
        sog_diff_list.append( sog_var )

    return sog_diff_list


# %%
# Cria novas colunas sog_diff e cog_diff
db = MetamodelDB()
# trajs = db.get_trajectories_by_mmsi( 312262000 )
df_metamodel = db.get_meta_model( )
trajs = []
for index, row in tqdm( df_metamodel.iterrows() ):
    traj = db.get_trajectory_by_metamodel_id( row['id'] )
    # traj.df['traj_fk'] = row['traj_fk']
    trajs.append( traj )

trajs = mpd.TrajectoryCollection( trajs )

# %%
col_cog_diff = rules_cog_diff( trajs )
col_sog_diff = rules_sog_diff( trajs )
# %%

db.update_metamodel_by_field( df_metamodel['id'], col_cog_diff, 'cog_diff')
db.update_metamodel_by_field( df_metamodel['id'], col_sog_diff, 'sog_diff')

# %%
preprocessing = PreprocessingStream( gdf_sistram[:10000] )
trajs, trajs_info = preprocessing.run()
# %%

import math

def haversine(lat1, lon1, lat2, lon2):
    """
    Calcula a distância em milhas náuticas entre duas coordenadas de latitude e longitude.
    lat1, lon1: Latitude e longitude do primeiro ponto (em graus decimais)
    lat2, lon2: Latitude e longitude do segundo ponto (em graus decimais)
    Retorna a distância entre os pontos em milhas náuticas.
    """
    # Raio da Terra em milhas náuticas
    raio_terra_mn = 3440.065

    # Convertendo graus decimais para radianos
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Diferenças de latitude e longitude
    d_lat = lat2_rad - lat1_rad
    d_lon = lon2_rad - lon1_rad

    # Fórmula de Haversine
    a = math.sin(d_lat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(d_lon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distancia = raio_terra_mn * c

    return distancia

# %%

wc = WebCrawler()
nome_navio, bandeira, tipo_navio = wc.obter_info_navio(993116065)
nome_navio, bandeira, tipo_navio


# %%
def mmsi_mid_to_county( mmsi ):

    mid_to_country = {
        201: "Albania (Republic of)",
        202: "Andorra (Principality of)",
        203: "Austria",
        204: "Azores",
        205: "Belgium",
        206: "Belarus (Republic of)",
        207: "Bulgaria (Republic of)",
        208: "Vatican City State",
        209: "Cyprus (Republic of)",
        210: "Cyprus (Republic of)",
        211: "Germany (Federal Republic of)",
        212: "Cyprus (Republic of)",
        213: "Georgia",
        214: "Moldova (Republic of)",
        215: "Malta",
        216: "Armenia (Republic of)",
        218: "Germany (Federal Republic of)",
        219: "Denmark",
        220: "Denmark",
        224: "Spain",
        225: "Spain",
        226: "France",
        227: "France",
        228: "France",
        229: "Malta",        
        230: "Finland",
        231: "Faroe Islands",
        232: "United Kingdom of Great Britain and Northern Ireland",
        233: "United Kingdom of Great Britain and Northern Ireland",
        234: "United Kingdom of Great Britain and Northern Ireland",
        235: "United Kingdom of Great Britain and Northern Ireland",
        236: "Gibraltar",
        237: "Greece",
        238: "Croatia (Republic of)",
        239: "Greece",
        240: "Greece",
        241: "Greece",
        242: "Morocco (Kingdom of)",
        243: "Hungary (Republic of)",
        244: "Netherlands (Kingdom of the)",
        245: "Netherlands (Kingdom of the)",
        246: "Netherlands (Kingdom of the)",
        247: "Italy",
        248: "Malta",
        249: "Malta",
        250: "Ireland",
        251: "Iceland",
        252: "Liechtenstein (Principality of)",
        253: "Luxembourg",
        254: "Monaco (Principality of)",
        255: "Madeira",
        256: "Malta",
        257: "Norway",
        258: "Norway",
        259: "Norway",
        261: "Poland (Republic of)",
        262: "Montenegro",
        263: "Portugal",
        264: "Romania",
        265: "Sweden",
        266: "Sweden",
        267: "Slovak Republic",
        268: "San Marino (Republic of)",
        269: "Switzerland (Confederation of)",
        270: "Czech Republic",
        271: "Turkey",
        272: "Ukraine",
        273: "Russian Federation",
        274: "The Former Yugoslav Republic of Macedonia",
        275: "Latvia (Republic of)",
        276: "Estonia (Republic of)",
        277: "Lithuania (Republic of)",
        278: "Slovenia (Republic of)",
        279: "Serbia (Republic of)",
        # Europe continued
        280: "Ukraine",
        281: "Belarus (Republic of)",
        282: "Moldova (Republic of)",
        283: "Armenia (Republic of)",
        284: "Georgia",
        285: "Bulgaria (Republic of)",
        286: "Turkey",
        287: "Cyprus (Republic of)",
        288: "Georgia",
        289: "Moldova (Republic of)",
        290: "Belarus (Republic of)",
        291: "Switzerland (Confederation of)",
        292: "Belgium",
        293: "Denmark",
        294: "Ireland",
        295: "Greece",
        296: "Iceland",
        297: "Portugal",
        298: "Malta",
        299: "Denmark",
        300: "United Kingdom of Great Britain and Northern Ireland",
        # North America
        301: "Anguilla",
        303: "Alaska (State of)",
        304: "Antigua and Barbuda",
        305: "Antigua and Barbuda",
        306: "Netherlands Antilles",
        307: "Aruba",
        308: "Bahamas (Commonwealth of)",
        309: "Bahamas (Commonwealth of)",
        310: "Bermuda",
        311: "Bahamas (Commonwealth of)",
        312: "Belize",
        314: "Barbados",
        316: "Canada",
        319: "Cayman Islands",
        321: "Costa Rica",
        323: "Cuba",
        325: "Dominica (Commonwealth of)",
        327: "Dominican Republic",
        329: "Guadeloupe (French Department of)",
        330: "Grenada",
        331: "Greenland",
        332: "Guatemala (Republic of)",
        334: "Honduras (Republic of)",
        336: "Haiti (Republic of)",
        338: "United States of America",
        339: "Jamaica",
        341: "Saint Kitts and Nevis (Federation of)",
        343: "Saint Lucia",
        345: "Mexico",
        347: "Martinique (French Department of)",
        348: "Montserrat",
        350: "Nicaragua",
        351: "Panama (Republic of)",
        352: "Panama (Republic of)",
        353: "Panama (Republic of)",
        354: "Panama (Republic of)",
        355: "Panama (Republic of)",
        356: "Panama (Republic of)",
        357: "Panama (Republic of)",
        355: "United States of America", # No specific allocation
        356: "United States of America", # No specific allocation
        357: "United States of America", # No specific allocation
        358: "Puerto Rico",
        359: "El Salvador (Republic of)",
        361: "Saint Pierre and Miquelon (Territorial Collectivity of)",
        362: "Trinidad and Tobago",
        364: "Turks and Caicos Islands",
        366: "United States of America",
        367: "United States of America",
        368: "United States of America",
        369: "United States of America",
        370: "Panama (Republic of)",
        371: "Panama (Republic of)",
        372: "Panama (Republic of)",
        373: "Panama (Republic of)",
        374: "Panama (Republic of)",
        375: "Saint Vincent and the Grenadines",
        376: "Saint Vincent and the Grenadines",
        377: "Saint Vincent and the Grenadines",
        378: "British Virgin Islands",
        379: "United States Virgin Islands",
        401: "Afghanistan",
        403: "Saudi Arabia (Kingdom of)",
        405: "Bangladesh (People's Republic of)",
        408: "Bahrain (Kingdom of)",
        410: "Bhutan (Kingdom of)",
        412: "China (People's Republic of)",
        413: "China (People's Republic of)",
        414: "China (People's Republic of)",        
        416: "Taiwan (Province of China)",
        417: "Sri Lanka (Democratic Socialist Republic of)",
        419: "India (Republic of)",
        422: "Iran (Islamic Republic of)",
        423: "Azerbaijani Republic",
        425: "Iraq (Republic of)",
        428: "Israel (State of)",
        431: "Japan",
        432: "Japan",
        434: "Turkmenistan",
        436: "Kazakhstan (Republic of)",
        437: "Uzbekistan (Republic of)",
        438: "Jordan (Hashemite Kingdom of)",
        440: "Korea (Republic of)",
        441: "Korea (Republic of)",
        443: "Palestine (In accordance with Resolution 99 Rev. Antalya, 2006)",
        445: "Democratic People's Republic of Korea",
        447: "Kuwait (State of)",
        450: "Lebanon",
        451: "Kyrgyz Republic",
        453: "Macao (Special Administrative Region of China)",
        455: "Maldives (Republic of)",
        457: "Mongolia",
        459: "Nepal (Federal Democratic Republic of)",
        461: "Oman (Sultanate of)",
        463: "Pakistan (Islamic Republic of)",
        466: "Qatar (State of)",
        468: "Syrian Arab Republic",
        470: "United Arab Emirates",
        473: "Yemen (Republic of)",
        475: "Yemen (Republic of)",
        477: "Hong Kong (Special Administrative Region of China)",
        478: "Bosnia and Herzegovina",
        # Oceania
        501: "Adelie Land",
        503: "Australia",
        506: "Myanmar (Union of)",
        508: "Brunei Darussalam",
        510: "Micronesia (Federated States of)",
        511: "Palau (Republic of)",
        512: "New Zealand",
        514: "Cambodia (Kingdom of)",
        515: "Cambodia (Kingdom of)",
        516: "Christmas Island (Indian Ocean)",
        518: "Cook Islands",
        520: "Fiji (Republic of)",
        523: "Cocos (Keeling) Islands",
        525: "Indonesia (Republic of)",
        529: "Kiribati (Republic of)",
        531: "Lao People's Democratic Republic",
        533: "Malaysia",
        536: "Northern Mariana Islands (Commonwealth of the)",
        538: "Marshall Islands (Republic of)",
        540: "New Caledonia",
        542: "Niue",
        544: "Nauru (Republic of)",
        546: "French Polynesia",
        548: "Philippines (Republic of)",
        553: "Papua New Guinea",
        555: "Pitcairn Island",
        557: "Solomon Islands",
        559: "American Samoa",
        561: "Samoa (Independent State of)",
        563: "Singapore (Republic of)",
        564: "Singapore (Republic of)",
        565: "Singapore (Republic of)",
        566: "Singapore (Republic of)",        
        567: "Thailand",
        570: "Tonga (Kingdom of)",
        572: "Tuvalu",
        574: "Viet Nam (Socialist Republic of)",
        576: "Vanuatu (Republic of)",
        577: "Vanuatu (Republic of)",
        578: "Wallis and Futuna Islands",
        # Africa
        601: "South Africa (Republic of)",
        603: "Angola (Republic of)",
        605: "Algeria (People's Democratic Republic of)",
        607: "Saint Paul and Amsterdam Islands",
        608: "Ascension Island",
        609: "Burundi (Republic of)",
        610: "Benin (Republic of)",
        611: "Botswana (Republic of)",
        612: "Central African Republic",
        613: "Cameroon (Republic of)",
        615: "Congo (Republic of the)",
        616: "Comoros (Union of the)",
        617: "Cape Verde (Republic of)",
        618: "Crozet Archipelago",
        619: "Côte d'Ivoire (Republic of)",
        621: "Djibouti (Republic of)",
        622: "Egypt (Arab Republic of)",
        624: "Ethiopia (Federal Democratic Republic of)",
        625: "Eritrea",
        626: "Gabonese Republic",
        627: "Ghana",
        629: "Gambia (Republic of the)",
        630: "Guinea-Bissau (Republic of)",
        631: "Equatorial Guinea (Republic of)",
        632: "Guinea (Republic of)",
        633: "Burkina Faso",
        634: "Kenya (Republic of)",
        635: "Kerguelen Islands",
        636: "Liberia (Republic of)",
        637: "Liberia (Republic of)",
        642: "Socialist People's Libyan Arab Jamahiriya",
        644: "Lesotho (Kingdom of)",
        645: "Mauritius (Republic of)",
        647: "Madagascar (Republic of)",
        649: "Mali (Republic of)",
        650: "Mozambique (Republic of)",
        654: "Mauritania (Islamic Republic of)",
        655: "Malawi",
        656: "Niger (Republic of)",
        657: "Nigeria (Federal Republic of)",
        659: "Namibia (Republic of)",
        660: "Reunion (French Department of)",
        661: "Rwanda (Republic of)",
        662: "Sudan (Republic of)",
        663: "Senegal (Republic of)",
        664: "Seychelles (Republic of)",
        665: "Saint Helena",
        666: "Somali Democratic Republic",
        667: "Sierra Leone",
        668: "Sao Tome and Principe (Democratic Republic of)",
        669: "Swaziland (Kingdom of)",
        670: "Chad (Republic of)",
        671: "Togolese Republic",
        672: "Tunisia",
        674: "Tanzania (United Republic of)",
        675: "Uganda (Republic of)",
        676: "Democratic Republic of the Congo",
        677: "Tanzania (United Republic of)",
        678: "Zambia (Republic of)",
        679: "Zimbabwe (Republic of)",
        # South America
        701: "Argentine Republic",
        710: "Brazil (Federative Republic of)",
        711: "Brazil (Federative Republic of)",
        712: "Brazil (Federative Republic of)",
        713: "Brazil (Federative Republic of)",
        714: "Brazil (Federative Republic of)",
        715: "Brazil (Federative Republic of)",
        716: "Brazil (Federative Republic of)",
        717: "Brazil (Federative Republic of)",
        718: "Brazil (Federative Republic of)",
        719: "Brazil (Federative Republic of)",
        720: "Bolivia (Plurinational State of)",
        725: "Chile",
        730: "Colombia (Republic of)",
        735: "Ecuador",
        740: "Falkland Islands (Malvinas)",
        745: "Guiana (French Department of)",
        750: "Guyana",
        755: "Paraguay (Republic of)",
        760: "Peru",
        765: "Suriname (Republic of)",
        770: "Uruguay (Eastern Republic of)",
        775: "Venezuela (Bolivarian Republic of)"
    }    

    # Extrai os três primeiros dígitos para verificar o MID
    mid = int(str(mmsi)[:3])

    # Verifica se o MID está no dicionário
    if mid not in mid_to_country:
        return (1, "N/A")

    return (mid, mid_to_country[mid])

def validate_mmsi(mmsi):
    # Valida se um número MMSI é válido
    # 0 invalid
    # 0.5 valid mmsi
    # 1 valid brazil mmsi
    
    mmsi = str(mmsi)

    # Verifica se o MMSI tem nove dígitos
    if not mmsi.isdigit() or len(mmsi) != 9:
        return 0
    
    md_code, country = mmsi_mid_to_county( mmsi )
    
    # valid and it's brazil
    if country.lower().find( "brazil" ) >= 0:
        return 1
    
    # valid, but it's not brazil
    if md_code > 1:
        return 0.5
    else:
        return 0        

def mmsi_valid( trajs ):
    mmsis_valid = []
    for traj in tqdm( trajs.trajectories ):
        mmsi = traj.df['mmsi'].iloc[0]
        mmsis_valid.append( validate_mmsi( mmsi ) )
    return mmsis_valid

# %%
# Corrige mmsi_valid field
db = MetamodelDB()
df_metamodel = db.get_meta_model( )
parameters = ["ft", "enc", "loi", "dentro_apa", "spoofing", "out_of_anchor_zone", "dark_ship", "flag_brazil", "flag_unknow", "flag_other", "type_fishing", "type_other", "type_unknow", "dentro_zee", "dentro_mt", "in_fpso_area"]

trajs = []
for index, row in tqdm( df_metamodel.iterrows() ):
    traj = db.get_trajectory_by_metamodel_id( row['id'] )
    traj.df['traj_fk'] = row['traj_fk']
    trajs.append( traj )

trajs = mpd.TrajectoryCollection( trajs )
mmsis_valid = mmsi_valid( trajs )

# %%
db.update_metamodel_by_field( df_metamodel['id'], mmsis_valid, 'mmsi_valid')


# %%

validate_mmsi( 901123000 )

# %%
# Corrige trajetorias de pesca

# db = MetamodelDB()
# df_metamodel = db.get_meta_model( )
# parameters = ["ft", "enc", "loi", "dentro_apa", "spoofing", "out_of_anchor_zone", "dark_ship", "flag_brazil", "flag_unknow", "flag_other", "type_fishing", "type_other", "type_unknow", "dentro_zee", "dentro_mt", "in_fpso_area"]

# trajs_ft = []
# n_corrigidos = 0
# for index, row in tqdm( df_metamodel.iterrows() ):
#     traj = db.get_trajectory_by_metamodel_id( row['id'] )
#     traj.df['traj_fk'] = row['traj_fk']
#     veloc_mean = traj.df['speed_nm'].mean()
#     if veloc_mean > 6 or veloc_mean < 1 or len(traj.df) <= 10:
#         trajs_ft.append( 0 )
#         n_corrigidos += 1
#     else:
#         trajs_ft.append( row['ft'] )

# print("Corrigidos: " + str(n_corrigidos) )
# # trajs_ft

# # %%

# db.update_metamodel_by_field( df_metamodel['id'], trajs_ft, 'ft')


# %%
# Corrige trajs sem ter que rodar tudo novamente
trajs = []
n_corrigidos = 0
for index, row in tqdm( df_metamodel.iterrows() ):
    traj = db.get_trajectory_by_metamodel_id( row['id'] )
    traj.df['traj_fk'] = row['traj_fk']
    trajs.append( traj )

preprocessing = Preprocessing(gdf_sistram[:1000])

trajs_collection = []
for traj in trajs.trajectories:
    traj.df['dist_diff']  = preprocessing.calc_distance_diff_nm( traj.df, 'lat', 'lon')
    traj.df['time_diff_h'] = preprocessing.calc_time_diff_h( traj.df.reset_index(), 'dh' )
    traj.df['time_diff'] = traj.df['time_diff_h'] * 3600
    traj.df['speed_nm'] = traj.df['dist_diff'] / traj.df['time_diff_h']
    traj.df['speed_nm'].iloc[0] = traj.df['speed_nm'].iloc[1]
    traj.df['ang_diff_cog'] = preprocessing.angular_diff( traj.df['rumo'], traj.df['rumo'].shift(1))
    traj.df['cog_calculated'] = preprocessing.calculate_cog( traj.df )
    traj.df['ang_diff_cog_calculated'] = preprocessing.angular_diff( traj.df['cog_calculated'], traj.df['cog_calculated'].shift(1))
    traj.df['acceleration'] = traj.df['speed_nm'] / traj.df['time_diff_h']
    traj.df['acceleration'].iloc[0] = traj.df['acceleration'].iloc[1]
    trajs_collection.append( traj )

# %%
# Escreve alteracoes no banco
db = MetamodelDB()
db.update_trajs( trajs_collection )

# %%
# Corrige trajetorias pesca sem ter rodar tudo novamente

db = MetamodelDB()
df_metamodel = db.get_meta_model( )
# parameters = ["ft", "enc", "loi", "dentro_apa", "spoofing", "out_of_anchor_zone", "dark_ship", "flag_brazil", "flag_unknow", "flag_other", "type_fishing", "type_other", "type_unknow", "dentro_zee", "dentro_mt", "in_fpso_area"]

trajs = []
n_corrigidos = 0
for index, row in tqdm( df_metamodel.iterrows() ):
    traj = db.get_trajectory_by_metamodel_id( row['id'] )
    traj.df['traj_fk'] = row['traj_fk']
    trajs.append( traj )

trajs = mpd.TrajectoryCollection( trajs )
trajs_info = preprocessing.trajs_to_df_agg_data( trajs )

# %%
ftd = FishingTrajectoryDetection("GB")
ypred_fishing = ftd.predict_gb( trajs_info )

for i in range(len(trajs)):
    traj = trajs.trajectories[i]
    speed_mean = trajs.trajectories[i].df['speed_nm'].mean()
    veloc_mean  = trajs.trajectories[i].df['veloc'].mean()
    # veloc_std = trajs.trajectories[i].df['speed_nm'].std()
    # para evitar casos onde o navio anda rapido e derrepente para
    # pescar e depois aumenta a velocidade, utilizaremos a media movel
    # OBS: quando diferença de tempo entre os pontos são segundos, imprecisões no GPS
    # podem ocorrer acarretando em um cálculo de velocidade errado. Para isso,
    # é importante também utilizar o SOG
    mm_speed = trajs.trajectories[i].df['speed_nm'].rolling(window=3).mean()
    mm_veloc = trajs.trajectories[i].df['veloc'].rolling(window=3).mean()
    if ( 
        (  (speed_mean > 7 and (not (mm_speed < 4).any())) and (veloc_mean > 7 and (not (mm_veloc < 4).any())) ) or 
        (  (speed_mean < 1 and (not (mm_speed > 2).any())) and (veloc_mean < 1 and (not (mm_veloc > 2).any())) ) or
        ( len(trajs.trajectories[i].df) < 5 ) or # se tiver menos de 6 pontos
        ( (trajs.trajectories[i].get_duration().total_seconds() / 3600) < 1 and ( len(trajs.trajectories[i].df) <= 6 ) ) # se a traj tiver menos de 2hs
    ):
        ypred_fishing[i, 0] = 0.0
        ypred_fishing[i, 1] = 1.0

ypred_fishing[:,0]

# %%
# Atualiza somente coluna loitering do metamodelo
db.update_metamodel_by_field( df_metamodel['id'], ypred_fishing[:,0].tolist(), 'ft')


# %%
# Corrige trajetorias loteiring sem ter rodar tudo novamente

db = MetamodelDB()
df_metamodel = db.get_meta_model( )
parameters = ["ft", "enc", "loi", "dentro_apa", "spoofing", "out_of_anchor_zone", "dark_ship", "flag_brazil", "flag_unknow", "flag_other", "type_fishing", "type_other", "type_unknow", "dentro_zee", "dentro_mt", "in_fpso_area"]

trajs = []
n_corrigidos = 0
for index, row in tqdm( df_metamodel.iterrows() ):
    traj = db.get_trajectory_by_metamodel_id( row['id'] )
    traj.df['traj_fk'] = row['traj_fk']
    trajs.append( traj )

trajs = mpd.TrajectoryCollection( trajs )
loitering = LoiteringTrajectoryDetection( )
y_pred_loitering = loitering.predict_rnn( trajs ).astype(float)

for i in range(len(trajs)):
    traj = trajs.trajectories[i]
    # Para ser loitering, o navio precisa parar em algum momento da trajetoria.
    # Para isso, calcularemos a media movel da velocidade com w=3, entao se existir pelo
    # menos uma media movel menor que 1, pode ser seja loitering.
    # Senao tiver nenhuma, nao ter como ser loitering
    mm = traj.df['speed_nm'].rolling(window=3).mean()
    if not (mm < 1).any():
        y_pred_loitering[i, 0] = 0
        y_pred_loitering[i, 1] = 1

y_pred_loitering[:,0]

# %%
# Atualiza somente coluna loitering do metamodelo
db.update_metamodel_by_field( df_metamodel['id'], y_pred_loitering[:,0].tolist(), 'loi')


# %%
## Atualiza coluna types of vessels
db = MetamodelDB()
df_metamodel = db.get_meta_model( )
olf2 = ObjectLevelFusion(preprocessing)
type_fishing, type_other, type_unknow, type_offshore, type_tanker, type_tug, type_anti_pollution, type_cargo, type_research, type_buoy = olf2.rules_get_vessel_type( df_metamodel["traj_id"] )

# %%
# Atualiza somente coluna types of vessels
db.update_metamodel_by_field( df_metamodel['id'], type_fishing, 'type_fishing')
db.update_metamodel_by_field( df_metamodel['id'], type_other, 'type_other')
db.update_metamodel_by_field( df_metamodel['id'], type_unknow, 'type_unknow')
db.update_metamodel_by_field( df_metamodel['id'], type_offshore, 'type_offshore')
db.update_metamodel_by_field( df_metamodel['id'], type_tanker, 'type_tanker')
db.update_metamodel_by_field( df_metamodel['id'], type_tug, 'type_tug')
db.update_metamodel_by_field( df_metamodel['id'], type_anti_pollution, 'type_anti_pollution')
db.update_metamodel_by_field( df_metamodel['id'], type_cargo, 'type_cargo')
db.update_metamodel_by_field( df_metamodel['id'], type_research, 'type_research')
db.update_metamodel_by_field( df_metamodel['id'], type_buoy, 'type_buoy')

# %%
# Atualiza somente coluna arriving do metamodelo

db = MetamodelDB()
df_metamodel = db.get_meta_model( )
trajs = []
n_corrigidos = 0
for index, row in tqdm( df_metamodel.iterrows() ):
    traj = db.get_trajectory_by_metamodel_id( row['id'] )
    traj.df['traj_fk'] = row['traj_fk']
    trajs.append( traj )

trajs = mpd.TrajectoryCollection( trajs )

olf2 = ObjectLevelFusion(preprocessing)
arriving = olf2.rules_calc_arring_trajs( trajs )

# %%
# Atualiza coluna arriving
db.update_metamodel_by_field( df_metamodel['id'], arriving, 'arriving')

# %%
# Atualiza somente coluna time_stopped do metamodelo

db = MetamodelDB()
df_metamodel = db.get_meta_model( )
trajs = []
n_corrigidos = 0
for index, row in tqdm( df_metamodel.iterrows() ):
    traj = db.get_trajectory_by_metamodel_id( row['id'] )
    traj.df['traj_fk'] = row['traj_fk']
    trajs.append( traj )

trajs = mpd.TrajectoryCollection( trajs )

olf2 = ObjectLevelFusion(preprocessing)
time_stopped = olf2.rules_time_stopped_trajs( trajs )

# %%
# Atualiza coluna time_stopped_h
db.update_metamodel_by_field( df_metamodel['id'], time_stopped, 'time_stopped_h')

# %%
# Corrige flag e type nas trajetorias alteradas
# db = MetamodelDB()
# meta_model = db.get_meta_model( )
# filtro_m = meta_model[ (meta_model['traj_id'].str.len() > 13) & ( (meta_model['flag_other'] == 1) | (meta_model['type_fishing'] == 1) ) ]
# filtro_m

# # %%
# for index, row in filtro_m.iterrows():
#     flag_other = row['flag_other']
#     type_other = row['type_fishing']
#     traj = db.get_trajectory_by_metamodel_id( row['id'] )
#     traj.df['traj_fk'] = row['traj_fk']

#     trajs.append( traj )

# trajs = mpd.TrajectoryCollection( trajs )

# %%

# Exportando o DataFrame com opções adicionais
# meta_model.to_csv('metamodel_exported.csv', sep=';', header=True, mode='w', index=False)
perf.df_classificacao[['al', 'dbscan', 'kmeans', 'human']].to_csv('performance_exported.csv', sep=';', header=True, mode='w', index=False)


# %%
# Contagem de avaliacao por classes
db = MetamodelDB()
meta_model = db.get_meta_model( )

# Filtrar as linhas onde a coluna "classificacao" não é nula
df_classificacao_nao_nula = meta_model[meta_model['classificacao'].notna()]

# Contabilizar as classes na coluna "classificacao"
contagem_classes = df_classificacao_nao_nula['classificacao'].value_counts()

contagem_classes

# %%
# Filtrar as linhas onde a coluna "classificacao" é nula
df_classificacao_nula = meta_model[meta_model['classificacao'].isnull()]

# Contabilizar as classes na coluna "predicao"
contagem_predicao_classificacao_nula = df_classificacao_nula['predicao'].value_counts()

contagem_predicao_classificacao_nula


# %%
# Pesca Ilegal - Brasileiro Dentro de APA
meta_model[ 
    ( (meta_model['traj_id'].str.len() >10 ) & (meta_model['traj_id'].str.len() < 13)  ) & 
    (meta_model['dentro_apa'] == 1  ) & 
    (meta_model['ft'] > 0.5  ) & 
    (meta_model['type_fishing'] == 1  ) & 
    (  (meta_model['flag_brazil'] == 1) ) 
    ]

# %%
# Pesca Ilegal - Estrangeiro dentro de ZEE
meta_model[ 
    ( (meta_model['traj_id'].str.len() >10 ) & (meta_model['traj_id'].str.len() < 13)  ) & 
    (meta_model['dentro_zee'] == 1  ) & 
    (meta_model['ft'] > 0.5  ) & 
    (meta_model['type_fishing'] == 1  ) & 
    (  (meta_model['flag_other'] == 1) ) 
    ]

# %%
# Suspeito - Pescando, bandeira desconhecida, tipo pesca
meta_model[ 
    ( (meta_model['traj_id'].str.len() >10 ) & (meta_model['traj_id'].str.len() < 13)  ) & 
    (meta_model['dentro_zee'] == 1  ) & 
    (meta_model['ft'] > 0.5  ) & 
    (meta_model['type_fishing'] == 1  ) & 
    (  (meta_model['flag_unknow'] == 1) ) 
    ]

# %%
# Suspeito - Pescando, bandeira qualquer, tipo desconhecido
meta_model[ 
    ( (meta_model['traj_id'].str.len() >10 ) & (meta_model['traj_id'].str.len() < 13)  ) & 
    (meta_model['dentro_zee'] == 1  ) & 
    (meta_model['ft'] > 0.5  ) & 
    (meta_model['type_unknow'] == 1  )  
    ]


# %%
meta_model[ 
    ( (meta_model['traj_id'].str.len() >10 ) & (meta_model['traj_id'].str.len() < 13)  ) & 
    (meta_model['dentro_zee'] == 1  ) & 
    (meta_model['ft'] > 0.98  ) & 
    (meta_model['type_other'] == 1  ) &
     (meta_model['predicao'] == 'atividade_suspeita'  )
    ]

# %%
# Atividades suspeitas reais
meta_model[ 
     (meta_model['date_end'] < pd.to_datetime('2023-01-01')  ) &
     (meta_model['ft'] > 0.98  ) &      
     (meta_model['predicao'] == 'atividade_suspeita'  )
    ]

# %%
# Atividades de pescal ilegal reais
meta_model[ 
     (meta_model['date_end'] < pd.to_datetime('2023-01-01')  ) &
     (meta_model['predicao'] == 'pesca_ilegal'  )
    ]

# %%
# Atividades anomalas reais
meta_model[ 
     (meta_model['date_end'] < pd.to_datetime('2023-01-01')  ) &
     (meta_model['predicao'] == 'atividade_anomala'  )
    ]

# %%
# Atividades normais reais
meta_model[ 
     (meta_model['date_end'] < pd.to_datetime('2023-01-01')  ) &
     (meta_model['predicao'] == 'atividade_normal'  )
    ]


# %%
# formata tabela para saida
db = MetamodelDB()
meta_model = db.get_meta_model( )
col_date_ini = []
col_date_end = []
for index, row in tqdm( meta_model.iterrows() ):
    traj = db.get_trajectory_by_metamodel_id( row['id'] )

    col_date_ini.append( traj.df.reset_index().dh.min() )
    col_date_end.append( traj.df.reset_index().dh.max() )

meta_model['date_ini'] = col_date_ini
meta_model['date_end'] = col_date_end
# %%

from sklearn.metrics import confusion_matrix
import seaborn as sns
import matplotlib.pyplot as plt

data_split = perf.df_classificacao[['al', 'human']]

# Calculate the confusion matrix
cm = confusion_matrix(data_split['human'], data_split['al'], labels=data_split['human'].unique())

# Create a DataFrame for the confusion matrix for better readability
cm_df = pd.DataFrame(cm, index=data_split['human'].unique(), columns=data_split['human'].unique())

# Plot the confusion matrix
plt.figure(figsize=(10, 7))
sns.heatmap(cm_df, annot=True, fmt='d', cmap='Blues')
plt.xlabel('Predicted Labels (al)')
plt.ylabel('True Labels (human)')
plt.title('Confusion Matrix: AL vs. Human')
plt.show()



# %%
db = MetamodelDB()
trajs = db.get_trajectories_by_al_prediction('atividade_suspeita')

# Export trajectories for plot in qgis
timestamp = []
mmsi = []
lat = []
lon =[]
cog = []
sog = []
traj_id = []
for traj in trajs.trajectories[:]:
    for index, row in traj.df.reset_index().iterrows():
        timestamp.append( str(row['dh']) )
        mmsi.append( row['mmsi'] )
        lat.append( row.lat )
        lon.append( row.lon )
        cog.append( row.direction )
        sog.append( row.speed_nm )
        traj_id.append( row.traj_id )

df_export = pd.DataFrame()
df_export['timestamp'] = timestamp
df_export['mmsi'] = mmsi
df_export['lat'] = lat
df_export['lon'] = lon
df_export['cog'] = cog
df_export['sog'] = sog
df_export['traj_id'] = traj_id

df_export.to_csv('trajetorias_suspeitas.csv', header=True)



# %%

# Função de normalização
def time_stopped_norm(val):
    # 1 week - 7 days * 24 hours
    if val > 168:
        return 1
    else:
        return val / 168

# %%
import shap
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import MinMaxScaler

db = MetamodelDB()
meta_model = db.get_meta_model()
class_index = 2

# Normaliza distancia de acordo com o tamanho da ZEE (200MN)
meta_model['dist_costa_normalizado'] = meta_model['dist_costa'] / 200.0
# Criar um objeto MinMaxScaler
scaler = MinMaxScaler()
meta_model['cog_diff_norm'] = scaler.fit_transform(meta_model[['cog_diff']])
meta_model['sog_diff_norm'] = scaler.fit_transform(meta_model[['sog_diff']])

#normalization
meta_model['time_stopped_h_norm'] = meta_model['time_stopped_h'].apply(time_stopped_norm)

parameters = ["ft", "enc", "loi", "dentro_apa", "spoofing", "out_of_anchor_zone", "dark_ship", "flag_brazil", "flag_unknow", "flag_other", "type_fishing", "type_other", "type_unknow", "type_offshore", "type_tanker", "type_tug", "type_anti_pollution", "type_research", "type_cargo", "type_research", "type_buoy", "dentro_zee", "dentro_mt", "in_fpso_area", "dist_costa_normalizado", "cog_diff_norm", "sog_diff_norm", "mmsi_valid", "arriving", "time_stopped_h_norm"]



X = meta_model[ parameters + ["classificacao"] ]
X = X[ X["classificacao"].notna() ]

y = X['classificacao']
X = X[ parameters ]

# X = self.replace_df_attributes_names_for_eng( X )
# p = self.replace_list_attributes_names_for_eng( self.parameters )
p = parameters

encoder = LabelEncoder()
Y_encoded = encoder.fit_transform(y)
print(encoder.classes_)

# Dividir em treino e teste
X_train, X_test, y_train, y_test = train_test_split(X, Y_encoded, test_size=0.2, random_state=42)

# Treinar um modelo de floresta aleatória
model = RandomForestClassifier(random_state=42)
model.fit(X_train, y_train)

# Criar o explainer SHAP
explainer = shap.TreeExplainer(model)

explanation = explainer(X_test)
shap_values = explanation.values
print(shap_values.shape)
p = X_test.columns.values
shap.summary_plot(shap_values[:,:,class_index], X_test, feature_names=p)



# %%

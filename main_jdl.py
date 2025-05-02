# %%
from src.preprocessing import Preprocessing
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
        popup_content = f"<b>Timestamp:</b> {row.name}<br><b>VesselName:</b> {row['nome_navio']}<br><b>MMSI</b>: {row['mmsi']}<br><b>LAT:</b> {row['lat']}<br><b>LON:</b> {row['lon']}<br><b>SOG:</b> {row['veloc']}<br><b>Type:</b> {vessel_description}<br><b>COG:</b> {row['rumo']}<br><b>Heading:</b> {row['direction']}"
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
# gdf_sistram = read_pickle_obj("data/sistram/gdf_sistram_1dn_ais_ihs.pkl")    
# gdf_sistram = read_pickle_obj("data/sintetic/gdf_sintetic.pkl") 
gdf_sistram = read_pickle_obj("data/sintetic/gdf_sintetic2.pkl") 
# gdf_sistram['mmsi'] = gdf_sistram['mmsi'].fillna(0).astype(int)
gdf_sistram = gdf_sistram.dropna(subset=['mmsi'])
gdf_sistram['mmsi'] = gdf_sistram['mmsi'].fillna(0).astype(int)
# gdf_sistram['mmsi'] = gdf_sistram['mmsi'].astype(str)
# gdf_sistram['mmsi'] = gdf_sistram['mmsi'].astype(str).str.replace('\.0$', '', regex=True) 
geometry = [Point(xy) for xy in zip(gdf_sistram['lon'], gdf_sistram['lat'])]
gdf_sistram = gpd.GeoDataFrame(gdf_sistram, geometry=geometry)
# gdf_sistram.rename(columns={'rumo': 'shipcourse', 'veloc': 'shipspeed'}, inplace=True)  
print("Number of lines: " + str(len(gdf_sistram)) )
preprocessing = Preprocessing(gdf_sistram[10000:])
# %%
trajs, trajs_info = preprocessing.run()

# %%

# salva objetos para o arquivo para nao ter que processa-los novamente
# utilizar para depuracao futuramente
# preprocessing.save_trajs_to_file()
# preprocessing.save_trajs_info_to_file()

# %%
# Carrega trajetorias do arquivo sem ter que processa-las
# preprocessing.load_trajs_from_file()
# preprocessing.load_trajs_info_from_file()
# trajs = preprocessing.get_trajs( )
# trajs_info = preprocessing.get_trajs_info( )


# %%
olf = ObjectLevelFusion( preprocessing )
olf.build_all_sources( )
olf.predict_all_behaviors( )

# %% 

sa = SituationalAwareness( olf )
sa.fuse_data( )

# %%
## Evento de avaliação pelo operador humano (colocar na interface grafica)
#

ia = ImpactAssessment( min_cold_start_rows=50, meta_model=None )
ia.update_all_models( )
# row, prediction = ia.query_instances_and_predict( )

# %%

ds = DecisionSupport( )
# ds.insert_specialist_response_row( row, "atividade_normal", al_prediction=None)
# ds.plot_trajectory_classification( )
# ds.plot_illegal_fishing_trajectories( )
ds.plot_suspected_trajectories( )

# %%
## Test performance class
perf = Performance()
perf.calc_acc( )
# %%

# TESTE
import geopandas as gpd
gdf_zee_brazil = gpd.read_file("data/zee/EEZ_land_union_v3_202003/EEZ_Land_v3_202030.shp")
# %%
gdf_zee_brazil[ gdf_zee_brazil["UNION"] == "Brazil" ].plot()
# %%

calc = CalcDistanciaCosta()

# %%
db = MetamodelDB()
# traj = db.get_trajectory( 57705 )
traj = db.get_trajectory_by_metamodel_id( 6618 )
traj.df


# %%
calc.calc_point_inside_eez(-42.753448, -23.515380 )
# %%

t = calc.calc_trajs_inside_eez( trajs )

# %%

# TESTE
encounter = Encounter( trajs )
df_encounters = encounter.detect_encouters()
# %%
traj_ids = df_encounters[0]["traj_id"].unique()
traj_fks = df_encounters[0]["traj_fk"].unique()
h3 = df_encounters[0]["h3_index"].iloc[0]


# %%
db = MetamodelDB()
db.insert_encounters( df_encounters )
# %%

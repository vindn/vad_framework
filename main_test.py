# %%
from src.preprocessing import Preprocessing
from src.object_level_fusion import ObjectLevelFusion
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
        popup_content = f"<b>Timestamp:</b> {row.name}<br><b>VesselName:</b> {row['nome_navio']}<br><b>MMSI</b>: {row['mmsi']}<br><b>LAT:</b> {row['lat']}<br><b>LON:</b> {row['lon']}<br><b>SOG:</b> {row['veloc']}<br><b>Type:</b> {vessel_description}<br><b>COG:</b> {row['rumo']}"
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

# %%

preprocessing = Preprocessing(gdf_sistram[:])
# %%
# trajs, trajs_info = preprocessing.run()

# %%

# salva objetos para o arquivo para nao ter que processa-los novamente
# utilizar para depuracao futuramente
# preprocessing.save_trajs_to_file()
# preprocessing.save_trajs_info_to_file()

# %%
# Carrega trajetorias do arquivo sem ter que processa-las
# preprocessing.load_trajs_from_file()
# preprocessing.load_trajs_info_from_file()
trajs = preprocessing.create_moving_pandas_trajectories( gdf_sistram[:] )
# trajs = preprocessing.get_trajs( )
preprocessing.trajs = trajs
trajs_info = preprocessing.trajs_to_df_agg_data( trajs )
preprocessing.trajs_info = trajs_info

# %%
# from joblib import load
# model = load('src/behaviours/fishing_trajectorie_gb.joblib')
# trajs_info = trajs_info[trajs_info["n_points"] > 2 ]
# ypred = model.predict_proba( trajs_info[ ['duration', 'varCourse', 'varSpeed', 'traj_len', 'n_points'] ] )


########### Fishing Trajectories ###################
# %%
ftd = FishingTrajectoryDetection("GB")
# ypred_fishing = ftd.predict_rnn( trajs )
ypred_fishing = ftd.predict_gb( trajs_info )
ypred = np.round(ypred_fishing[:, 1])
# Encontrar índices onde o valor é zero
indices_zero = np.where(ypred == 0)[0]


# %%
# escolher trajetorias para visualizar
traj = trajs.trajectories[6000]
# traj = trajs.get_trajectory("308293000.0_708")
plot_trajectory( traj.df, "Unknow" )

# %%

# # Acertar isso no modelo de FT, vou considerar possiveis traj de pesca trajs com media
# # de veloc < 5 knots, se for maior que 5 não é trajetoria de pesca
for i in range(len(trajs)):
    if trajs.trajectories[i].df['veloc'].mean() > 6:
        ypred_fishing[i, 0] = 0
        ypred_fishing[i, 1] = 1
ypred = np.round(ypred_fishing[:, 1])
# Encontrar índices onde o valor é zero
indices_zero = np.where(ypred == 0)[0]



############## Encounters ###########################
# %%
# Detect encounter beteween vessels using h3
encounter = Encounter( trajs )
df_encounters = encounter.detect_encouters()
db = MetamodelDB()
row_enc = db.insert_encounters( df_encounters )
y_pred_encounters = encounter.get_encounters_on_trajs()

# %%
df_encounters

# %%
# enc_gdf = encounter.get_encounter_by_mmsi( "228329800" )[0]
# mmsis = enc_gdf['mmsi'].unique()
# gdf1 = enc_gdf[enc_gdf['mmsi'] == mmsis[0]]
# gdf2 = enc_gdf[enc_gdf['mmsi'] == mmsis[1]]
# encounter.plot_encounter( gdf1, gdf2 )

# %%
traj_ids = df_encounters[0]['traj_id'].unique()
gdf1 = trajs.get_trajectory( traj_ids[0] ).df
gdf2 = trajs.get_trajectory( traj_ids[1] ).df
encounter.plot_encounter( gdf1, gdf2 )

# %%
#Teste
# df_combined = encounter.df_combined
# # get clusters indexes with only two different MMSIs in cluster
# couting = df_combined.groupby('h3_index')['mmsi'].nunique()
# indexes = couting.where(couting == 2).dropna().index

# %%

############## Loitering ###########################
# se yp_pred == 1 é loitering
loitering = LoiteringTrajectoryDetection( )
y_pred_loitering = loitering.predict_rnn( trajs )


# %%
ypred = np.round(y_pred_loitering[:, 1])
# Encontrar índices onde o valor é hum
indices_zero = np.where(ypred == 0)[0]
# escolher trajetorias para visualizar
traj = trajs.trajectories[8214]
plot_trajectory( traj.df, "Unknow" )

# %%

############## CRIA DF_METAMODELO #################
import pandas as pd
# Criar um DataFrame vazio com essas colunas
df_metamodelo = pd.DataFrame()

df_metamodelo["traj_id"] = trajs_info["traj_id"]
df_metamodelo["ft"]  = ypred_fishing[:,0]
df_metamodelo["enc"] = np.array( y_pred_encounters )
df_metamodelo["loi"] = y_pred_loitering[:,1]
# verify if a vessel has AIS transmission gap in a trajectory in    anytime
da = DarkActivity( gdf_sistram )
trajs_da = da.build_trajectories( )
# da.criar_mapa_historico_multiplo()

# verify if a vessel has AIS transmission gap in a trajectory in anytime
trajs_gap = da.update_gap_on_trajectories(trajs.trajectories, 3)
# trajs_gap = da.update_gap_on_trajectories_paralell(trajs.trajectories, 3)
tg = []
for x in trajs_gap:
    if x == True:
        tg.append( 1 )
    else:
        tg.append( 0 )
df_metamodelo["dark_ship"] = tg

dist = CalcDistanciaCosta( )
df_metamodelo["dist_costa"] = dist.distancia_costa_brasil_array( trajs )

dentro_zee = ( df_metamodelo["dist_costa"] < 200 ).astype(int)
df_metamodelo["dentro_zee"] = dentro_zee

dentro_mt = ( df_metamodelo["dist_costa"] < 12 ).astype(int)
df_metamodelo["dentro_mt"] = dentro_mt

apas = APA()
df_metamodelo["dentro_apa"] = apas.verifica_trajetorias_dentro_apa_binario( trajs )

aiss = AISSpoofing( trajs )
aiss_verify = np.array( aiss.verify_spoofing_position_trajs() )
df_metamodelo["spoofing"] = aiss_verify.astype(int)

az = AnchorageZone( gdf_sistram )
az.build_anchorage_zones( resolution=6 )
trajs_out_of_anchor_zones = az.get_trajs_out_achorage_zones( trajs )
df_metamodelo["out_of_anchor_zone"] = trajs_out_of_anchor_zones

fpso = FPSO(5000)
df_metamodelo["in_fpso_area"] = fpso.is_trajs_inside( trajs )

df_metamodelo["classificacao"] = None
df_metamodelo["predicao"] = None


# %%

############ Criação do DB do metamodelo ############33

# Insere predicao de comportamentos das trajetorias no BD
db = MetamodelDB()
# Inserir o DataFrame no banco de dados
# db.to_sql(df_metamodelo, 'metamodelo', if_exists='replace')
# db.insere_df_metamodelo(df_metamodelo, se_existir='replace')

# %%

# Update Vessel Info
# Filtrar linhas onde 'mmsi' tem exatamente 9 dígitos
df_filtrado = trajs_info[trajs_info['mmsi'].astype(str).apply(len) == 9]
mmsis = df_filtrado["mmsi"].unique().astype(int)
wc = WebCrawler()
wc.baixar_info_navios( mmsis )

# %%
# Load metamodelo with human classification updated
query = "SELECT * FROM metamodelo"
df_metamodelo = db.read_sql(query)


# %%
# Flags
# 0 Brazil, 1 - Unknow, 2 - Other
flag_brazil = []
flag_unknow = []
flag_other = []
for i in range( len(df_metamodelo) ):
    traj_id = df_metamodelo["traj_id"].iloc[i]
    mmsi = traj_id.split("_")[0]
    nome_navio, bandeira, tipo = db.get_info_navio(mmsi)
    if bandeira == None or bandeira.lower() == "unknow" or bandeira.lower() == "unknown":
        flag_brazil.append( 0 )
        flag_unknow.append( 1 )
        flag_other.append( 0 )
    else:
        if bandeira.lower( ) == "brazil" or bandeira.lower( ) == "brasil":
            flag_brazil.append( 1 )
            flag_unknow.append( 0 )
            flag_other.append( 0 )
        else:
            flag_brazil.append( 0 )
            flag_unknow.append( 0 )
            flag_other.append( 1 )


df_metamodelo["flag_brazil"] = flag_brazil
df_metamodelo["flag_unknow"] = flag_unknow
df_metamodelo["flag_other"] = flag_other

# %%
# Type of Vessel in metamodel
# Flags
# 0 Brazil, 1 - Unknow, 2 - Other
type_fishing = []
type_other = []
type_unknow = []
for i in range( len(df_metamodelo) ):
    traj_id = df_metamodelo["traj_id"].iloc[i]
    mmsi = traj_id.split("_")[0]
    nome_navio, bandeira, tipo = db.get_info_navio(mmsi)
    if tipo == None or tipo.lower() == "unknow" or tipo.lower() == "unknown":
        type_fishing.append( 0 )
        type_other.append( 0 )
        type_unknow.append( 1 )
    else:
        if tipo.lower() == "fishing" or tipo.lower().find("fish") > -1 or tipo.lower() == "trawler" :
            type_fishing.append( 1 )
            type_other.append( 0 )
            type_unknow.append( 0 )
        else:
            type_fishing.append( 0 )
            type_other.append( 1 )
            type_unknow.append( 0 )


df_metamodelo["type_fishing"] = type_fishing
df_metamodelo["type_other"] = type_other
df_metamodelo["type_unknow"] = type_unknow

db.insere_df_metamodelo(df_metamodelo, se_existir='replace')



# %%

# # teste para Consultar dados do banco de dados
# query = "SELECT * FROM metamodelo"
# df_lido = db.read_sql(query)

# # Não se esqueça de fechar a conexão quando terminar
# # db.close()
# df_lido

# %%

# db.cria_tabela_trajetorias()

# %%

# # teste para Consultar dados do banco de dados
# query = "SELECT * FROM trajetorias"
# df_lido = db.read_sql(query)
# df_lido

# %%

db.insere_trajs( trajs )

# %%

# teste para Consultar dados do banco de dados
query = "SELECT * FROM trajetorias"
df_lido = db.read_sql(query)
df_lido

# %% 

# traj = db.get_trajectory( "('96214383360627',)_1" )
# plot_trajectory( traj.df, "Unknow" )

# %%

# %%


#################### Active Learning ################
# Inicializa com os parametros utilizavei
# modelAL = ActiveLearningModel(df_metamodelo[["ft", "enc", "loi", "dist_costa", "dentro_apa", "spoofing", "classificacao"]])
# modelAL.fit( )
# Para consultar instâncias para rotular
# instances_to_label = modelAL.query_instances(n_instances=5)
# Atribuição da coluna 'traj_id'
# instances_to_label.loc[:, "traj_id"] = df_metamodelo["traj_id"]
# Atribuição de None para a coluna 'classificacao' (Perguntar ao expert)
# ###instances_to_label.loc[:, "classificacao"] = None
# cria tabela com as linhas a rotular
# db.cria_tabela_al(instances_to_label)
# exibit interface para usuario rotular
# instances_to_label.loc[:, "classificacao"] = "atividade_normal"
# db.set_classificacao_traj("710028340.0_882", "atividade_normal")
# db.set_classificacao_al_traj("710028340.0_882", "atividade_normal")

# %%
# X_new = instances_to_label[["ft", "loi", "dist_costa","dentro_apa"]]
# y_new = instances_to_label["classificacao"]

# Após rotular as instâncias (substitua y_new pelos rótulos reais)
# modelAL.update(
#     X_new=X_new,
#     y_new=y_new
#     )

# Para fazer previsões
# AFAZER: 
# Aplicar regras cinematicas
# Melhorar o algoritmo de deteccao de pesca
# Media de velocidade acima de 5 knots nao é pesca
# Aumentar dataset

# %%
## aplicar um K-Means para agrupar classes e nao termos que sair do zero ao classificar.

from sklearn.cluster import KMeans
import pandas as pd

# Suponha que df é seu DataFrame
# df = pd.read_csv('seu_arquivo.csv')

# Normalizando os dados
from sklearn.preprocessing import StandardScaler
scaler = StandardScaler()
df_scaled = scaler.fit_transform(df_metamodelo[["ft", "enc", "loi", "dentro_apa", "spoofing", "out_of_anchor_zone", "dark_ship", "flag_brazil", "flag_unknow", "flag_other", "type_fishing", "type_other", "type_unknow", "dentro_zee", "dentro_mt", "in_fpso_area"]])

# Aplicando K-Means
kmeans = KMeans(n_clusters=8)  # Escolha o número de clusters
clusters = kmeans.fit_predict(df_scaled)

# Adicionando a coluna de clusters ao DataFrame original
df_metamodelo['cluster_kmeans'] = clusters
db.insere_equivalencia_kmeans( df_metamodelo )
df_metamodelo

# %%
## Aplica dbscan como coldstart

from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

# Suponha que df é seu DataFrame
# df = pd.read_csv('seu_arquivo.csv')

# Normalizando os dados
scaler = StandardScaler()
df_scaled = scaler.fit_transform(df_metamodelo[["ft", "enc", "loi", "dentro_apa", "spoofing", "out_of_anchor_zone", "dark_ship", "flag_brazil", "flag_unknow", "flag_other", "type_fishing", "type_other", "type_unknow", "dentro_zee", "dentro_mt", "in_fpso_area" ]])

dbscan = DBSCAN(eps=4.0, min_samples=8)  # Ajuste esses valores conforme necessário
clusters = dbscan.fit_predict(df_scaled)

# Adicionando a coluna de clusters ao DataFrame original
df_metamodelo['cluster_dbscan'] = clusters

db.insere_df_metamodelo(df_metamodelo, se_existir='replace')
db.insere_equivalencia_dbscan( df_metamodelo )

# %%
modelAL = ActiveLearningModel(df_metamodelo[["ft", "enc", "loi", "dentro_apa", "spoofing", "out_of_anchor_zone", "dark_ship", "flag_brazil", "flag_unknow", "flag_other", "type_fishing", "type_other", "type_unknow", "dentro_zee", "dentro_mt", "in_fpso_area","classificacao"]])
modelAL.fit( )

# predictions = modelAL.predict(df_metamodelo.iloc[100:105][["ft", "loi", "dist_costa"]])
trajs_sem_rot = db.get_trajs_sem_rotulos()
# predictions = modelAL.predict(df_metamodelo.iloc[100:105][["ft", "loi", "dist_costa"]])
# predictions = modelAL.predict_all_labels()
predictions = modelAL.predict(df_metamodelo[["ft", "enc", "loi", "dentro_apa", "spoofing", "out_of_anchor_zone", "dark_ship", "flag_brazil", "flag_unknow", "flag_other", "type_fishing", "type_other", "type_unknow", "dentro_zee", "dentro_mt", "in_fpso_area"]])
df_metamodelo["predicao"] = predictions
db.insere_df_metamodelo(df_metamodelo, se_existir='replace')

# %%

# Configura o indice e cria a coluna classficacao
query = "SELECT * FROM active_learning_update_data"
df_al = db.read_sql(query)
df_al = df_al.set_index("index")
df_al

# %%

# df_al = pd.concat([df_al, instances_to_label], ignore_index=False)

# %%



# %%

# db.execute_sql("DELETE FROM active_learning_update_data")
# %%


# db.set_classificacao_al_traj("710028340.0_882", "atividade_normal")
# %%

apas = APA()
apas.show_apa_brazil()

# %%
gdf_apas = apas.get_gdf()
gdf_apas[ gdf_apas["NAME"].str.contains("cabo", case=False) ]
# %%
gdf_apas[ gdf_apas["SUB_LOC"].str.contains("RJ", case=False) ]
# %%
apas.verifica_trajetoria_dentro_apa( traj )
# %%
wc = WebCrawler()
nome_navio, bandeira, tipo_navio = wc.obter_info_navio(636012804)
nome_navio, bandeira, tipo_navio


# %%

# db.cria_tabela_info_navio()

# %%

# db.insere_info_navio(248717000, nome_navio, bandeira, tipo_navio)

# %%

db.get_info_navio(248717000)


# %%
wc = WebCrawler()
wc.baixar_info_navios( trajs_info["mmsi"].unique() )

# %%

# db.criar_tabela_historico_transmissoes_ais()

# %%
db = MetamodelDB()
da = DarkActivity( gdf_sistram )

# %% 

trajs_da = da.build_trajectories( )

# %%

# verify if a vessel has AIS transmission gap in a trajectory in anytime
trajs_gap = da.update_gap_on_trajectories(trajs_da.trajectories, 3)

# %% analizar a trajetoria

plot_trajectory( trajs_da.trajectories[104].df, 'dark test' )

# %%

trajs_da.trajectories[100].df.iloc[0]

# %%
## Detectcao de DarkShip
# Para cada trajetoria:
## Pegar os dois primeiros pontos e prever o proximo ponto
### Se o proximo ponto recebido dentro da zona prevista, ok;
### Se nao receber o proximo ponto dentro do tempo, testar se é uma dark zone;
### Se for, não é dark ship
### Se nao for, é dark ship

import movingpandas as mpd
import numpy as np
from shapely.geometry import Point
from datetime import timedelta

def predict_position(trajectory, minutes_ahead, method='linear'):
    if method != 'linear':
        raise NotImplementedError("Atualmente, apenas o método 'linear' é suportado.")

    # Verifica se a trajetória tem pelo menos dois pontos
    if len(trajectory.df) < 2:
        raise ValueError("A trajetória precisa ter pelo menos dois pontos para calcular a direção e a velocidade.")

    # Último ponto e o ponto anterior
    last_point = trajectory.get_position_at(trajectory.get_end_time())
    second_last_point = trajectory.df.iloc[-2].geometry

    # Calculando a velocidade
    distance = last_point.distance(second_last_point)  # Distância
    time_diff = (trajectory.get_end_time() - trajectory.df.iloc[-2].name).total_seconds()  # Diferença de tempo em segundos
    if time_diff == 0:
        raise ValueError("Os dois últimos pontos da trajetória têm o mesmo timestamp, impossível calcular a velocidade.")
    speed = distance / time_diff  # Velocidade em unidades espaciais por segundo

    # Calcular a distância prevista baseada no tempo e na velocidade
    time_delta = timedelta(minutes=minutes_ahead)
    predicted_distance = speed * time_delta.total_seconds()

    # Direção do último segmento
    direction = np.arctan2(last_point.y - second_last_point.y, last_point.x - second_last_point.x)

    # Calcular o deslocamento no eixo x e y
    delta_x = predicted_distance * np.cos(direction)
    delta_y = predicted_distance * np.sin(direction)

    # Nova posição prevista
    new_x = last_point.x + delta_x
    new_y = last_point.y + delta_y
    predicted_position = Point(new_x, new_y)

    return predicted_position

gdf_dark = trajs.trajectories[8000].df
tempo = 30
traj = mpd.Trajectory( gdf_dark[0:2], 1 )
prox_ponto = predict_position(traj, tempo, method='linear')
time_delta = timedelta(minutes=tempo)
prox_tempo = traj.df.reset_index()['dh'].iloc[-1] + time_delta
data  = {'dh': [prox_tempo], 'lat':[prox_ponto.y], 'lon': [prox_ponto.x], 'rumo':[0.0], 'veloc':[0.0], 'geometry':[prox_ponto], 'mmsi':[gdf_dark.iloc[0].mmsi], 'nome_navio':[gdf_dark.iloc[0].nome_navio]}
prox_df = pd.DataFrame(data)
prox_df = prox_df.set_index('dh')

# plot_trajectory( pd.concat([ traj.df, prox_df ]), 'dark' )
da.plot_geohash_on_map(pd.concat([ traj.df, prox_df ]), 4)


# %%

da.verifica_navio_historico_transmissao( traj, 30, 5)

# %%

da.plot_gaps_on_map( trajs_da.trajectories[106], 3 )

# %%

da.is_gap_on_trajectory( trajs_da.trajectories[106], 3 )

# %%

# %%

# da.criar_mapa_historico( )

# %%

gdf_sistram.reset_index().dh

# %%

print(gdf_sistram.reset_index().iloc[0].dh.strftime('%Y-%m-%d %H:%M:%S') == "2019-10-22 16:26:52")
# %%

### AIS Spoofing testes

aiss = AISSpoofing( trajs )
aiss_verify = np.array( aiss.verify_spoofing_position_trajs() )

# %%
true_indices = [i for i, value in enumerate(aiss_verify) if value]
print(true_indices)

# %%


plot_trajectory( trajs.trajectories[8173].df, 'AIS Spoofing Test' )




# %%

# Atualizar colunas dos clusters para a classficacao



# %%


cd = CalcDistanciaCosta()
cruzou = cd.verifica_trajetoria_cruzou_costa( trajs.get_trajectory("('188687364514644',)_8") )
cruzou

# %%

az = AnchorageZone( gdf_sistram )
az.build_anchorage_zones( resolution=6 )
points = az.verify_ship_on_anchorage_zones( gdf1 )

# %%
az.draw_polygons_on_map()

# %%
# az.verify_ship_on_anchorage_zones( trajs.trajectories[100].df )
az.verify_ship_on_anchorage_zones( trajs.trajectories[100].df )

# %%

az.draw_ship_on_anchor_zones( trajs.trajectories[100].df )

# %%

trajs_out_of_anchor_zones = az.get_trajs_out_achorage_zones( trajs )

# %%

plot_trajectory( gdf1, 'Out of Achorage Zones' )





# %%
poly = az.gdf_poly
# %%
gdf = gdf_sistram
#%%

# %%
plot_trajectory(gdf1, "kk")
# %%
# Teste plot encounters
result_enc = db.get_encounters_by_traj_id( "367533290_0")
gdf1 = trajs.get_trajectory(result_enc[0][1]).to_point_gdf()
gdf2 = trajs.get_trajectory(result_enc[0][2]).to_point_gdf()
m = encounter.plot_encounter(gdf1, gdf2)
m.save("templates/encounter.html")





# %%
## Plot test
import geopandas as gpd
from shapely.geometry import Polygon

# Retângulo 1: Latitude entre 23°S e 28°S, Longitude entre 44°W e 48°W
retangulo1 = Polygon([(-48, -23), (-44, -23), (-44, -28), (-48, -28)])

# Retângulo 2: Latitude entre 18°S e 23°S, Longitude entre 41°W e 44°W
retangulo2 = Polygon([(-44, -18), (-41, -18), (-41, -23), (-44, -23)])

# Criando um GeoDataFrame
gdf = gpd.GeoDataFrame({'id': [1, 2], 'geometry': [retangulo1, retangulo2]})

az = AnchorageZone(None)
az.gdf_poly = gdf
az.draw_polygons_on_map()



# %%
df = gpd.read_file("src/rules/fpso.csv")
# %%
## Test performance class
perf = Performance()
perf.calc_acc( )

# %%
# Teste para associar o dbscan com os rotulos.
# Função para associar os rótulos aos grupos

db = MetamodelDB()
# db.insere_equivalencia_dbscan( df_metamodelo )
# %%
db = MetamodelDB()
db.get_string_dbscan("2")
# %%
db = MetamodelDB()
# db.insere_equivalencia_kmeans( df_metamodelo )

# %%
db = MetamodelDB()
db.get_string_kmeans('2')
# %%

# 1. Ler df_metamodel;
# 2. Exibir para os usuarios das trajetorias;
# 3. Usuario classifica trajetoria e salva em df_metamodel;
# 4. Atualiza BD;

# %%

from src.database.metamodel_base import MetamodelDB
import multiprocessing
import geopandas as gpd
import pickle
import movingpandas as mpd
import numpy as np
from flask import Flask, render_template, request, redirect, url_for
from src.tools.web_crawler import WebCrawler
from src.decision_support import DecisionSupport
from src.behaviours.dark_activity import DarkActivity
from src.behaviours.encounter import Encounter
from src.rules.fpso import FPSO
import random

app = Flask(__name__)

# Estrutura de dados atualizada com informações adicionais
trajetorias = [
    [
        {'coords': (37.7749, -122.4194), 'info': {'nome': 'Ponto 1', 'direcao': 'Norte', 'velocidade': '60km/h'}},
        {'coords': (34.0522, -118.2437), 'info': {'nome': 'Ponto 2', 'direcao': 'Leste', 'velocidade': '65km/h'}},
        {'coords': (36.1699, -115.1398), 'info': {'nome': 'Ponto 3', 'direcao': 'Sul', 'velocidade': '70km/h'}}
    ],
    [
        {'coords': (37.7749, -122.4194), 'info': {'nome': 'Ponto K', 'direcao': 'Norte', 'velocidade': '60km/h'}},
        {'coords': (34.0522, -118.2437), 'info': {'nome': 'Ponto K', 'direcao': 'Leste', 'velocidade': '65km/h'}},
        {'coords': (36.1699, -115.1398), 'info': {'nome': 'Ponto K', 'direcao': 'Sul', 'velocidade': '70km/h'}}
    ],    
    # Mais trajetórias...
]

def traj_df_to_geo( df ):
    # Converter DataFrame para a estrutura de dados desejada
    trajetorias = []
    for _, row in df.iterrows():
        ponto = {
            'coords': (row['lat'], row['lon']),
            'info': {
                'mmsi': row['mmsi'],
                'nome': row['nome_navio'],
                'direcao': row['rumo'],
                'velocidade': row['veloc'],
                'speed_nm': round(row['speed_nm'], 2),    
                'timestamp': row['dh']
            }
        }
        trajetorias.append(ponto)  # Cada ponto é uma trajetória separada
    return trajetorias


@app.route('/')
@app.route('/<int:trajetoria_id>')
def index(trajetoria_id=0):

    # Inicializa BD
    db = MetamodelDB()
    query = "SELECT * FROM metamodelo WHERE classificacao is NULL and synthetic = 1"
    df_metamodelo = db.read_sql(query)

    # somente trajetorias sintéticas para o coldstart
    n_syntetic = len(df_metamodelo)
    print(n_syntetic)
    trajetoria_id = random.randint(0, n_syntetic-1)
    
    traj_meta = df_metamodelo.iloc[ trajetoria_id ]
    traj_id = traj_meta["traj_id"]
    meta_id = traj_meta["id"]
    ft=round(traj_meta["ft"]*100,2)
    # enc=round(traj_meta["enc"]*100,2)
    enc="Sim" if traj_meta["enc"] == 1 else "Não"
    loi=round(traj_meta["loi"]*100,2)
    classificacao=traj_meta["classificacao"]
    dist_costa=round(traj_meta["dist_costa"],2)
    apa = "Sim" if traj_meta["dentro_apa"] == 1 else "Não"
    predicao=traj_meta["predicao"]
    # spoofing=traj_meta["spoofing"]*100
    spoofing="Sim" if traj_meta["spoofing"] == 1 else "Não"
    # dark_ship=traj_meta["dark_ship"]*100
    dark_ship="Sim" if traj_meta["dark_ship"] == 1 else "Não"
    out_of_anchor_zone="Sim" if traj_meta["out_of_anchor_zone"] ==0 else "Não"

    in_fpso_area="Sim" if traj_meta["in_fpso_area"] == 1 else "Não"
    
    predicao_kmeans = traj_meta["cluster_kmeans"]
    if predicao_kmeans != None:
        predicao_kmeans = db.get_string_kmeans( predicao_kmeans )
    else:
        predicao_kmeans = "-"
    
    predicao_dbscan = traj_meta["cluster_dbscan"]
    if predicao_dbscan != None:
        predicao_dbscan = db.get_string_dbscan( predicao_dbscan )
    else:
        predicao_dbscan = '-'


    traj_fk = int(traj_meta['traj_fk'])
    print(trajetoria_id)
    print(traj_id)
    print("traj_fk = " + str(traj_fk) )

    traj = db.get_trajectory( traj_fk )
    df = traj.df.reset_index()
    trajetoria_atual = traj_df_to_geo( df )
    count_total = len(df_metamodelo)
    # count_sem_rotulos = db.count_trajs_sem_rotulos()
    count_sem_rotulos = len( df_metamodelo[ df_metamodelo['classificacao'].isnull() ] )
    count_com_rotulos = db.count_trajs_com_rotulos()
    
    
    wc = WebCrawler()
    nome_navio, bandeira, tipo_navio = wc.obter_info_navio( int(df['mmsi'].iloc[0]) )
    print(df['mmsi'].iloc[0], nome_navio, bandeira, tipo_navio)
    db.close()

    # get flag from df_metamodelo
    if traj_meta["flag_brazil"] == 1:
        bandeira = "Brazil"
    else:
        if traj_meta["flag_other"] == 1:
            bandeira = "Other" + "(" + bandeira + ")"
        else:
            bandeira = "Unknow"

    # get vessel type from df_metamodelo
    # get vessel type from df_metamodelo
    if traj_meta["type_other"] == 1:
        tipo_navio = "Other" + "(" + tipo_navio + ")"
    elif traj_meta["type_fishing"] == 1:
        tipo_navio = "Fishing"
    else:
        tipo_navio = "Unknow"



    # if trajetoria_id >= len(trajetorias):
    #     return "Todas as trajetórias foram classificadas!"
    # trajetoria_atual = trajetorias[trajetoria_id]
    
    mmsi = traj_id.split("_")[0]

    sog_mean = round(traj_meta['sog_diff'], 2)
    print("sog_mean: " + str(sog_mean))
    
    mmsi = traj_id.split("_")[0]

    mmsi_valid = traj_meta['mmsi_valid']
    if mmsi_valid == 0.5:
        mmsi_valid = "Valid"
    elif mmsi_valid == 1:
        mmsi_valid = "Brazil Valid"
    else:
        mmsi_valid = "Invalid"

    type_vessel = "Unknow"
    if traj_meta["type_fishing"] == 1:
        type_vessel = "Fishing"
    elif traj_meta["type_offshore"] == 1 :
        type_vessel = "Offshore"
    elif traj_meta["type_tanker"] == 1 :
        type_vessel = "Tanker"
    elif traj_meta["type_tug"] == 1 :
        type_vessel = "Tug"
    elif traj_meta["type_anti_pollution"] == 1 :
        type_vessel = "Anti Pollution"
    elif traj_meta["type_cargo"] == 1 :
        type_vessel = "Cargo"
    elif traj_meta["type_research"] == 1 :
        type_vessel = "Research"
    elif traj_meta["type_buoy"] == 1 :
        type_vessel = "Buoy"
    elif traj_meta["type_other"] == 1 :
        type_vessel = "Other"

    time_stopped_h = round(traj_meta["time_stopped_h"],2)

    return render_template('index.html', 
                           trajetoria_atual=trajetoria_atual, 
                           trajetoria_id=meta_id,
                           traj_id=traj_id,
                           ft=ft,
                           enc=enc,
                           loi=loi,
                           spoofing=spoofing,
                           gap=dark_ship,
                           dist_costa=dist_costa,
                           out_of_anchor_zone=out_of_anchor_zone,
                           in_fpso_area=in_fpso_area,
                           classificacao=classificacao,
                           predicao=predicao,
                           count_total=count_total, 
                           count_com_rotulos=count_com_rotulos,
                           apa=apa,
                           nome_navio=nome_navio,
                           bandeira=bandeira,
                           tipo_navio=tipo_navio,
                           predicao_kmeans=predicao_kmeans,
                           predicao_dbscan=predicao_dbscan,
                           traj_fk=traj_fk,
                           mmsi=mmsi,
                           sog_mean=sog_mean,
                           mmsi_valid=mmsi_valid,
                           type_vessel=type_vessel,
                           time_stopped_h=time_stopped_h
                           )

@app.route('/classificar/<int:meta_id>', methods=['POST'])
def classificar(meta_id):
    classificacao = request.form.get('classificacao')
    print(f"Trajetória {meta_id} classificada como: {classificacao}")

    if classificacao == "proximo":
        return redirect(url_for('index', trajetoria_id=meta_id + 1))    

    if classificacao == "anterior":
        return redirect(url_for('index', trajetoria_id=(meta_id - 1) ))    

    ds = DecisionSupport( )
    ds.insert_specialist_response_id( meta_id, classificacao )

    # db = MetamodelDB()
    # query = "SELECT * FROM metamodelo"
    # df_metamodelo = db.read_sql(query)
    # traj_id = df_metamodelo.iloc[ meta_id ]["traj_id"]
    # db.set_classificacao_traj( traj_id, classificacao )
    # db.close()

    # rand the next sintetyc traj
    n_syntetic = 1848
    next_traj = random.randint(0, n_syntetic)

    return redirect(url_for('index', trajetoria_id=0))

@app.route('/encounter/<traj_fk>')
def encounter(traj_fk):
    print("traj_fk: ", traj_fk)
    db = MetamodelDB()
    result_enc = db.get_encounters_by_traj_id( traj_fk )
    print(result_enc)
    if not result_enc:
        return "Trajetória sem encontros!"

    gdf1 = db.get_trajectory(result_enc[0][0]).to_point_gdf()    
    gdf2 = db.get_trajectory(result_enc[0][1]).to_point_gdf()
    print(gdf2)

    fpso = FPSO(15000)
    m_fpso = fpso.plot_fpsos( )

    enc = Encounter(None)
    m = enc.plot_encounter(gdf1, gdf2, m_fpso)
    m.save("templates/encounter.html")

    return render_template('encounter.html')

@app.route('/gap/<mmsi>/<precision>')
def gap(mmsi, precision):
    print("mmsi: ", mmsi)
    print("precision: ", precision)
    
    precision = int(precision)
    if precision < 2 or precision > 5:
        return "Incorrect precision parameter!!"

    db = MetamodelDB()
    gdfs = db.get_gdf_trajectories_by_mmsi( mmsi )
    if len( gdfs ) > 0:
        da = DarkActivity( gdfs ) 
        da.build_trajectories( )
        m = da.plot_gaps_on_map( da.trajs.trajectories[0], precision )
        m.save("templates/gap.html")
    else:
        print("MMSI not founded!")

    return render_template('gap.html')


if __name__ == '__main__':

    app.run(debug=True)



# # %%

# # Inicializa BD
# db = MetamodelDB()

# # %%

# # teste para Consultar dados do banco de dados
# query = "SELECT * FROM metamodelo"
# df_lido = db.read_sql(query)

# # Não se esqueça de fechar a conexão quando terminar
# # db.close()
# df_lido

# # %%

# # teste para Consultar dados do banco de dados
# query = "SELECT * FROM trajetorias"
# df_lido = db.read_sql(query)
# df_lido
# # %%

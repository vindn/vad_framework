# 1. Ler df_metamodel;
# 2. Exibir para os usuarios das trajetorias;
# 3. Usuario classifica trajetoria e salva em df_metamodel;
# 4. Atualiza BD;

# %%

from src.database.metamodel_base import MetamodelDB
from src.metamodel.active_learning import ActiveLearningModel
from src.tools.web_crawler import WebCrawler
from src.behaviours.encounter import Encounter
from src.rules.fpso import FPSO
from src.rules.apa import APA
from src.impact_assessment import ImpactAssessment
from src.decision_support import DecisionSupport
from src.behaviours.dark_activity import DarkActivity
from src.tools.performance import Performance
import multiprocessing
import geopandas as gpd
import pickle
import movingpandas as mpd
import numpy as np
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

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
        trajetorias.append(ponto)  # Cada ponto eh uma trajetória separada
    return trajetorias



@app.route('/')
@app.route('/<int:trajetoria_id>')
def index(trajetoria_id=0):

    # Impact Assessment
    # Query instances on cold star or AL and show to Human operator
    db = MetamodelDB( )
    ia = ImpactAssessment( meta_model=None, min_cold_start_rows = 100 )
    row, prediction = ia.query_instances_and_predict( )
    traj_id = row["traj_id"]

    print(row)    

    if prediction is not None:
        prediction = prediction[0]

    # Preenche dados da trajetoria no html
    ft=round(row["ft"]*100,2)
    # enc=round(row["enc"]*100,2)
    enc="Sim" if row["enc"] == 1 else "Não"
    loi=round(row["loi"]*100,2)
    classificacao=row["classificacao"]
    dist_costa=round(row["dist_costa"],2)
    apa = "Sim" if row["dentro_apa"] == 1 else "Não"
    # predicao=row["predicao"]
    predicao=prediction
    # predicao=row["predicao"]
    spoofing="Sim" if row["spoofing"] == 1 else "Não"
    # spoofing=row["spoofing"]*100
    # dark_ship=row["dark_ship"]*100
    dark_ship="Sim" if row["dark_ship"] == 1 else "Não"
    out_of_anchor_zone="Sim" if row["out_of_anchor_zone"] ==0 else "Não"

    in_fpso_area="Sim" if row["in_fpso_area"] == 1 else "Não"

    # Get associated cluster with activity
    predicao_kmeans = row["cluster_kmeans"]
    print("predicao kmeans: " + str(predicao_kmeans) )
    predicao_kmeans = db.get_string_kmeans( predicao_kmeans )
    
    # Get associated cluster with activity
    predicao_dbscan = row["cluster_dbscan"]
    print("predicao dbscan: " + str(predicao_dbscan) )
    predicao_dbscan = db.get_string_dbscan( predicao_dbscan )

    traj_fk = int(row['traj_fk'])
    print(trajetoria_id)
    print(traj_id)
    print("traj_fk = " + str(traj_fk) )
    
    traj = db.get_trajectory( traj_fk )
    df = traj.df.reset_index()
    trajetoria_atual = traj_df_to_geo( df )
    count_total = db.count_trajs( )
    count_sem_rotulos = db.count_trajs_sem_rotulos()
    count_com_rotulos = count_total - count_sem_rotulos
    
    wc = WebCrawler()
    nome_navio, bandeira, tipo_navio = wc.obter_info_navio( int(df['mmsi'].iloc[0]) )
    print(df['mmsi'].iloc[0], nome_navio, bandeira, tipo_navio)
    db.close()
    # get flag from df_metamodelo
    if row["flag_brazil"] == 1:
        bandeira = "Brazil"
    else:
        if row["flag_other"] == 1:
            bandeira = "Other" + "(" + bandeira + ")"
        else:
            bandeira = "Unknow"

    # get vessel type from df_metamodelo
        
    if row["type_fishing"] == 1:
        tipo_navio = "Fishing"
    elif row["type_unknow"] == 1:
        tipo_navio = "Unknow"
    else:
        tipo_navio = "Other" + "(" + tipo_navio + ")"

    trajetoria_id = row["id"]
    # if trajetoria_id >= len(trajetorias):
    #     return "Todas as trajetórias foram classificadas!"
    # trajetoria_atual = trajetorias[trajetoria_id]
    sog_mean = round(row['sog_diff'], 2)
    print("sog_mean: " + str(sog_mean))
    
    mmsi = traj_id.split("_")[0]
    
    mmsi_valid = row['mmsi_valid']
    if mmsi_valid == 0.5:
        mmsi_valid = "Valid"
    elif mmsi_valid == 1:
        mmsi_valid = "Brazil Valid"
    else:
        mmsi_valid = "Invalid"

    type_vessel = "Unknow"
    if row["type_fishing"] == 1:
        type_vessel = "Fishing"
    elif row["type_offshore"] == 1 :
        type_vessel = "Offshore"
    elif row["type_tanker"] == 1 :
        type_vessel = "Tanker"
    elif row["type_tug"] == 1 :
        type_vessel = "Tug"
    elif row["type_anti_pollution"] == 1 :
        type_vessel = "Anti Pollution"
    elif row["type_cargo"] == 1 :
        type_vessel = "Cargo"
    elif row["type_research"] == 1 :
        type_vessel = "Research"
    elif row["type_buoy"] == 1 :
        type_vessel = "Buoy"
    elif row["type_other"] == 1 :
        type_vessel = "Other"


    time_stopped_h = round(row["time_stopped_h"],2)

    lr = 0
    # if count_com_rotulos % 10 == 0:
    #     lr = str(Performance.learning_rate( ))
    #     print("lr: " + lr)

    return render_template('index.html', 
                           trajetoria_atual=trajetoria_atual, 
                           trajetoria_id=trajetoria_id,
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
                           time_stopped_h=time_stopped_h,
                           lr=lr
                           )

@app.route('/classificar/<meta_id>', methods=['POST'])
def classificar(meta_id):
    classificacao = request.form.get('classificacao')
    print(f"Trajetória {meta_id} classificada como: {classificacao}")

    ds = DecisionSupport( )
    ds.insert_specialist_response_id( meta_id, classificacao, 'op1' )
    # ds.set_classificacao_traj_performance( traj_id, classificacao, 100 )

    # db = MetamodelDB()
    # query = "SELECT * FROM metamodelo"
    # df_metamodelo = db.read_sql(query)
    # traj_id = df_metamodelo.iloc[ trajetoria_id ]["traj_id"]
    # # db.set_classificacao_traj( traj_id, classificacao )
    # db.set_classificacao_traj_performance( df_metamodelo.iloc[ trajetoria_id ], classificacao )
    # db.close()

    return redirect(url_for('index', traj_id=meta_id))
    # return redirect(url_for('/'))

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

@app.route('/apa/<traj_fk>')
def apa(traj_fk):
    print("traj_fk: ", traj_fk)
    db = MetamodelDB()
    traj = db.get_trajectory( traj_fk )
    print(traj)

    apa = APA()
    m = apa.plot_apa( traj.df )

    m.save("templates/apa.html")

    return render_template('apa.html')



if __name__ == '__main__':

    app.run(debug=True)

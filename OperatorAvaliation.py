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
from OperatorBot import ClassificadorTrajetorias

# %%
# COLD START, somente sintético
# Funcionou bem, após isso, avaliar 200 trajetórias com AL manualmente.
db = MetamodelDB( )
ia = ImpactAssessment( meta_model=None, min_cold_start_rows = 10, size=3000 )

ct = ClassificadorTrajetorias()
ds = DecisionSupport( )

meta_model = db.get_meta_model( )

n_avalicoes = 380
ia.update_all_models( )
rows = ia.query_instances( n_instances=n_avalicoes )
predictions = ia.modelAL.predict(rows)
for i, (index, r) in enumerate(rows.iterrows()):
    row = meta_model.iloc[index]
    classificacao = ct.classificar( row )   
    ds.insert_specialist_response_id( int(row.id), classificacao, 'op1' )
    meta_model.at[i, 'predicao'] = predictions[i]

db.update_metamodel_by_field( meta_model['id'], meta_model['predicao'], 'predicao')

# %%

## Test performance class
perf = Performance()
# perf.calc_acc_by_class( )
# perf.calc_acc( )
# perf.confusion_matrix_plot( op="op1" )
# perf.precision_recall_f1( )
# perf.calculate_metrics( op='op1')
perf.count(op="op1")


# %%
# ESTE É UM TESTE! (NÃO FUNCIONOU BEM!)
# Avalia 100 trajetorias de cada classe e testa acc
import random
db = MetamodelDB( )
ds = DecisionSupport( )
ia = ImpactAssessment( meta_model=None, min_cold_start_rows = 100 )
ct = ClassificadorTrajetorias()
min_class_each = 100
op="op1"
meta_model = db.get_meta_model( )
end = False

ia.update_all_models( )
print("PESCA ILEGAL")
n_ilf = db.get_operators_classification_count( op, 'pesca_ilegal' )
for j in range(min_class_each):
    # verify if op1 rated the at least min_class_each classes for illegal fishing.  
    if n_ilf < min_class_each:
        # df_illegal_fishing_trajs = meta_model[ (meta_model["predicao"] == "pesca_ilegal") & (meta_model["classificacao"].isnull() ) & ( meta_model["traj_id"].str.len() < 13) ]
        df_illegal_fishing_trajs = meta_model[ (meta_model["predicao"] == "pesca_ilegal") & (meta_model["classificacao"].isnull() ) ]
        # print('len = ' + str(len(df_illegal_fishing_trajs)))
        n_rand = random.randint(0, len(df_illegal_fishing_trajs)-1)
        # print('nrand = ' + str(n_rand))
        row = df_illegal_fishing_trajs.iloc[ n_rand ]
        prediction = "pesca_ilegal"
        classificacao = ct.classificar( row )   
        meta_model.loc[ meta_model['id']==row.id, 'classificacao'] = classificacao
        #[al, km, dbscan]
        ds.insert_specialist_response_id( int(row.id), classificacao, op )
        n_ilf += 1
    else:
        break

ia.update_all_models( )
meta_model = db.get_meta_model( )
print("ATIVIDADE SUSPEITA")
n_sus = db.get_operators_classification_count( op, 'atividade_suspeita' )
for j in range(min_class_each):    
    # verify if op1 rated the at least min_class_each classes for suspicius.
    if n_sus < min_class_each:
        df_susp_trajs = meta_model[ (meta_model["predicao"] == "atividade_suspeita") & (meta_model["classificacao"].isnull() ) & (meta_model["sog_diff"] <= 8) & (meta_model["dist_costa"] > 2) ]
        n_rand = random.randint(0, len(df_susp_trajs)-1)
        row = df_susp_trajs.iloc[ n_rand ]
        prediction = "atividade_suspeita"
        classificacao = ct.classificar( row )   
        meta_model.loc[ meta_model['id']==row.id, 'classificacao'] = classificacao
        ds.insert_specialist_response_id( int(row.id), classificacao, op )
        n_sus += 1
    else:
        break

ia.update_all_models( )
meta_model = db.get_meta_model( )
print("ATIVIDADE ANOMALA")
n_anon = db.get_operators_classification_count( op, 'atividade_anomala' )
for j in range(min_class_each):
    # verify if op1 rated the at least min_class_each classes for anonmalous.    
    if n_anon < min_class_each:
        # df_anon_trajs = meta_model[ (meta_model["predicao"] == "atividade_anomala") & (meta_model["classificacao"].isnull() ) & (meta_model["sog_diff"] <= 6 ) & (meta_model["dist_costa"] > 2) & (meta_model["type_unknow"] == 1) & ( (meta_model["ft"] > 0.5) | (meta_model["type_buoy"] == 1) )]
        df_anon_trajs = meta_model[ (meta_model["predicao"] == "atividade_anomala") & (meta_model["classificacao"].isnull() ) & (meta_model["sog_diff"] <= 6 ) & (meta_model["dist_costa"] > 2) & (meta_model["type_unknow"] == 1) ]
        n_rand = random.randint(0, len(df_anon_trajs)-1)
        row = df_anon_trajs.iloc[ n_rand ]
        prediction = "atividade_anomala"
        classificacao = ct.classificar( row )   
        meta_model.loc[ meta_model['id']==row.id, 'classificacao'] = classificacao
        ds.insert_specialist_response_id( int(row.id), classificacao, op )
        n_anon += 1
    else:
        break

ia.update_all_models( )
meta_model = db.get_meta_model( )
print("ATIVIDADE NORMAL")
n_normal = db.get_operators_classification_count( op, 'atividade_normal' )
for j in range(min_class_each):    
    # verify if op1 rated the at least min_class_each classes for normal.                
    if n_normal < min_class_each:
        df_normal_trajs = meta_model[ (meta_model["predicao"] == "atividade_normal") & (meta_model["classificacao"].isnull() ) ]
        n_rand = random.randint(0, len(df_normal_trajs)-1)
        row = df_normal_trajs.iloc[ n_rand ]
        prediction = "atividade_normal"
        classificacao = ct.classificar( row )   
        meta_model.loc[ meta_model['id']==row.id, 'classificacao'] = classificacao
        ds.insert_specialist_response_id( int(row.id), classificacao, op )
        n_normal += 1
    else:
        break


perf = Performance()
# perf.calculate_metrics(op="op1")
perf.count(op="op1")


# %%

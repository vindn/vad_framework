# Realiza análises para entender o contexto ou situação geral, como padrões de movimento. (Nivel 2)
# Fusão dos dados dos meta modelos
# inferir dados no meta modelo

from src.database.metamodel_base import MetamodelDB
from src.object_level_fusion import ObjectLevelFusion
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from src.metamodel.active_learning import ActiveLearningModel

class SituationalAwareness:
    def __init__(self, olf):

        if not isinstance(olf, ObjectLevelFusion):
            raise TypeError("Parameter is not instance of ObjectLevelFusion Class!")

        self.olf = olf
        self.db = MetamodelDB( )
        # self.model_outputs = model_outputs
        self.meta_model_incoming = self.olf.get_meta_model()
        self.meta_model = self.load_meta_model_from_db( )
        self.meta_model = pd.concat( [self.meta_model, self.meta_model_incoming ] )
        self.parameters = ["ft", "enc", "loi", "dentro_apa", "spoofing", "out_of_anchor_zone", "dark_ship", "flag_brazil", "flag_unknow", "flag_other", "type_fishing", "type_other", "type_unknow", "type_offshore", "type_tanker", "type_tug", "type_anti_pollution", "type_cargo", "dentro_zee", "dentro_mt", "in_fpso_area", "arriving", "time_stopped_h"]

    
    def execute_kmeans_predictions( self ):
        ## aplicar um K-Means para agrupar classes e nao termos que sair do zero ao classificar.

        # Normalizando os dados
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler()
        df_scaled = scaler.fit_transform(self.meta_model[ self.parameters ])

        # Aplicando K-Means
        kmeans = KMeans(n_clusters=8)  # Escolha o número de clusters
        clusters = kmeans.fit_predict(df_scaled)
        # Adicionando a coluna de clusters ao DataFrame original
        self.meta_model['cluster_kmeans'] = clusters
        # Faz a correlação entre o número do grupo e a atividade
        self.db.insere_equivalencia_kmeans( self.meta_model )
    
    def execute_dbscan_predictions( self ):
        ## Aplica dbscan como coldstart

        # Normalizando os dados
        scaler = StandardScaler()
        df_scaled = scaler.fit_transform(self.meta_model[ self.parameters ])

        dbscan = DBSCAN(eps=4.0, min_samples=8)  # Ajuste esses valores conforme necessário
        clusters = dbscan.fit_predict(df_scaled)

        # Adicionando a coluna de clusters ao DataFrame original
        self.meta_model['cluster_dbscan'] = clusters
        # Faz a correlação entre o número do grupo e a atividade
        self.db.insere_equivalencia_dbscan( self.meta_model )


    def save_meta_model_to_db( self ):
        # self.db.insere_df_metamodelo(self.meta_model, se_existir='replace')
        self.db.save_df_metamodelo( self.meta_model )

    def load_meta_model_from_db(self):
        # Load metamodelo with human classification updated
        query = "SELECT * FROM metamodelo"
        meta_model = self.db.read_sql(query)
        return meta_model

    def fuse_data(self):
        #  self.execute_dbscan_predictions( )
        #  self.execute_kmeans_predictions( )
        #  try:
        #     self.execute_active_learning_predictions( )
        #  except Exception as e:
        #      print("AL error! It's necessary at least 1 classification in the row in metamodel. Do it a cold start!: ", e)
         self.save_meta_model_to_db( )

    def get_metamodel( self ):
        return self.load_meta_model_from_db( )
    

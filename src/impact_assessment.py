# Fusão de dados em nível de impacto
# Foca na interpretação dos dados para previsão e avaliação de consequências futuras. (Nivel 3)
# Implementar aqui:
# Active learning para atualizar o metamodelo
# treinar metamodelo, coletar respostas do especialista

from src.situacional_awareness import SituationalAwareness
from src.metamodel.active_learning import ActiveLearningModel
from src.database.metamodel_base import MetamodelDB
import random
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import MinMaxScaler

# Função de normalização
def time_stopped_norm(val):
    # 1 week - 7 days * 24 hours
    if val > 168:
        return 1
    else:
        return val / 168

class ImpactAssessment:
    def __init__(self, meta_model=None, min_cold_start_rows = 100, size=0):
        
        self.db = MetamodelDB()
        if meta_model is None:
            self.meta_model = self.load_meta_model_from_db( )
            # JUST FOR 1DN training, after that remove this line!!
            if size > 100:
                self.meta_model = self.meta_model[:size]
        else:
            self.meta_model = meta_model

        # Normaliza distancia de acordo com o tamanho da ZEE (200MN)
        self.meta_model['dist_costa_normalizado'] = self.meta_model['dist_costa'] / 200.0
        # Criar um objeto MinMaxScaler
        scaler = MinMaxScaler()
        self.meta_model['cog_diff_norm'] = scaler.fit_transform(self.meta_model[['cog_diff']])
        self.meta_model['sog_diff_norm'] = scaler.fit_transform(self.meta_model[['sog_diff']])
        
        #normalization
        self.meta_model['time_stopped_h_norm'] = self.meta_model['time_stopped_h'].apply(time_stopped_norm)
        
        self.parameters = ["ft", "enc", "loi", "dentro_apa", "spoofing", "out_of_anchor_zone", "dark_ship", "flag_brazil", "flag_unknow", "flag_other", "type_fishing", "type_other", "type_unknow", "type_offshore", "type_tanker", "type_tug", "type_anti_pollution", "type_research", "type_cargo", "type_research", "type_buoy", "dentro_zee", "dentro_mt", "in_fpso_area", "dist_costa_normalizado", "cog_diff_norm", "sog_diff_norm", "mmsi_valid", "arriving", "time_stopped_h_norm"]
        # self.modelAL = ActiveLearningModel(self.meta_model[ self.parameters + ["classificacao"] ])
        # self.modelAL.fit( )
        self.min_cold_start_rows = min_cold_start_rows

    def execute_active_learning_predictions( self ):

        # verificar se foi feito cold start
        count_rows_with_label = self.db.count_trajs_com_rotulos( )

        if count_rows_with_label > self.min_cold_start_rows:           
            modelAL = ActiveLearningModel(self.meta_model[ self.parameters + ["classificacao"] ])
            modelAL.fit( )
            
            # trajs_sem_rot = self.db.get_trajs_sem_rotulos()
            predictions = modelAL.predict(self.meta_model[ self.parameters ])
            self.meta_model["predicao"] = predictions
            return True
        else:
            print("It's no possibile execute AL. First, do a cold start!")
            return False

    def query_instances( self, n_instances=1 ):
        self.modelAL = ActiveLearningModel(self.meta_model[ self.parameters + ["classificacao"] ])
        self.modelAL.fit( )        

        # Para consultar instâncias para rotular
        instances_to_label = self.modelAL.query_instances(n_instances)

        return instances_to_label

    def query_instances_and_predict( self, n_instances=1 ):
        
        # verificar se foi feito cold start
        count_rows_with_label = self.db.count_trajs_com_rotulos( )

        if count_rows_with_label > self.min_cold_start_rows:           
            self.modelAL = ActiveLearningModel(self.meta_model[ self.parameters + ["classificacao"] ])
            self.modelAL.fit( )

            # Para consultar instâncias para rotular
            instances_to_label = self.modelAL.query_instances(n_instances)
            idx = instances_to_label.index
            meta_id = int(idx[0])
            traj_id = self.meta_model[ "traj_id" ].iloc[ meta_id ]
            traj_meta = self.meta_model[ self.parameters ].iloc[ meta_id:meta_id+1 ]

            prediction = self.modelAL.predict(traj_meta)

            traj_meta = self.meta_model.iloc[ meta_id ]
        else:
            # cold start - randomize a row
            n = random.randint(0, len(self.meta_model))
            traj_meta = self.meta_model.iloc[ n ]
            print( "classificacao: ", traj_meta["classificacao"] )
            while traj_meta["classificacao"] is not None:
                n = random.randint(0, len(self.meta_model))
                traj_meta = self.meta_model.iloc[ n ]

            prediction = None

        return traj_meta, prediction


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
        print("kmeans predictions...")
        print(clusters[:10])
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

    def execute_hdbscan_predictions( self ):
        import hdbscan
        ## Aplica dbscan como coldstart

        # Normalizando os dados
        scaler = StandardScaler()
        df_scaled = scaler.fit_transform(self.meta_model[ self.parameters ])

        # Criando o modelo HDBSCAN
        h_dbscan = hdbscan.HDBSCAN(min_cluster_size=8)

        # Ajustando o modelo aos dados
        h_dbscan.fit(df_scaled)

        # Obtendo os rótulos dos clusters
        labels = h_dbscan.labels_
        print("hdbscan predictions...")
        print(labels[:10])
        # Adicionando a coluna de clusters ao DataFrame original
        self.meta_model['cluster_dbscan'] = labels
        # Faz a correlação entre o número do grupo e a atividade
        self.db.insere_equivalencia_dbscan( self.meta_model )



    def update_all_models( self ):
        self.execute_active_learning_predictions( )
      
        # self.execute_hdbscan_predictions( )
        # self.execute_kmeans_predictions( )
        
        self.save_predictions_to_db( ) 

    def load_meta_model_from_db(self):
        # Load metamodelo with human classification updated
        query = "SELECT * FROM metamodelo"
        meta_model = self.db.read_sql(query)
        return meta_model
    
    def save_meta_model_to_db( self ):
        # self.db.insere_df_metamodelo(self.meta_model, se_existir='replace')
        # retira a coluna da distancia normalizada, retira colunas normalizada de cog e sog
        self.db.save_df_metamodelo(self.meta_model.iloc[:, :-3])

    def save_predictions_to_db( self ):       
        self.db.update_metamodel_by_field( self.meta_model['id'], self.meta_model['predicao'], 'predicao')
        self.db.update_metamodel_by_field( self.meta_model['id'], self.meta_model['cluster_dbscan'].tolist(), 'cluster_dbscan')
        self.db.update_metamodel_by_field( self.meta_model['id'], self.meta_model['cluster_kmeans'].tolist(), 'cluster_kmeans')
    
    def execute_cold_start( self ):
        # Continuar daqui
        pass


    def integrate_expert_feedback(self, expert_feedback):
        # Integrar o feedback do especialista
        # Pode envolver a identificação dos casos mais informativos para o treinamento
        pass

    def train_with_active_learning(self):
        # Aplicar técnicas de Active Learning para treinar/reajustar o meta-modelo
        # com base no feedback do especialista
        pass

    def update_model(self):
        # Atualizar o meta-modelo com os novos dados treinados
        pass

    def validate_model(self):
        # Testar e validar o modelo atualizado
        pass

    def execute_active_learning_shap_characteristic( self, characteristic, classe ):
        import shap
        import numpy as np
        from sklearn.model_selection import train_test_split
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.preprocessing import LabelEncoder

        X = self.meta_model[ self.parameters + ["classificacao"] ]
        X = X[ X["classificacao"].notna() ]

        y = X['classificacao']
        X = X[ self.parameters ]

        encoder = LabelEncoder()
        Y_encoded = encoder.fit_transform(y)

        # Dividir em treino e teste
        X_train, X_test, y_train, y_test = train_test_split(X, Y_encoded, test_size=0.2, random_state=42)

        # Treinar um modelo de floresta aleatória
        model = RandomForestClassifier(random_state=42)
        model.fit(X_train, y_train)

        # Criar o explainer SHAP
        explainer = shap.TreeExplainer(model)

        # Calcular os SHAP values para os dados de teste
        shap_values = explainer.shap_values(X_test)

        # Plotar o dependence plot para a característica 
        shap.dependence_plot(characteristic, shap_values[:, :, classe], X_test, feature_names=self.parameters)

    def replace_df_attributes_names_for_eng( self, df ):
        df = df.rename(
            columns={'dist_costa_normalizado': 'coast_dist',
                     'dentro_apa': 'inside_mpa',
                     'cog_diff_norm': 'cog_diff',
                     'dentro_mt': 'inside_ts',
                     'dentro_zee': 'inside_eez',
                     'sog_diff_norm': 'sog_diff'
                     }
            )
        return df

    def replace_df_attributes_names_for_pt( self, df ):
        df = df.rename(
            columns={'dist_costa_normalizado': 'distancia_costa',
                     'dentro_apa': 'dentro_apa',
                     'cog_diff_norm': 'variacao_cog',
                     'dentro_mt': 'dentro_mt',
                     'dentro_zee': 'dentro_zee',
                     'sog_diff_norm': 'variacao_sog'
                     }
            )
        return df


    def replace_list_attributes_names_for_eng( self, l ):
        columns={'dist_costa_normalizado': 'coast_dist',
                    'dentro_apa': 'inside_mpa',
                    'cog_diff_norm': 'cog_diff',
                    'dentro_mt': 'inside_ts',
                    'dentro_zee': 'inside_eez',
                    'sog_diff_norm': 'sog_diff'
                    }

        for k, it in columns.items():
            for i in range(len(l)):
                if k == l[i]:
                    l[i] = it

        return l

    def replace_list_attributes_names_for_pt( self, l ):
        columns={   'dist_costa_normalizado': 'dist_costa',
                    'dentro_apa': 'dentro_apa',
                    'cog_diff_norm': 'variacao_cog',
                    'dentro_mt': 'dentro_mt',
                    'dentro_zee': 'dentro_zee',
                    'sog_diff_norm': 'variacao_sog',
                    'type_fishing':'tipo_pesca',
                    'ft':'trajetoria_pesca',
                    'mmsi_valid':'mmsi_valido',
                    'type_unknow':'tipo_desconhecido',
                    'time_stopped_h_norm':'tempo_parado',
                    'flag_unknow':'bandeira_desconhecida',
                    'type_other':'tipo_outro',
                    'flag_other':'bandeira_outra',
                    'arriving':'chegada',
                    'in_fpso_area':'dentro_fpso_area',
                    'out_of_anchor_zone':'fora_zn_ancoragem',
                    'type_tanker':'tipo_tanker',
                    'type_tug':'tipo_tug',
                    'type_buoy':'tipo_boia'
                    }

        for k, it in columns.items():
            for i in range(len(l)):
                if k == l[i]:
                    l[i] = it

        return l

    def execute_active_learning_shap_class( self, class_index ):
        import shap
        import numpy as np
        from sklearn.model_selection import train_test_split
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.preprocessing import LabelEncoder

        X = self.meta_model[ self.parameters + ["classificacao"] ]
        X = X[ X["classificacao"].notna() ]

        y = X['classificacao']
        X = X[ self.parameters ]

        X = self.replace_df_attributes_names_for_eng( X )
        p = self.replace_list_attributes_names_for_eng( self.parameters )

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
        shap.summary_plot(shap_values[:,:,class_index], X_test, feature_names=p)


    def execute_active_learning_shap_class_pt( self, class_index ):
        import shap
        import numpy as np
        from sklearn.model_selection import train_test_split
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.preprocessing import LabelEncoder

        X = self.meta_model[ self.parameters + ["classificacao"] ]
        X = X[ X["classificacao"].notna() ]

        y = X['classificacao']
        X = X[ self.parameters ]

        X = self.replace_df_attributes_names_for_pt( X )        
        # p = self.parameters
        # p = X_test.columns.values

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
        p = self.replace_list_attributes_names_for_pt( X_test.columns.values )
        print(p)
        shap.summary_plot(shap_values[:,:,class_index], X_test, feature_names=p)


# Exemplo de uso
# meta_model = # Meta-modelo existente
# impact_assessment = ImpactAssessment(meta_model)
# impact_assessment.integrate_expert_feedback(expert_feedback)
# impact_assessment.train_with_active_learning()
# impact_assessment.update_model()
# impact_assessment.validate_model()

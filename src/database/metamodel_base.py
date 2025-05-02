import sqlite3
import pandas as pd
import geopandas as gpd
import pickle
import movingpandas as mpd
import numpy as np
import geohash as geo
from tqdm import tqdm
import traceback

class MetamodelDB:
    def __init__(self):
        """ Inicializa a conexão com o banco de dados SQLite. """
        # self.conn = sqlite3.connect('metamodel.db')
        self.conn = sqlite3.connect('metamodel.db', timeout=30)

    def to_sql(self, df, table_name, if_exists='fail'):
        """ Insere um DataFrame no banco de dados. """
        df.to_sql(table_name, self.conn, if_exists=if_exists, index=False)

    def read_sql(self, query):
        """ Lê dados do banco de dados e retorna um DataFrame. """
        return pd.read_sql(query, self.conn)

    def close(self):
        """ Fecha a conexão com o banco de dados. """
        self.conn.close()

    def insere_df_metamodelo( self, df, se_existir='replace' ):
        # self.to_sql(self, df, 'metamodelo', if_exists=se_existir )
        df.to_sql('metamodelo', self.conn, if_exists=se_existir, index=False)

    def save_df_metamodelo( self, df ):
        # Conectar ao banco de dados SQLite
        cursor = self.conn.cursor()
        
        # Separar o DataFrame em dois: um para inserção e outro para atualização
        df_insert = df[df['id'].isnull()]
        df_update = df[~df['id'].isnull()]
        
        # Inserção em massa para linhas sem ID
        if not df_insert.empty:
            cols = ", ".join([str(i) for i in df_insert.columns if i != 'id'])
            vals = ", ".join(['?' for _ in df_insert.columns if _ != 'id'])
            sql = f"INSERT INTO metamodelo ({cols}) VALUES ({vals})"
            tuplas = [tupla for tupla in df_insert[ cols.replace(' ', '').split(",") ].itertuples(index=False, name=None) ]
            cursor.executemany( sql, tuplas )
            self.conn.commit()
        
        # Atualização individual para linhas com ID
        for index, row in df_update.iterrows():
            cols = ", ".join([f"{i}=?" for i in df_update.columns if i != 'id'])
            sql = f"UPDATE metamodelo SET {cols} WHERE id = ?"
            cursor.execute(sql, (*row[df_update.columns != 'id'].values, row['id']))
        
        self.conn.commit()


    def cria_tabela_al( self, df ):
        df.to_sql("active_learning_update_data", self.conn, if_exists='replace', index=True)

        # cursor = self.conn.cursor()

        # # Criar uma tabela para armazenar o objeto (se ainda não existir)
        # cursor.execute('''
        #     DELETE FROM active_learning_update_data
        # ''')        
        # self.conn.commit()

    def get_df_tabela_al( self ):
        pass


    def insere_tabela_al( self, df ):
        df.to_sql("active_learning_update_data", self.conn, if_exists='replace', index=True)
        df["classificacao"] = None
        self.conn.commit()

    def cria_tabela_trajetorias( self  ):
        cursor = self.conn.cursor()

        # Criar uma tabela para armazenar o objeto (se ainda não existir)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trajetorias (
                id INTEGER PRIMARY KEY,
                traj_id STRING(30),
                dados BLOB
            )
        ''')        
        self.conn.commit()

    def delete_all_trajs( self ):
        cursor = self.conn.cursor()
        cursor.execute("delete from trajetorias")
        self.conn.commit()
        cursor.close( )


    def insere_trajs( self, trajs ):
        cursor = self.conn.cursor()
        trajs_fk = []
        for traj in trajs.trajectories[:]:
            traj_id = traj.df.iloc[0]["traj_id"]
            # Serializar o objeto com pickle
            objeto_serializado = pickle.dumps(traj)
            # Inserir o objeto serializado na tabela
            cursor.execute('''INSERT INTO trajetorias (traj_id, dados) 
                              VALUES (?, ?)''', (traj_id, objeto_serializado,))
            # Obter o ID da última linha inserida
            id_gerado = cursor.lastrowid
            trajs_fk.append( id_gerado )

        self.conn.commit()            
        return trajs_fk

    def update_trajs( self, trajs ):
        cursor = self.conn.cursor()
        trajs_fk = []
        for traj in tqdm(trajs):
            traj_id = traj.df.iloc[0]["traj_id"]
            # Serializar o objeto com pickle
            objeto_serializado = pickle.dumps(traj)
            # Inserir o objeto serializado na tabela
            cursor.execute('''UPDATE trajetorias 
                                 SET dados = ? 
                             WHERE traj_id = ?
                              ''', (objeto_serializado, traj_id, ))
            # Obter o ID da última linha inserida
            id_gerado = cursor.lastrowid
            trajs_fk.append( id_gerado )

        self.conn.commit()            
        return trajs_fk


    def get_trajectory( self, traj_fk ):
        cursor = self.conn.cursor()

        # Consultar o objeto serializado
        cursor.execute('SELECT dados FROM trajetorias WHERE id = ?', (traj_fk,))
        # rows = cursor.fetchall()
        dados_binarios = cursor.fetchone()[0]

        # Desserializar o objeto
        traj = pickle.loads(dados_binarios)

        return traj

    # def set_classificacao_traj( self, traj_id, classificacao ):
    #     cursor = self.conn.cursor()
    #     cursor.execute('''UPDATE metamodelo SET classificacao = ?
    #                        WHERE  traj_id = ? ''', (classificacao, traj_id,))
    #     self.conn.commit()
    #     cursor.close()

    def get_trajectories_by_mmsi( self, mmsi ):
        cursor = self.conn.cursor()

        str_mmsi = str(mmsi) + "_%"
        # Consultar o objeto serializado
        cursor.execute('SELECT dados FROM trajetorias WHERE traj_id like ?', (str_mmsi,))
        rows = cursor.fetchall()
        
        trajs = [ ]
        
        for r in rows:
            dados_binarios = r[0]
            # Desserializar o objeto
            traj = pickle.loads(dados_binarios)
            trajs.append( traj )

        return trajs
    
    def get_gdf_trajectories_by_mmsi( self, mmsi ):
        trajs = self.get_trajectories_by_mmsi( mmsi )
        if len( trajs ) <= 0:
            return trajs

        gdf_list = []
        for traj in trajs:
            gdf_list.append( traj.df )

        return pd.concat( gdf_list )


    def set_classificacao_traj(self, meta_id, classificacao):
        cursor = self.conn.cursor()
        
        # # Primeiro, encontre o id do último registro para o traj_id especificado
        # cursor.execute('''SELECT id FROM metamodelo
        #                 WHERE traj_id = ?
        #                 ORDER BY id DESC
        #                 LIMIT 1''', (meta_id,))
        # result = cursor.fetchone()
        
        # if result:
            # Se um registro foi encontrado, atualize a classificação para esse id específico
            # last_id = result[0]
        cursor.execute('''UPDATE metamodelo SET classificacao = ?
                        WHERE id = ?''', (classificacao, int(meta_id) ))
        self.conn.commit()
        
        cursor.close()




    def insere_equivalencia_kmeans( self, df_metamodelo, coluna_grupo='cluster_kmeans', coluna_rotulo='classificacao' ):
        if df_metamodelo is None:
            return None
        else:
            df_associacoes_dbscan = self.calcular_equivalencias( df_metamodelo, coluna_grupo='cluster_kmeans', coluna_rotulo='classificacao' )
            df_associacoes_dbscan.fillna(value="atividade_anomala", inplace=True)
            lista_de_tuplas = [tupla for tupla in df_associacoes_dbscan.itertuples(index=False, name=None)]
            print(lista_de_tuplas)
            try:
                cursor = self.conn.cursor()
                cursor.execute("delete from kmeans")
                self.conn.commit()
                cursor.executemany('''
                    INSERT INTO kmeans (cluster, classificacao)
                    VALUES (?, ?)
                ''', lista_de_tuplas)
                self.conn.commit()
            except Exception as e:
                print("Insert error: " + e)
                self.close()

        return df_associacoes_dbscan


    def get_string_kmeans( self, predicao_kmeans ):

        cursor = self.conn.cursor()
        cursor.execute('SELECT classificacao FROM kmeans WHERE cluster = ?', (int(predicao_kmeans),) )
        # print("get string kmeans: ", cursor.fetchone() )
        classificacao = cursor.fetchone()[0]
        cursor.close()

        return classificacao
        

    def calcular_equivalencias(self, df, coluna_grupo='cluster_dbscan', coluna_rotulo='classificacao'):
        """
        Calcula as equivalências entre os rótulos predominantes e os grupos.

        Parâmetros:
        - df (pd.DataFrame): DataFrame contendo os dados.
        - coluna_grupo (str): Nome da coluna no DataFrame que contém os identificadores de grupo.
        - coluna_rotulo (str): Nome da coluna no DataFrame que contém os rótulos.

        Retorna:
        - pd.DataFrame: DataFrame contendo a equivalência entre grupos e rótulos predominantes.
        """
        # Ignorar os pontos de ruído na análise
        df_validos = df[df[coluna_grupo] != -1]
        
        # Obter a moda (rótulo mais frequente) para cada grupo usando uma abordagem que evita erros
        modas = df_validos.groupby(coluna_grupo)[coluna_rotulo].agg(lambda x: x.mode().iloc[0] if not x.mode().empty else pd.NA)
        
        # Criando a lista de equivalências
        equivalencias = modas.reset_index().rename(columns={coluna_rotulo: 'rotulo_predominante'})
        
        return equivalencias

    def insere_equivalencia_dbscan( self, df_metamodelo, coluna_grupo='cluster_dbscan', coluna_rotulo='classificacao' ):
        if df_metamodelo is None:
            return None
        else:
            df_associacoes_dbscan = self.calcular_equivalencias( df_metamodelo )
            df_associacoes_dbscan.fillna(value="atividade_anomala", inplace=True)
            lista_de_tuplas = [tupla for tupla in df_associacoes_dbscan.itertuples(index=False, name=None)]
            # print(lista_de_tuplas)
            try:
                cursor = self.conn.cursor()
                cursor.execute("delete from dbscan")
                self.conn.commit()
                cursor.executemany('''
                    INSERT INTO dbscan (cluster, classificacao)
                    VALUES (?, ?)
                ''', lista_de_tuplas)
                self.conn.commit()
                cursor.close()
            except Exception as e:
                print("Insert error: " + e)
                self.close()

        return df_associacoes_dbscan


    def get_string_dbscan( self, predicao_dbscan ):

        if predicao_dbscan == -1:
            return "atividade_anomala"

        cursor = self.conn.cursor()
        cursor.execute('SELECT classificacao FROM dbscan WHERE cluster = ?', (int(predicao_dbscan),) )
        classificacao = cursor.fetchone()[0]
        cursor.close()

        return classificacao


    def set_classificacao_traj_performance( self, row_metamodelo, classificacao, min_cold_start=100, classificacao_al=None, op=None ):
        print("set_classificacao_traj_performance")
        print(row_metamodelo["id"])
        meta_id = row_metamodelo["id"]
        # update human classification
        self.set_classificacao_traj( meta_id, classificacao )
        n_classifief_rows = self.count_trajs_com_rotulos()
        if n_classifief_rows > min_cold_start:
            if classificacao_al is None:
                al = row_metamodelo["predicao"]
            else:
                al = classificacao_al
            km = self.get_string_kmeans( row_metamodelo["cluster_kmeans"] )
            dbscan = self.get_string_dbscan( row_metamodelo["cluster_dbscan"] )
            human_class = classificacao

            vote_count = np.array([al, km, dbscan])
            print(vote_count)
            # Encontrar as strings únicas e suas contagens
            strings_unicas, contagens = np.unique(vote_count, return_counts=True)
            # Identificar a string com a maior contagem
            indice_max_contagem = np.argmax(contagens)
            string_mais_frequente = strings_unicas[indice_max_contagem]
            if contagens[indice_max_contagem] == 1:
                string_mais_frequente = "empate"

            query = '''
            INSERT INTO classificacao (traj_id, al, dbscan, kmeans, voting, human, user) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(traj_id) DO UPDATE SET
                al = ?,
                dbscan = ?,
                kmeans = ?,
                voting = ?,
                human = ?,
                user=?
                WHERE traj_id = ?;
            '''

            cursor = self.conn.cursor()
            cursor.execute(query, (meta_id, al, dbscan, km, string_mais_frequente, human_class, op, al, dbscan, km, string_mais_frequente, human_class, op, meta_id))
            self.conn.commit()
            cursor.close()


    def get_trajs_sem_rotulos( self ):
        query = '''
        SELECT * 
          FROM metamodelo
         WHERE classificacao IS NULL
        '''
        df = self.read_sql( query )
        return df

    def set_classificacao_al_traj( self, traj_id, classificacao ):
        cursor = self.conn.cursor()
        cursor.execute('''UPDATE active_learning_update_data SET classificacao = ?
                           WHERE  traj_id = ? ''', (classificacao, traj_id,))
        self.conn.commit()
        cursor.close()


    def execute_sql( self, str  ):
        cursor = self.conn.cursor()

        # Criar uma tabela para armazenar o objeto (se ainda não existir)
        cursor.execute(str)        
        self.conn.commit()
        cursor.close()

    def count_trajs_sem_rotulos( self ):
        # Criando um cursor
        cursor = self.conn.cursor()
        query = '''
        SELECT COUNT (*)
          FROM metamodelo
         WHERE classificacao IS NULL
        '''
        cursor.execute(query)
        # Obtendo o resultado
        count = cursor.fetchone()[0]

        return count

    def count_trajs_com_rotulos( self ):
        # Criando um cursor
        cursor = self.conn.cursor()
        query = '''
        SELECT COUNT (*)
          FROM metamodelo
         WHERE classificacao IS NOT NULL
        '''
        cursor.execute(query)
        # Obtendo o resultado
        count = cursor.fetchone()[0]

        return count

    def count_trajs( self ):
        # Criando um cursor
        cursor = self.conn.cursor()
        query = '''
        SELECT COUNT (*)
          FROM metamodelo
        '''
        cursor.execute(query)
        # Obtendo o resultado
        count = cursor.fetchone()[0]

        return count


    def cria_tabela_info_navio( self  ):
        cursor = self.conn.cursor()

        # Criar uma tabela para armazenar o objeto (se ainda não existir)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS info_navio (
                mmsi INTEGER PRIMARY KEY,
                nome_navio STRING(30),
                bandeira STRING(30),
                tipo STRING(30)
            )
        ''')        
        self.conn.commit()

    def insere_info_navio( self, mmsi, nome_navio, bandeira, tipo ):
        cursor = self.conn.cursor()
        # SQL para INSERT OR REPLACE
        sql = '''
        REPLACE INTO info_navio (mmsi, nome_navio, bandeira, tipo) VALUES (?, ?, ?, ?)
        ''' 
        cursor.execute(sql, (mmsi, nome_navio, bandeira, tipo))
        self.conn.commit()

    def get_info_navio( self, mmsi ):
        cursor = self.conn.cursor()

        # Consultar o objeto serializado
        cursor.execute('SELECT nome_navio, bandeira, tipo FROM info_navio WHERE mmsi = ?', (mmsi,))
        # rows = cursor.fetchall()
        # Buscar todos os resultados
        registro = cursor.fetchone()

        if registro:
            nome_navio = registro[0]
            bandeira = registro[1]
            tipo = registro[2]
            return nome_navio, bandeira, tipo
        else:
            return None, None, None
        
    # Função para criar a tabela
    def criar_tabela_historico_transmissoes_ais(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historico_transmissoes_ais (
                id INTEGER PRIMARY KEY,
                mmsi INTEGER,
                geohash TEXT,
                latitude REAL,
                longitude REAL,
                timestamp TEXT
            )
        ''')
        self.conn.commit()        


    def insere_transmissao_ais( self, mmsi, latitude, longitude, ts, precisao_geohash=5):
        geohash = geo.encode(latitude, longitude, precisao_geohash)
        cursor = self.conn.cursor()
        print(mmsi, geohash, latitude, longitude, ts)
        cursor.execute('''
            INSERT INTO historico_transmissoes_ais (mmsi, geohash, latitude, longitude, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', (mmsi, geohash, latitude, longitude, ts))
        self.conn.commit()

    def insere_multiplas_transmissao_ais( self, row_list ):
        self.conn.execute('PRAGMA journal_mode = MEMORY')  # Ou 'OFF' para desativar completamente
        self.conn.execute('PRAGMA synchronous = OFF')  # Cuidado com a integridade dos dados
        cursor = self.conn.cursor()
        # print(mmsi, geohash, latitude, longitude, ts)
        cursor.executemany('''
            INSERT INTO historico_transmissoes_ais (mmsi, geohash, latitude, longitude, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ''', row_list)
        self.conn.commit()


    def atualiza_transmissao_ais( self, id, mmsi, latitude, longitude, timestamp):
        geohash = geo.encode(latitude, longitude)
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE historico_transmissoes_ais
            SET mmsi = ?, geohash = ?, latitude = ?, longitude = ?, timestamp = ?
            WHERE id = ?
        ''', (mmsi, geohash, latitude, longitude, timestamp, id))
        self.conn.commit()    

    def deleta_transmissao( self, id ):
        cursor = self.conn.cursor()
        cursor.execute('''
            DELETE FROM historico_transmissoes_ais WHERE id = ?
        ''', (id,))
        self.conn.commit()

    def busca_historico_transmissao_ais( self, latitude, longitude, precisao_geohash=6):
        # Gerar o geohash da localização fornecida
        geohash = geo.encode(latitude, longitude, precisao_geohash)

        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM historico_transmissoes_ais WHERE geohash LIKE ?
        ''', (geohash + '%',))

        resultados = cursor.fetchall()

        # if resultados:
        #     print("Histórico de transmissão encontrado para a localização fornecida.")
        #     for row in resultados:
        #         print(row)
        # else:
        #     print("Nenhum histórico de transmissão encontrado para a localização fornecida.")
        return resultados
    
    def busca_geohash_historico_transmissao_ais( self, geohash ):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM historico_transmissoes_ais WHERE geohash LIKE ?
        ''', (geohash + '%',))

        resultados = cursor.fetchall()

        return resultados

        
    def get_all_geohash( self ):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT DISTINCT geohash FROM historico_transmissoes_ais
        ''')

        resultados = cursor.fetchall()
        lista_simples = [item[0] for item in resultados]
        return lista_simples


    def insert_encounters( self, df_encounters ):
        # traj_id_1, traj_id_2, h3
        row_list = []
        
        for i in range( len(df_encounters) ):
            traj_ids = df_encounters[i]["traj_id"].unique()
            e = df_encounters[i]
            # traj_fks = df_encounters[i]["traj_fk"].unique()
            traj_fk1 = e[e["traj_id"]==traj_ids[0]]['traj_fk'].iloc[0]
            traj_fk2 = e[e["traj_id"]==traj_ids[1]]['traj_fk'].iloc[0]
            h3 = df_encounters[i]["h3_index"].iloc[0]
            row_list.append( (traj_ids[0], traj_ids[1], h3, int(traj_fk1), int(traj_fk2) ) )

        cursor = self.conn.cursor()
        # cursor.execute("delete from encounters")
        # self.conn.commit()
        print(row_list)
        cursor.executemany('''
            INSERT INTO encounters (traj_id_1, traj_id_2, h3, traj_1_fk, traj_2_fk)
            VALUES (?, ?, ?, ?, ?)
        ''', row_list)
        self.conn.commit()

        return row_list

    def insert_replace_encounters( self, df_encounters ):
        # traj_id_1, traj_id_2, h3
        row_list = []
        
        for i in range( len(df_encounters) ):
            traj_ids = df_encounters[i]["traj_id"].unique()
            traj_fks = df_encounters[i]["traj_fk"].unique()
            h3 = df_encounters[i]["h3_index"].iloc[0]
            row_list.append( (traj_ids[0], traj_ids[1], h3, int(traj_fks[0]), int(traj_fks[1]) ) )

        cursor = self.conn.cursor()
        # cursor.execute("delete from encounters")
        # self.conn.commit()
        print(row_list)
        for r in row_list:
            cursor.execute('''
                REPLACE INTO encounters (traj_id_1, traj_id_2, h3, traj_1_fk, traj_2_fk)
                VALUES (?, ?, ?, ?, ?)
            ''', r)
        self.conn.commit()

        return row_list


    def get_encounters_by_traj_id(self, traj_fk ):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT traj_1_fk, traj_2_fk FROM encounters WHERE (traj_1_fk = ? or traj_2_fk = ?)
        ''', (traj_fk, traj_fk))

        resultados = cursor.fetchall()
        return resultados
    
    def get_classificacao_table( self ):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM classificacao
        ''')

        resultados = cursor.fetchall()
        return resultados
    
    def insere_atualiza_gdf_poly( self, gdf ):
        cursor = self.conn.cursor()
        objeto_serializado = pickle.dumps(gdf)
        cursor.execute('''
            REPLACE INTO anchor_zone (id, gdf_poly)
            VALUES (?, ?)
        ''', (0, objeto_serializado,))
        self.conn.commit()
        cursor.close()

    def get_gdf_poly( self ):
        # Criando um cursor
        cursor = self.conn.cursor()
        query = '''
            SELECT gdf_poly
            FROM anchor_zone
            WHERE id=0
            '''
        cursor.execute(query)
        # Obtendo o resultado
        dados_binarios = cursor.fetchone()[0]

        gdf_poly = pickle.loads(dados_binarios)

        cursor.close()

        return gdf_poly


    def get_meta_model(self):
        # Load metamodelo with human classification updated
        query = "SELECT * FROM metamodelo"
        meta_model = self.read_sql(query)
        return meta_model
    
    # def get_row_by_traj_id( self, traj_id ):
        
    #     query = "SELECT * FROM metamodelo WHERE traj_id = ?"
    #     parameter = (traj_id,)
    #     df = pd.read_sql(query, self.conn, params=parameter)

    #     return df
    
    def get_row_by_traj_id(self, traj_id):
        # Modifica a consulta para ordenar os resultados por id em ordem decrescente e limitar a 1
        query = "SELECT * FROM metamodelo WHERE traj_id = ? ORDER BY id DESC LIMIT 1"
        parameter = (traj_id,)
        df = pd.read_sql(query, self.conn, params=parameter)

        return df

    def get_row_by_id(self, id):
        # Modifica a consulta para ordenar os resultados por id em ordem decrescente e limitar a 1
        query = "SELECT * FROM metamodelo WHERE id = ? ORDER BY id DESC LIMIT 1"
        parameter = (id,)
        df = pd.read_sql(query, self.conn, params=parameter)

        return df

    def get_trajectory_by_metamodel_id( self, meta_id ):
        # Modifica a consulta para ordenar os resultados por id em ordem decrescente e limitar a 1
        query = '''
            SELECT t.dados
            FROM metamodelo m, trajetorias t 
            WHERE m.traj_fk = t.id 
            AND m.id = ?
            '''
        cursor = self.conn.cursor()
        # Consultar o objeto serializado
        cursor.execute(query, (meta_id,))
        # rows = cursor.fetchall()
        dados_binarios = cursor.fetchone()[0]

        # Desserializar o objeto
        traj = pickle.loads(dados_binarios)

        return traj

    def get_trajectories_all( self ):
        # Modifica a consulta para ordenar os resultados por id em ordem decrescente e limitar a 1
        query = '''
            SELECT t.dados
            FROM metamodelo m, trajetorias t 
            WHERE m.traj_fk = t.id 
            '''
        cursor = self.conn.cursor()
        # Consultar o objeto serializado
        cursor.execute(query)
        rows = cursor.fetchall()

        trajs = []
        for r in tqdm( rows ):
            dados_binarios = r[0]
            # Desserializar o objeto
            traj = pickle.loads(dados_binarios)
            trajs.append( traj )

        return mpd.TrajectoryCollection( trajs )

    def get_trajectories_by_al_prediction( self, class_name, with_human_classification=False ):
        # Modifica a consulta para ordenar os resultados por id em ordem decrescente e limitar a 1
        if with_human_classification:
            query = '''
                SELECT t.dados
                FROM metamodelo m, trajetorias t 
                WHERE m.traj_fk = t.id 
                AND m.predicao = ?
                '''
        else:
            query = '''
                SELECT t.dados
                FROM metamodelo m, trajetorias t 
                WHERE m.traj_fk = t.id 
                AND m.predicao = ?
                AND m.classificacao is NULL
                '''
        cursor = self.conn.cursor()
        # Consultar o objeto serializado
        cursor.execute(query, (class_name,))
        rows = cursor.fetchall()

        trajs = []
        for r in tqdm( rows ):
            dados_binarios = r[0]
            # Desserializar o objeto
            traj = pickle.loads(dados_binarios)
            trajs.append( traj )

        return mpd.TrajectoryCollection( trajs )


    def get_trajectories_synthetic( self ):
        # Modifica a consulta para ordenar os resultados por id em ordem decrescente e limitar a 1
        query = '''
            SELECT t.dados
            FROM metamodelo m, trajetorias t 
            WHERE m.traj_fk = t.id
              and synthetic = 1
            '''
        cursor = self.conn.cursor()
        # Consultar o objeto serializado
        cursor.execute(query)
        rows = cursor.fetchall()

        trajs = []
        for r in tqdm( rows ):
            dados_binarios = r[0]
            # Desserializar o objeto
            traj = pickle.loads(dados_binarios)
            trajs.append( traj )

        return mpd.TrajectoryCollection( trajs )



    def update_metamodel_trajectories_synthetic( self ):
        # Criteria for identify a synthetic trajectory, in this case date > 2023

        # Modifica a consulta para ordenar os resultados por id em ordem decrescente e limitar a 1
        query = '''
            SELECT m.*, t.dados
            FROM metamodelo m, trajetorias t 
            WHERE m.traj_fk = t.id 
            '''
        
        df = pd.read_sql(query, self.conn)

        try:        
            synthetic = []
            for r in tqdm( df.itertuples() ):
                dados_binarios = r.dados
                # Desserializar o objeto
                traj = pickle.loads(dados_binarios)
                if traj.df.reset_index().loc[0, 'dh'] > pd.to_datetime('2023-01-01'):
                    synthetic.append( 1 )
                else:
                    synthetic.append( 0 )

            self.update_metamodel_by_field( df.id, synthetic, 'synthetic' )
            return True
        except Exception as e:
            traceback.print_exc()
            return False       


    def update_metamodel_by_field( self, column_id, column_data, column_name ):
        cursor = self.conn.cursor()
        query = f"UPDATE metamodelo SET {column_name} = ? WHERE id = ?"
        print(query)
        for i in range( len(column_id) ):         
            cursor.execute( query, (column_data[i], int(column_id[i]),) )
            # print(cursor.rowcount)
            # print((column_data[i], column_id[i]))
        self.conn.commit()    

        cursor.close( )

    def get_operators_classification_count( self, op, activity_class ):

        query = '''
            SELECT COUNT(*) as n
            FROM classificacao c
            WHERE c.user = ?
              AND c.al = ?
            '''
        
        cursor = self.conn.cursor()
        # Consultar o objeto serializado
        cursor.execute(query,( op,activity_class ))
        n = cursor.fetchone()[0]

        return n




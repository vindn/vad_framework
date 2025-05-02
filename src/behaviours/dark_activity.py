from src.database.metamodel_base import MetamodelDB
import pandas as pd
import geohash as geo
import folium
from shapely.geometry import Point, LineString, Polygon
import geopandas as gpd
import numpy as np
from datetime import timedelta
from shapely.geometry import LineString
from shapely.ops import substring
from tqdm import tqdm
import time
from joblib import Parallel, delayed
import traceback

class DarkActivity( ):
    def __init__( self, gdf ):
        self.gdf = gdf
        self.db = MetamodelDB( )
        self.trajs = None
        self.trajs_gap = None
        self.all_geohash = None

    # Contruir trajetoria unica por mmsi
    def build_trajectories( self ):
        import movingpandas as mpd
        import shapely as shp
        import hvplot.pandas
        import time
        print("Building unique trajectories for Dark Activity detection...")
        # reset index
        gdf = self.gdf.reset_index()
        gdf['dh'] = pd.to_datetime(gdf['dh'], utc=True)
        # gdf['mmsi'] = gdf['mmsi'].astype(str)
        gdf['traj_id'] = gdf['mmsi']

        # create trajectories
        start_time = time.time()

        # collection = mpd.TrajectoryCollection(
        #     gdf, "traj_id", t='dh', min_length=0.001, crs='epsg:4326')
        # collection.add_direction(gdf.rumo)
        # collection.add_speed(gdf.veloc)

        # # set time gap between trajectories for split
        # # collection = mpd.ObservationGapSplitter(
        # #     collection).split(gap=timedelta(minutes=90))
        # # collection = mpd.ObservationGapSplitter(
        # #     collection).split(gap=timedelta(minutes=gap_minutes))
        
        # collection.add_speed(overwrite=True)
        # collection.add_direction(overwrite=True)
        collection = mpd.TrajectoryCollection(
            gdf, "traj_id",  t='dh', min_length=0.001, crs='epsg:4326')
        
        collection.add_speed(overwrite=True, name="speed_nm", units=('nm', 'h'))
        collection.add_direction(overwrite=True, name='direction')
        collection.add_timedelta(overwrite=True, name='time_delta')
        collection.add_angular_difference(overwrite=True, name='ang_diff')
        collection.add_distance(overwrite=True, name="dist_diff", units="km")     
        collection.add_acceleration(overwrite=True, name="acceleration", units=('nm', 'h'))     

        end_time = time.time()
        print("Time creation trajectories: ", (end_time-start_time)/60,  " min")

        self.trajs = collection

        return collection

    # Criar um mapa historico de transmissao de posicao AIS
    # Utilizar o geohash para mapear as posicoes
    # armazenar essas posicoes no banco
    def criar_mapa_historico( self ):
        import datetime
        for index, row in tqdm( self.gdf.reset_index().iterrows() ):
            ts = row.dh.strftime('%Y-%m-%d %H:%M:%S')
            # print("data:", ts)
            self.db.insere_transmissao_ais( row.mmsi, row.lat, row.lon, ts )

    def criar_mapa_historico_multiplo( self ):

        import datetime
        row_list = []
        for index, row in tqdm( self.gdf.reset_index().iterrows() ):
            ts = row.dh.strftime('%Y-%m-%d %H:%M:%S')
            precisao_geohash=5
            geohash = geo.encode(row.lat, row.lon, precisao_geohash)
            row_list.append( (row.mmsi, geohash, row.lat, row.lon, ts) )
        
        self.db.insere_multiplas_transmissao_ais( row_list )



    # Informa se a posicao tem historico de transmissao
    def get_posicao_transmissao( self, lat, lon ):
        hist = self.db.busca_historico_transmissao_ais( self, lat, lon )
        if hist:
            return True
        else:
            return False

    def update_posicao_transmissao( self, lat, lon ):
        pass

    def predict_position(self, trajectory, minutes_ahead, method='linear'):
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

    # Verifica se a trajetoria tem um GAP de transmissao
    def verifica_gap_trajetoria( self, traj ):
        # for index, row in traj.df.iterrows():
            # hist = self.db.busca_historico_transmissao_ais( self, row.lat, row.lon )
        pass


    def verifica_navio_historico_transmissao( self, traj, time, precision_geohash=3 ):
        # gera predicao de posicao com base na trajetoria
        prox_ponto = self.predict_position(traj, time, method='linear')
        # time_delta = timedelta(minutes=time)
        # prox_tempo = traj.df.reset_index()['dh'].iloc[-1] + time_delta
        # data  = {'dh': [prox_tempo], 'lat':[prox_ponto.y], 'lon': [prox_ponto.x], 'rumo':[0.0], 'veloc':[0.0], 'geometry':[prox_ponto], 'mmsi':[gdf_dark.iloc[0].mmsi], 'nome_navio':[gdf_dark.iloc[0].nome_navio]}
        # prox_df = pd.DataFrame(data)
        # prox_df = prox_df.set_index('dh')
        # verifica se o hash esta em uma area de transmissao
        # se tem o hash no db, entao ja transmitiram da posicao
        if self.db.busca_historico_transmissao_ais( prox_ponto.y, prox_ponto.x, precision_geohash ):
            return False
        else:
            return True


    def geohash_to_polygon(seld, geohash):
        """ Decodifica um geohash em um polígono representando a área correspondente. """
        lat, lon, lat_err, lon_err = geo.decode_exactly(geohash)
        corners = [
            (lat - lat_err, lon - lon_err),
            (lat - lat_err, lon + lon_err),
            (lat + lat_err, lon + lon_err),
            (lat + lat_err, lon - lon_err)
        ]
        return corners

    def plot_geohash_on_map( self, gdf_traj, precisao_geohash=3 ):
        location=[gdf_traj.iloc[0].lat, gdf_traj.iloc[0].lon]

        m = self.plot_trajectory( gdf_traj, 'Teste')

        # Criando o mapa
        # m = folium.Map(location=location, zoom_start=12)
        # geohashes = self.db.get_all_geohash( )
        for index, row in gdf_traj.reset_index().iterrows():    
            # teve_transmissao = self.get_posicao_transmissao( row.lat, row.lon )
            geohash = geo.encode(row.lat, row.lon, precisao_geohash)            
            # if teve_transmissao:
            polygon = self.geohash_to_polygon(geohash)
            folium.Polygon(locations=polygon, color='green', fill=True, fill_color='green', fill_opacity=0.1).add_to(m)

        return m

    def plot_gaps_on_map( self, traj, precisao_geohash=3 ):
               
        all_geohashes = self.get_geohashes_from_linestring(traj.to_linestring(), precisao_geohash )

        gdf_traj = traj.df
        location=[gdf_traj.iloc[0].lat, gdf_traj.iloc[0].lon]

        m = self.plot_trajectory( gdf_traj, 'Teste')

        # Criando o mapa
        # m = folium.Map(location=location, zoom_start=12)
        # geohashes = self.db.get_all_geohash( )
        traj_geohash = []
        for index, row in gdf_traj.reset_index().iterrows():    
            # teve_transmissao = self.get_posicao_transmissao( row.lat, row.lon )
            geohash = geo.encode(row.lat, row.lon, precisao_geohash)            
            traj_geohash.append( geohash )
            # if teve_transmissao:
            polygon = self.geohash_to_polygon(geohash)
            # folium.Polygon(locations=polygon, color='green', fill=True, fill_color='green', fill_opacity=0.1).add_to(m)
            folium.Polygon(locations=polygon, color='green', fill=False).add_to(m)

        for geoh in all_geohashes:
            if geoh not in traj_geohash:
                polygon = self.geohash_to_polygon(geoh)
                # folium.Polygon(locations=polygon, color='red', fill=True, fill_color='red', fill_opacity=0.1).add_to(m)
                folium.Polygon(locations=polygon, color='red', fill=False).add_to(m)

        return m



    # plot gdf points
    def plot_gdf( self, gdf, vessel_description ):
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


    def create_linestring(self, group):        
        # Ordenar por timestamp
        group = group.sort_values(by='dh')      
        # Se há mais de um ponto no grupo, crie uma LineString, caso contrário, retorne None
        return LineString(group.geometry.tolist()) if len(group) > 1 else None


    # plot trajectories from points
    def plot_trajectory( self, gdf, vessel_description ):
        import folium

        lines = gdf.groupby('mmsi').apply(self.create_linestring)

        # Remove possíveis None (se algum grupo tiver apenas um ponto)
        lines = lines.dropna()

        # Crie um novo GeoDataFrame com as LineStrings
        lines_gdf = gpd.GeoDataFrame(lines, columns=['geometry'], geometry='geometry')

        lines_gdf.reset_index(inplace=True)

        # start_point = Point(lines_gdf.iloc[0].geometry.coords[0])
        # m = folium.Map(location=[start_point.y, start_point.x], zoom_start=10)

        m = self.plot_gdf( gdf, vessel_description )

        for _, row in lines_gdf.iterrows():            
            if row['geometry'].geom_type == 'LineString':
                popup_content = f"{row['mmsi']}"
                coords = list(row['geometry'].coords)
                    
                folium.PolyLine(locations=[(lat, lon) for lon, lat in coords], 
                            popup=popup_content,
                            weight=0.5
                ).add_to(m)

        return m


    def get_geohashes_from_linestring(self, linestring, precision=3):
        """
        Retorna uma lista de geohashes únicos por onde passa a linestring.
        
        :param linestring: Objeto LineString do Shapely.
        :param precision: Precisão do geohash (número de caracteres). Valores mais altos geram geohashes mais precisos.
        :return: Lista de geohashes únicos.
        """
        length = linestring.length
        current_distance = 0
        step_size = 0.5  # Define o tamanho do passo em graus. Ajuste conforme necessário.
        geohashes = set()

        while current_distance < length:
            # Extrai um ponto ao longo da linestring a cada passo
            point = substring(linestring, current_distance, current_distance).coords[0]
            # Calcula o geohash para o ponto atual
            hash = geo.encode(point[1], point[0], precision=precision)
            geohashes.add(hash)
            current_distance += step_size

        return list(geohashes)


    def is_gap_on_trajectory( self, traj, precisao_geohash=3 ):
               
        all_geohashes = self.get_geohashes_from_linestring(traj.to_linestring(), precisao_geohash )

        gdf_traj = traj.df
        traj_geohash = []
        # get all geohashes from trajectory points
        for index, row in gdf_traj.reset_index().iterrows():    
            # teve_transmissao = self.get_posicao_transmissao( row.lat, row.lon )
            geohash = geo.encode(row.lat, row.lon, precisao_geohash)            
            traj_geohash.append( geohash )

        has_gap = False
        for geoh in all_geohashes:
            # se existe geohash que não tem ponto, é um gap
            if geoh not in traj_geohash:
                # Verificar se a substring está em algum elemento da lista
                # founded = any(geoh in s for s in self.all_geohash)
                founded = self.is_geohash_gap_transmission( geoh )
                # testa se ja houve transmissao nesse geohash
                if founded:
                    # print("gap on geohash: " + geoh)
                    has_gap = True
                    break

        return has_gap
    
    def update_gap_on_trajectories( self, trajs_spllited, precisao_geohash=3 ):
        
        self.all_geohash = self.db.get_all_geohash( )
        self.trajs_gap = []
        try:
            print("Update gap on trajectories...")
            for traj in tqdm( trajs_spllited ):
                mmsi = traj.df.mmsi.iloc[0]
                traj_ship = self.trajs.filter('mmsi', [mmsi]).trajectories[0]
                is_gap = self.is_gap_on_trajectory( traj_ship, precisao_geohash )
                self.trajs_gap.append( is_gap )
        except TypeError:
            print("Trajs array is None!!")
            traceback.print_exc()
        except Exception as e:
            print("Error on update_gap_on_trajectories: " )
            print("mmsi = " + str(mmsi) )
            print(e)
            print(traj.df)
            traceback.print_exc()


        return self.trajs_gap  
    

    def update_gap_on_trajectories_paralell(self, trajs, precisao_geohash=3):
        self.trajs_gap = []
        self.all_geohash = self.db.get_all_geohash( )
        all_geohash = self.all_geohash
        
        def get_geohashes_from_linestring(linestring, precision=3):
            """
            Retorna uma lista de geohashes únicos por onde passa a linestring.
            
            :param linestring: Objeto LineString do Shapely.
            :param precision: Precisão do geohash (número de caracteres). Valores mais altos geram geohashes mais precisos.
            :return: Lista de geohashes únicos.
            """
            length = linestring.length
            current_distance = 0
            # step_size = 0.0001  # Define o tamanho do passo em graus. Ajuste conforme necessário.
            step_size = 0.5  # Aproximadamente 55km
            geohashes = set()

            while current_distance < length:
                # Extrai um ponto ao longo da linestring a cada passo
                point = substring(linestring, current_distance, current_distance).coords[0]
                # Calcula o geohash para o ponto atual
                hash = geo.encode(point[1], point[0], precision=precision)
                geohashes.add(hash)
                current_distance += step_size

            return list(geohashes)

        def is_gap_on_trajectory( traj, all_geohash, precisao_geohash=3 ):
                
            all_geohashes = get_geohashes_from_linestring(traj.to_linestring(), precisao_geohash )

            gdf_traj = traj.df
            traj_geohash = []
            for index, row in gdf_traj.reset_index().iterrows():    
                # teve_transmissao = self.get_posicao_transmissao( row.lat, row.lon )
                geohash = geo.encode(row.lat, row.lon, precisao_geohash)            
                traj_geohash.append( geohash )

            has_gap = False
            for geoh in all_geohashes:
                # se existe geohash que não tem ponto é um gap
                if geoh not in traj_geohash:
                    # Verificar se a substring está em algum elemento da lista
                    founded = any(geoh in s for s in all_geohash)
                    # testa se ja houve transmissao nesse geohash
                    if founded:
                        has_gap = True
                        break

            return has_gap

        # Função auxiliar para processar cada trajetória em paralelo
        def process_traj(traj, trajs_unique):
            try:
                mmsi = traj.df.mmsi.iloc[0]
                mmsi = mmsi.split("_")[0]
                traj_ship = trajs_unique.filter('mmsi', [mmsi]).trajectories[0]
                is_gap = is_gap_on_trajectory(traj_ship, all_geohash, precisao_geohash)
                return is_gap
            except Exception as e:
                print("Erro ao processar trajetória:", e)
                print("MMSI: " + mmsi)
                return None  # Ou maneje o erro conforme necessário

        # Executa o processamento em paralelo e preserva a ordem dos resultados
        # Utiliza tqdm para mostrar o progresso
        # self.trajs_gap = Parallel(n_jobs=-1)(delayed(process_traj)(traj, self.trajs) for traj in tqdm(trajs, total=len(trajs)))
        self.trajs_gap = Parallel(n_jobs=-1)(delayed(process_traj)(traj, self.trajs) for traj in tqdm(trajs))

        # Aqui, não é necessário filtrar os resultados por None, a menos que process_traj possa retornar None como um resultado válido em caso de erro
        return self.trajs_gap

    
    def get_gap_on_trajectories( self ):
        return self.trajs_gap
    
    def is_geohash_gap_transmission( self, geohash ):
        hist = self.db.busca_geohash_historico_transmissao_ais( geohash )

        # test if exists geohash in database
        if hist:
            return True
        else:
            return False


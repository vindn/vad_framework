import numpy as np
import pandas as pd
import movingpandas as mpd
from datetime import datetime, timedelta
import h3
from src.rules.distancia_costa import CalcDistanciaCosta
from geopy.distance import great_circle
from shapely.geometry import MultiPoint
from shapely.geometry import Point
from shapely.geometry import LineString
import time
import geopandas as gpd
import folium
from folium.plugins import MeasureControl

class Encounter:        

    def __init__( self, trajs ):
        self.trajs = trajs
        self.df_combined = None
        self.df_clusters = None

    # def detect_encouters( self, last_hours=None ):
        
    #     df_traj = pd.DataFrame(columns=['traj_id', 'h3_index', 'dh', 'lat', 'lon', 'rumo', 'veloc'])
    #     for i in range( len(self.trajs) ):
    #         traj = self.trajs.trajectories[i]
    #         traj_id = str(traj.to_traj_gdf()["traj_id"]).split()[1]
    #         traj.df["traj_id"] = traj_id
    #         traj.df["h3_index"].iloc[0]
    #         for j in range( len( traj.df )):                
    #             nova_linha = pd.DataFrame({
    #                 'traj_id': [traj.df["traj_id"].iloc[j]], 
    #                 'h3_index': [traj.df["h3_index"].iloc[j]], 
    #                 'dh': [traj.df.reset_index().dh.iloc[j]], 
    #                 'lat': [traj.df["lat"].iloc[j]], 
    #                 'lon': [traj.df["lon"].iloc[j]], 
    #                 'rumo': [traj.df["rumo"].iloc[j]], 
    #                 'veloc': [traj.df["veloc"].iloc[j]]
    #             })
    #             # Concatenando o novo DataFrame com o DataFrame existente
    #             df_traj = pd.concat([df_traj, nova_linha], ignore_index=True)        
        
    #     # Agrupar por 'h3_index' e filtrar grupos com mais de 1 unidade
    #     df_traj['h3_index'] = df_traj['h3_index'].astype(str)
    #     self.df_encouters = df_traj
    #     df_filtrado = df_traj.groupby(['traj_id','h3_index']).filter(lambda x: len(x) > 1)      

    #     if last_hours != None:
    #         # Definir o tempo atual (ou um tempo específico se necessário)
    #         tempo_atual = datetime.now()

    #         # Calcular o tempo limite (atual menos 4 horas)
    #         limite_tempo = tempo_atual - timedelta(hours=last_hours)

    #         # Filtrar os registros das últimas 4 horas
    #         df_filtrado = df_filtrado[df_filtrado['dh'] >= limite_tempo]

    #     return df_filtrado
    
    def detect_encouters( self, last_hours=None ):
        self.combine_trajs_gdf( self.trajs )
        self.df_clusters = self.detect_encounters_h3( self.df_combined, time_interval_m=240, min_distance_from_coast=10, min_distance_between_ships_km=10 )
        return self.df_clusters
    
    def get_df_clusters( self ):
        return self.df_clusters
    
    def get_encounters_on_trajs( self ):
        if len( self.df_clusters ) < 1:
            return None
        df_concat_clusters = pd.concat(self.df_clusters)
        traj_ids_on_encounters = df_concat_clusters['traj_fk'].unique()
        traj_encounters = []
        for i in range( len(self.trajs) ):
            traj = self.trajs.trajectories[i]
            traj_fk = traj.df['traj_fk'].iloc[0]
            if traj_fk in traj_ids_on_encounters:
                traj_encounters.append( 1 )
            else:
                traj_encounters.append( 0 )

        return traj_encounters




    # def combine_trajs_gdf( self, trajs ):
    #     dc = CalcDistanciaCosta()
    #     df_traj = pd.DataFrame(columns=['traj_id', 'mmsi', 'h3_index', 'dh', 'lat', 'lon', 'rumo', 'veloc', 'distance_to_coast'])
    #     for i in range( len(self.trajs) ):
    #         traj = self.trajs.trajectories[i]
    #         # traj_id = str(traj.to_traj_gdf()["traj_id"]).split()[1]
    #         traj_id = traj['traj_id'].iloc[0]
    #         # traj.df["traj_id"] = traj_id
    #         traj.df["h3_index"].iloc[0]
    #         for j in range( len( traj.df )):                
    #             nova_linha = pd.DataFrame({
    #                 'traj_id': [traj.df["traj_id"].iloc[j]], 
    #                 'mmsi': [traj.df["mmsi"].iloc[j]], 
    #                 'h3_index': [traj.df["h3_index"].iloc[j]], 
    #                 'dh': [traj.df.reset_index().dh.iloc[j]], 
    #                 'lat': [traj.df["lat"].iloc[j]], 
    #                 'lon': [traj.df["lon"].iloc[j]], 
    #                 'rumo': [traj.df["rumo"].iloc[j]], 
    #                 'veloc': [traj.df["veloc"].iloc[j]],
    #                 'distance_to_coast':[ dc.distancia_costa_brasil(traj.df["lon"].iloc[j], traj.df["lat"].iloc[j]) ]
    #             })
    #             # Concatenando o novo DataFrame com o DataFrame existente
    #             df_traj = pd.concat([df_traj, nova_linha], ignore_index=True)        
        
    #     # Agrupar por 'h3_index' e filtrar grupos com mais de 1 unidade
    #     df_traj['h3_index'] = df_traj['h3_index'].astype(str)
    #     self.df_combined = df_traj
    #     return df_traj
    def combine_trajs_gdf( self, trajs ):
        self.df_combined = pd.concat( [ traj.df for traj in trajs.trajectories ] )
        return self.df_combined

    
    def get_trajectories_by_h3( self, h3 ):
        return self.df_encouters[ self.df_encouters['h3_index'] == h3 ]['traj_id']
    
    def get_h3_clusters( self, gdf, min_distance_from_coast=10 ):

        # get clusters indexes with only two different MMSIs in cluster
        couting = gdf.groupby('h3_index')['mmsi'].nunique()
        indexes = couting.where(couting == 2).dropna().index

        encounters = []
        for i in indexes:
            # get cluster by index
            g_cluster = gdf[ gdf["h3_index"] == i ]
            encounters.append( g_cluster[:2] )

        return encounters

    def detect_encounters_h3( self, gdf, time_interval_m=240, min_distance_from_coast=10, min_distance_between_ships_km=10 ):
        import datetime
        import traceback
        # Defina o intervalo de tempo
        time_h = 4
        time_m = 60

        # gdf.dh = pd.to_datetime(gdf.dh)
        min_time = gdf.reset_index().dh.min()
        max_time = gdf.reset_index().dh.max()
        start_time = min_time
        end_time = min_time + datetime.timedelta(minutes=time_interval_m)
        if end_time > max_time:
            end_time = max_time
        encounters = []

        while start_time < max_time:       
            # gdf_filtered = gdf[(gdf.index >= start_time) & (gdf.index <= end_time)]
            gdf_filtered = gdf[(gdf.index >= start_time) & (gdf.index <= end_time) & (gdf.veloc <= 2.0 ) ]
            # print('gdf size: ', str(len( gdf_filtered )) )
            try:
                # print( "start_time=", start_time, " end_time=", end_time )
                # do filter points longer than 10km from coast
                gdf_filtered = gdf_filtered[ gdf_filtered[ "distance_to_coast" ] > min_distance_from_coast ]
                # print('gdf size filtered coast: ', str(len( gdf_filtered )) )
                # cluster points
                # print("Clustering points...")
                tmp_encounters = self.get_h3_clusters( gdf_filtered )
                encounters += tmp_encounters
            except Exception as e: 
                print("Error! Size cluster: ", len( gdf_filtered ) )
                traceback.print_exc()

            start_time += datetime.timedelta(minutes=time_interval_m)
            end_time += datetime.timedelta(minutes=time_interval_m)
            if end_time > max_time:
                end_time = max_time

        return encounters    

    # plot gdf points
    def plot_gdf( self, gdf, vessel_description, m=None, color='blue' ):
        import folium

        latitude_initial = gdf.iloc[0]['lat']
        longitude_initial = gdf.iloc[0]['lon']

        if not m:
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
                color=color,  # Define a cor do ponto
                fill=True,
                fill_opacity=1,
            ).add_to(m)            

        return m


    def create_linestring(self, group):        
        # Ordenar por timestamp
        group = group.sort_values(by='dh')      
        # Se há mais de um ponto no grupo, crie uma LineString, caso contrário, retorne None
        return LineString(group.geometry.tolist()) if len(group) > 1 else None


    # plot trajectories from points
    def plot_trajectory( self, gdf, vessel_description, m=None, color='blue' ):
        import folium

        lines = gdf.groupby('mmsi').apply(self.create_linestring)

        # Remove possíveis None (se algum grupo tiver apenas um ponto)
        lines = lines.dropna()

        # Crie um novo GeoDataFrame com as LineStrings
        lines_gdf = gpd.GeoDataFrame(lines, columns=['geometry'], geometry='geometry')

        lines_gdf.reset_index(inplace=True)

        # start_point = Point(lines_gdf.iloc[0].geometry.coords[0])
        # m = folium.Map(location=[start_point.y, start_point.x], zoom_start=10)

        if not m:
            m = self.plot_gdf( gdf, vessel_description, color=color )
        else:
            self.plot_gdf( gdf, vessel_description, m, color=color )

        for _, row in lines_gdf.iterrows():            
            if row['geometry'].geom_type == 'LineString':
                popup_content = f"{row['mmsi']}"
                coords = list(row['geometry'].coords)
                    
                folium.PolyLine(locations=[(lat, lon) for lon, lat in coords], 
                            popup=popup_content,
                            weight=0.5,
                            color=color
                ).add_to(m)

        return m


    def plot_encounter( self, gdf1, gdf2, m=None ):
        if m is None:
            m = self.plot_trajectory( gdf1, "vessel 1", m=None, color='green' )
            m = self.plot_trajectory( gdf2, "vessel 2", m, color='red' )
        else:
            m = self.plot_trajectory( gdf1, "vessel 1", m=m, color='green' )
            m = self.plot_trajectory( gdf2, "vessel 2", m, color='red' )

        m.add_child(MeasureControl())

        return m
    
    def get_df_combined( self ):
        return self.df_combined
    
    def get_encounter_by_mmsi(self, mmsi ):
        mmsi_encounters = []
        for i in range(len(self.df_clusters)):
            if mmsi in self.df_clusters[i]['mmsi']:
                mmsi_encounters.append(  self.df_clusters[i] )

        return mmsi_encounters
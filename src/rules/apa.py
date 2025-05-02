import geopandas as gpd
from geopy.distance import geodesic
from shapely.geometry import Point
from shapely.ops import nearest_points
import pickle
import movingpandas as mpd
import numpy as np
import pandas as pd
from tqdm import tqdm
import folium
from folium.plugins import MeasureControl
from geopy.distance import great_circle
from shapely.geometry import MultiPoint
from shapely.geometry import Point
from shapely.geometry import LineString


class APA:
    def __init__( self ):
        # Caminho para o arquivo GeoPackage
        self.brazil_shp = 'data/apa/shp/WDPA_WDOECM_Jan2024_Public_BRA_shp-polygons.shp'
        # Carregar a camada específica do GeoPackage
        self.gdf_brazil = gpd.read_file(self.brazil_shp)
    
    def show_apa_brazil( self ):
        return self.gdf_brazil.plot()
    
    def get_gdf( self ):
        return self.gdf_brazil
    
    def verifica_trajetoria_dentro_apa( self, traj ):
        traj_geom = traj.to_linestring()
        # Verificar se a linha cruza algum polígono no GeoDataFrame
        cruza = self.gdf_brazil['geometry'].intersects(traj_geom)
        return cruza.any()

    def verifica_trajetoria_dentro_apa_binario( self, traj ):
        traj_geom = traj.to_linestring()
        # Verificar se a linha cruza algum polígono no GeoDataFrame
        cruza = self.gdf_brazil['geometry'].intersects(traj_geom)
        if cruza.any() == False:
            return 0
        else:
            return 1

    def verifica_trajetorias_dentro_apa_binario( self, trajs ):
        dentro = []
        d = 0
        print("Verifying trajectories inside MPAs...")
        for traj in tqdm(trajs.trajectories[:]) :
            d = self.verifica_trajetoria_dentro_apa_binario( traj )
            dentro.append( d )

        #return np.array( dentro, dtype=int )
        return dentro

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


    def draw_polygons_on_map(self, gdf, mapa=None, cor='blue', opacidade=0.5 ):
        """
        Desenha polígonos de um GeoDataFrame em um mapa Folium.

        :param gdf: GeoDataFrame contendo as geometrias dos polígonos.
        :param mapa: Objeto Folium Map existente. Se None, um novo mapa será criado.
        :param cor: Cor dos polígonos.
        :param opacidade: Opacidade dos polígonos.
        :return: Objeto Folium Map com os polígonos desenhados.
        """

        # gdf = self.gdf_brazil

        # Se nenhum mapa for fornecido, criar um novo
        if mapa is None:
            # Calcular o centro do primeiro polígono para centralizar o mapa
            centro = gdf.geometry.iloc[0].centroid.coords[0][::-1]
            mapa = folium.Map(location=centro, zoom_start=12)

        # Iterar sobre as geometrias no GeoDataFrame
        for _, row in gdf.iterrows():
            # Simplificar a geometria para melhorar a performance
            geometria_simplificada = row['geometry'].simplify(tolerance=0.001)
            # Adicionar a geometria ao mapa
            folium.GeoJson(geometria_simplificada, 
                        style_function=lambda x: {'fillColor': cor, 'color': cor, 'weight': 2, 'fillOpacity': opacidade}
                        ).add_to(mapa)

        return mapa
    
    def plot_apa( self, gdf_traj ):

        # Realizando um 'spatial join' para pegar apenas os polígonos de gdf1 que têm interseção com gdf2
        gdf1_with_intersection = gpd.sjoin(self.gdf_brazil, gdf_traj, how='inner', predicate='intersects')
        # Remover possíveis duplicatas, se necessário
        gdf1_with_intersection = gdf1_with_intersection.drop_duplicates()
        print("intersecao:\n" + str(gdf1_with_intersection) )

        # Verificando se o resultado está vazio (ou seja, não houve interseção)
        if gdf1_with_intersection.empty:
            print("Não houve interseção entre os dois GeoDataFrames.")
            m_area = self.draw_polygons_on_map( self.gdf_brazil, opacidade=0.2 )
        else:
            m_area = self.draw_polygons_on_map( gdf1_with_intersection, opacidade=0.2 )

        if m_area is None:
            m = self.plot_trajectory( gdf_traj, "vessel 1", m=None, color='red' )
        else:
            m = self.plot_trajectory( gdf_traj, "vessel 1", m=m_area, color='red' )

        m.add_child(MeasureControl())

        return m


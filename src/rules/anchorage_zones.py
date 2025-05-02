# AFAZER: criar "mapa de calor" com zonas de navios parados; 
# desta forma saberemos os locais comuns de fundeio.
# Um navio fundeando fora dessas areas pode ser anomalo
from sklearn.cluster import KMeans
from sklearn.cluster import DBSCAN
import pandas as pd
from sklearn.preprocessing import StandardScaler
from src.database.metamodel_base import MetamodelDB
from shapely.geometry import MultiPoint
from geopandas.tools import sjoin
import geopandas as gpd
import h3
import folium

class AnchorageZone( ):
    def __init__(self, gdf ):
        self.gdf = gdf
        self.gdf_stopped = None
        self.gdf_poly = None
        self.db = MetamodelDB( )

    def get_all_anchored_ships( self ):
        return self.gdf[ self.gdf["veloc"] < 1 ]

    def cluster_points( self, gdf ):
        # Normalizando os dados

        # scaler = StandardScaler()
        # df_scaled = scaler.fit_transform(self.gdf[['lat', 'lon']])
        df_scaled = self.gdf[['lat', 'lon']]

        # Aplicando K-Means
        # kmeans = KMeans(n_clusters=3)  # Escolha o número de clusters
        # clusters = kmeans.fit_predict(df_scaled)

        # Aplicando dbscan
        # dbscan = DBSCAN(eps=0.5, min_samples=3)  # Ajuste esses valores conforme necessário
        # clusters = dbscan.fit_predict(df_scaled)
        # Definir eps como aproximadamente 1/60 de grau
        eps = 0.1 / 60  # Aproximadamente 1 milha náutica
        dbscan = DBSCAN(eps=eps, min_samples=10).fit(df_scaled)  # Ajuste os parâmetros eps e min_samples conforme necessário
        gdf['cluster'] = dbscan.labels_        

        # Adicionando a coluna de clusters ao DataFrame original
        # self.gdf['cluster_dbscan'] = clusters.labels_

        return self.gdf['cluster_dbscan']


    # Resolução	    Raio (km)
    # 0	    1279.0
    # 1	    483.4
    # 2	    183.0
    # 3	    69.09
    # 4	    26.10
    # 5	    9.87
    # 6	    3.73
    # 7	    1.41
    # 8	    0.53
    # 9 	0.20
    # 10	0.076
    # 11	0.0287
    # 12	0.0109
    # 13	0.00411
    # 14	0.00155
    # 15	0.000587
    # Converta os pontos do gdf para índices H3
    def cluster_points_h3( self, gdf , resolution = 6):        
        gdf['cluster_anchor_h3'] = gdf.apply(lambda row: h3.geo_to_h3(row['geometry'].y, row['geometry'].x, resolution), axis=1)
        return gdf

    def apply_convex_hull( self, gdf ):
        # 1. Filtrar por grupos que possuem ao menos 3 navios no grupo, agrupar por h3_cluster e pelo intervalo de tempo
        # Certifique-se de que a coluna de tempo está no formato de data e hora
        # Criar uma coluna de intervalo de tempo de 4 horas
        # gdf['interval_time_4h'] = gdf.index.floor('4H')
        gdf['interval_time_4h'] = gdf.reset_index()['dh'].dt.floor('4H')
        # Agrupar por 'cluster_anchor_h3' e contar os 'mmsi' únicos em cada grupo
        contagem_mmsi = gdf.groupby(['cluster_anchor_h3', 'interval_time_4h'])['mmsi'].nunique()
        # Filtrar grupos com mais de 3 'mmsi' únicos
        contagem_mmsi_filtrada = contagem_mmsi[contagem_mmsi > 3]
        # Extrair os índices para um array NumPy
        # cluster_anchor_h3_filtrados = contagem_mmsi_filtrada.index.to_numpy()
        contagem_mmsi_filtrada = contagem_mmsi_filtrada.reset_index( ).cluster_anchor_h3.unique()

        # 2. Criar Polígonos dos Clusters
        polys = []
        # for cluster_id in set(gdf['cluster_anchor_h3']):
        for cluster_id in contagem_mmsi_filtrada:
            points = gdf[gdf['cluster_anchor_h3'] == cluster_id]['geometry']
            poly = MultiPoint(list(points)).convex_hull
            polys.append(poly)

        # Criando um novo GeoDataFrame para os polígonos
        self.gdf_poly = gpd.GeoDataFrame(geometry=polys)
        
        return polys

    def build_anchorage_zones( self, resolution=6 ):
        print("Building Anchorage Zones ...")
        self.gdf_stopped = self.get_all_anchored_ships( )
        self.cluster_points_h3( self.gdf_stopped, resolution=resolution )
        self.apply_convex_hull( self.gdf_stopped )
        self.db.insere_atualiza_gdf_poly( self.gdf_poly )

    def verify_ship_on_anchorage_zones( self, newships ):
        self.gdf_poly = self.db.get_gdf_poly( )
        pointInPolys = sjoin(newships, self.gdf_poly, how='inner', op='within')
        return pointInPolys

    def get_gdf_anchorage_zones( self ):
        self.gdf_poly =  self.db.get_gdf_poly( )
        return self.gdf_poly

    def draw_polygons_on_map(self, mapa=None, cor='blue', opacidade=0.5):
        """
        Desenha polígonos de um GeoDataFrame em um mapa Folium.

        :param gdf: GeoDataFrame contendo as geometrias dos polígonos.
        :param mapa: Objeto Folium Map existente. Se None, um novo mapa será criado.
        :param cor: Cor dos polígonos.
        :param opacidade: Opacidade dos polígonos.
        :return: Objeto Folium Map com os polígonos desenhados.
        """

        gdf = self.gdf_poly

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
    
    def draw_ship_on_anchor_zones( self, gdf, cor='red', opacidade=0.5 ):
        m = self.draw_polygons_on_map( )

        # Iterar sobre as geometrias no GeoDataFrame
        for _, row in gdf.iterrows():
            # Simplificar a geometria para melhorar a performance
            geometria_simplificada = row['geometry'].simplify(tolerance=0.001)
            # Adicionar a geometria ao mapa
            folium.GeoJson(geometria_simplificada, 
                        style_function=lambda x: {'fillColor': cor, 'color': cor, 'weight': 2, 'fillOpacity': opacidade}
                        ).add_to(m)
            
        return m

    def get_trajs_out_achorage_zones( self, trajs ):
        traj_anchor = []
        for traj in trajs.trajectories:
            series_on_zone = self.verify_ship_on_anchorage_zones( traj.df )
            if len(series_on_zone) > 0:
                # Ship inside achorage zone
                traj_anchor.append( 0 )
            else:
                # Ship outside achorage zone
                traj_anchor.append( 1 )

        return traj_anchor

import geopandas as gpd
from geopy.distance import geodesic
from shapely.geometry import Point
from shapely.ops import nearest_points
import numpy as np
from tqdm import tqdm
import pandas as pd
from tqdm.auto import tqdm
tqdm.pandas(desc="Progress")

class CalcDistanciaCosta:
    def __init__( self ):
        # Caminho para o arquivo GeoPackage
        self.brazil_gpkg = 'data/gadm41_BRA.gpkg'
        self.eez_shp = 'data/zee/EEZ_land_union_v3_202003/EEZ_Land_v3_202030.shp'
        # Carregar a camada específica do GeoPackage
        self.gdf_brazil = gpd.read_file(self.brazil_gpkg)
        self.gdf_eez_brazil = gpd.read_file(self.eez_shp)
        self.gdf_eez_brazil = self.gdf_eez_brazil[ self.gdf_eez_brazil["UNION"] == "Brazil" ]

    def show_map_brazil( self ):
        return self.gdf_brazil.plot()
    
    def show_eez_map_brazil( self ):
        return self.gdf_eez_brazil.plot()
    
    # Função para calcular a distância geodésica em milhas náuticas
    def calcular_distancia_geodesica(self, ponto1, ponto2):
        return geodesic(ponto1, ponto2).nautical

    def distancia_costa_brasil( self, lon, lat ):
        # Extrair pontos da linha costeira do Brasil
        # pontos_costa = self.gdf_brazil.geometry[0].boundary

        # Encontrar o ponto mais próximo na linha costeira do MULTIPOLYGON
        ponto_proximo = nearest_points( Point(lon, lat), self.gdf_brazil.geometry[0])[1]

        # Calcular a distância mínima
        # Calcular a distância geodésica em milhas e converter para milhas náuticas
        distancia_milhas = geodesic((lat, lon), (ponto_proximo.y, ponto_proximo.x)).miles
        distancia_nautica = distancia_milhas * 0.868976
        
        return distancia_nautica
    
    def distancia_costa_brasil_array( self, trajs ):
        distances = []
        print("Calc distances between trajectories to coast ...")
        for traj in tqdm(trajs.trajectories[:]):
            d1 = self.distancia_costa_brasil( traj.df.iloc[0]["lon"], traj.df.iloc[0]["lat"] )
            d2 = self.distancia_costa_brasil( traj.df.iloc[-1]["lon"], traj.df.iloc[-1]["lat"] )
            # media entre a maior distancia e a menor distancia
            distances.append( (d1+d2)/2 )

        return np.array( distances )

    def detect_arriving( self, trajs ):
        arriving = []
        print("Calc distances between trajectories to coast ...")
        for traj in tqdm(trajs.trajectories[:]):
            d1 = self.distancia_costa_brasil( traj.df.iloc[0]["lon"], traj.df.iloc[0]["lat"] )
            d2 = self.distancia_costa_brasil( traj.df.iloc[-1]["lon"], traj.df.iloc[-1]["lat"] )
            
            diff = d1 - d2
            dist = self.calcular_distancia_geodesica( (traj.df.iloc[0]["lat"], traj.df.iloc[0]["lon"]), ( traj.df.iloc[-1]["lat"], traj.df.iloc[-1]["lon"]) )
            if dist == 0:
                arriving.append( 0 )
            else:
                arriving.append( diff / dist )
            # if d2 < d1:
            #     # if last position is less than first position, vessel can be arriving
            #     arriving.append( diff / dist )
            # else:
            #     # if last position is greater than first position, vessel can be leaving
            #     arriving.append( 0 )           

        return np.array( arriving )


    def get_gdf_brazil( self ):
        return self.gdf_brazil
    
    def verifica_trajetoria_cruzou_costa( self, traj ):       
         
        return self.gdf_brazil.geometry.crosses(traj.to_linestring())
    
    def calc_point_inside_eez( self, lon, lat ):
        ponto = Point(lon, lat)
        # Isso retorna uma Series de valores booleanos
        esta_dentro = self.gdf_eez_brazil.contains(ponto)

        # Para verificar se o ponto está dentro de pelo menos um polígono
        return esta_dentro.any()

    def calc_traj_inside_eez( self, traj ):

        is_inside = traj.df.apply(lambda row: self.gdf_eez_brazil.contains(row['geometry']).any(), axis=1)

        return is_inside


    def calc_trajs_inside_eez( self, trajs ):
        print("Calc trajectories inside Brazil EEZ ...")
        t = []
        for traj in tqdm(trajs.trajectories[:]):
            is_inside = traj.df.apply(lambda row: self.gdf_eez_brazil.contains(row['geometry']).any(), axis=1)
            d = is_inside.any( )
            t.append( int(d) )

        return np.array( t )

    def filter_gdf_inside_eez( self, gdf ):        
        dist = CalcDistanciaCosta( )
        # is_inside = gdf.reset_index().apply(lambda row: self.gdf_eez_brazil.contains(row['geometry']).any(), axis=1)
        is_inside = gdf.reset_index().progress_apply(lambda row: self.gdf_eez_brazil.contains(row['geometry']).any(), axis=1)
        
        return gdf.reset_index()[ is_inside ]


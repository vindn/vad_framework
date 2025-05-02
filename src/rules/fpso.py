# %%
import pandas as pd
import geopandas as gpd
from src.rules.anchorage_zones import AnchorageZone
from shapely.geometry import Polygon


class FPSO:
    def __init__(self, square_size_in_meters=5000):
        # Localizacao das FPSOs
        # https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/lpo/dados-abertos-plataformas-operacao.csv
        # file_path = 'src/rules/fpsos.geojson'
        file_path = "src/rules/fpso.csv"
        self.df = gpd.read_file(file_path)
        self.df['[LATITUDE]'] = pd.to_numeric(self.df['[LATITUDE]'], errors='coerce')
        self.df['[LONGITUDE]'] = pd.to_numeric(self.df['[LONGITUDE]'], errors='coerce')
        # Convertendo o DataFrame em GeoDataFrame
        self.gdf_instalacoes = gpd.GeoDataFrame(
            self.df,
            geometry=gpd.points_from_xy(self.df['[LONGITUDE]'], self.df['[LATITUDE]']),
            crs="EPSG:4326"
        )

        # Deslocamento aproximado em graus para 500 metros. Este valor é uma aproximação.
        # Para precisão real, converter para um sistema UTM é necessário.
        distance_in_deg = square_size_in_meters / 111320  # 111320 é uma aproximação da conversão metros para graus na equador.

        # Criar os quadrados
        squares = [self.create_square_around_point(row['[LATITUDE]'], row['[LONGITUDE]'], distance_in_deg) for idx, row in self.gdf_instalacoes.iterrows()]

        # Criar um novo GeoDataFrame com os quadrados
        self.gdf_squares = gpd.GeoDataFrame(self.gdf_instalacoes[['[SIGLA DA INSTALAÇÃO]']], geometry=squares, crs="EPSG:4326")
        

    # Função para criar um quadrado ao redor de um ponto em EPSG:4326
    def create_square_around_point(self, lat, lon, distance_in_deg):
        """
        Cria um quadrado ao redor de um ponto.
        
        Args:
        - lat, lon: Latitude e Longitude do ponto central.
        - distance_in_deg: Deslocamento em graus para formar o quadrado.
        
        Returns:
        - Polygon representando o quadrado.
        """
        return Polygon([
            (lon - distance_in_deg, lat - distance_in_deg),
            (lon - distance_in_deg, lat + distance_in_deg),
            (lon + distance_in_deg, lat + distance_in_deg),
            (lon + distance_in_deg, lat - distance_in_deg)
        ])

    def plot_fpsos( self ):
        az = AnchorageZone(None)
        az.gdf_poly = self.gdf_squares
        return az.draw_polygons_on_map()
    
    def is_inside( self, gdf ):
        # Realiza a junção espacial para encontrar interseções
        intersections = gpd.sjoin(gdf, self.gdf_squares, how='inner', op='intersects')
        any_intersection = not intersections.empty
        return any_intersection
    
    def is_trajs_inside( self, trajs ):
        fpso_trajs = []
        for i in range( len(trajs.trajectories) ):
            traj = trajs.trajectories[i]
            if self.is_inside( traj.to_traj_gdf() ):
                fpso_trajs.append( 1 )
            else:
                fpso_trajs.append( 0 )

        return fpso_trajs
    

# %%

# fpso = FPSO()
# fpso.plot_fpsos( )

# %%

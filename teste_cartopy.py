# %%
from src.preprocessing import PreprocessingStream
from src.rules.distancia_costa import CalcDistanciaCosta
from multiprocessing import Process, Queue
import multiprocessing
import geopandas as gpd
import pickle
import movingpandas as mpd
import numpy as np
import pandas as pd
from tqdm import tqdm
import time

def read_pickle_obj(file_name):
    try:
        with open(file_name, 'rb') as data_file:
            data = pickle.load(data_file)
            return data
    except Exception as e:
        print(e, "File not Found!")

##
## Plot trajectory for use in the paper
##

from shapely.geometry import Point, LineString, Polygon

# plot gdf points
def plot_gdf( gdf, vessel_description ):
    import folium

    latitude_initial = gdf.iloc[0]['lat']
    longitude_initial = gdf.iloc[0]['lon']

    m = folium.Map(location=[latitude_initial, longitude_initial], zoom_start=10)

    for _, row in gdf.iterrows():

        # vessel_description = vessel_type_mapping.get( int( row['VesselType'] ), "Unknown")
        # vessel_description = vessel_type_mapping.get( int( row['VesselType'] ), "Unknown")

        # Concatenar colunas para o popup
        popup_content = f"<b>Timestamp:</b> {row.name}<br><b>VesselName:</b> {row['nome_navio']}<br><b>MMSI</b>: {row['mmsi']}<br><b>LAT:</b> {row['lat']}<br><b>LON:</b> {row['lon']}<br><b>SOG:</b> {row['veloc']}<br><b>Type:</b> {vessel_description}<br><b>COG:</b> {row['rumo']}<br>"
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


def create_linestring(group):        
    # Ordenar por timestamp
    group = group.sort_values(by='dh')      
    # Se há mais de um ponto no grupo, crie uma LineString, caso contrário, retorne None
    return LineString(group.geometry.tolist()) if len(group) > 1 else None


# plot trajectories from points
def plot_trajectory( gdf, vessel_description ):
    import folium

    lines = gdf.groupby('mmsi').apply(create_linestring)

    # Remove possíveis None (se algum grupo tiver apenas um ponto)
    lines = lines.dropna()

    # Crie um novo GeoDataFrame com as LineStrings
    lines_gdf = gpd.GeoDataFrame(lines, columns=['geometry'], geometry='geometry')

    lines_gdf.reset_index(inplace=True)

    # start_point = Point(lines_gdf.iloc[0].geometry.coords[0])
    # m = folium.Map(location=[start_point.y, start_point.x], zoom_start=10)

    m = plot_gdf( gdf, vessel_description )

    for _, row in lines_gdf.iterrows():            
        if row['geometry'].geom_type == 'LineString':
            popup_content = f"{row['mmsi']}"
            coords = list(row['geometry'].coords)
                
            folium.PolyLine(locations=[(lat, lon) for lon, lat in coords], 
                        popup=popup_content,
                        weight=0.5
            ).add_to(m)

    return m



########## MAIN ##################

### Evento de chegada AIS

# %%    
# Preprocessa e retorna trajetorias
# gdf_sistram = read_pickle_obj("data/sistram/gdf_sistram_1dn_ais_ihs.pkl")    
# gdf_sistram = read_pickle_obj("data/sintetic/gdf_sintetic.pkl") 
# gdf_sistram = read_pickle_obj("data/sintetic/gdf_sintetic2.pkl") 
# gdf_sistram = read_pickle_obj("/home/vindn/SISTRAM/gdf_ais_outros_dn/gdf_600000000_699999999.pickle") 
# gdf_sistram = read_pickle_obj("/home/vindn/SISTRAM/gdf_ais_outros_dn/gdf_500000000_599999999.pickle") 
gdf_sistram = read_pickle_obj("/home/vindn/SISTRAM/gdf_ais_outros_dn/gdf_400000000_499999999.pickle") 

# gdf_sistram['mmsi'] = gdf_sistram['mmsi'].fillna(0).astype(int)
gdf_sistram = gdf_sistram.dropna(subset=['mmsi'])
gdf_sistram['mmsi'] = gdf_sistram['mmsi'].fillna(0).astype(int)
# gdf_sistram['mmsi'] = gdf_sistram['mmsi'].astype(str)
# gdf_sistram['mmsi'] = gdf_sistram['mmsi'].astype(str).str.replace('\.0$', '', regex=True) 
geometry = [Point(xy) for xy in zip(gdf_sistram['lon'], gdf_sistram['lat'])]
gdf_sistram = gpd.GeoDataFrame(gdf_sistram, geometry=geometry)
gdf_sistram = gdf_sistram.set_index('dh')
# gdf_sistram.rename(columns={'rumo': 'shipcourse', 'veloc': 'shipspeed'}, inplace=True)  
print("Number of lines: " + str(len(gdf_sistram)) )

# %%
# from src.preprocessing import PreprocessingStream

# preprocessing = PreprocessingStream( gdf_sistram )
# trajs, trajs_info = preprocessing.run()

# Create unique trajectories by vessel
gdf = gdf_sistram.reset_index()

dist = CalcDistanciaCosta( )
gdf = dist.filter_gdf_inside_eez( gdf_sistram.reset_index()[:] )

gdf['dh'] = pd.to_datetime(gdf['dh'], utc=True)
gdf['traj_id'] = gdf['mmsi']
trajs = mpd.TrajectoryCollection(
    gdf, "traj_id",  t='dh', min_length=200, crs='epsg:4326')



# %%

import geopandas as gpd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from scipy.stats import gaussian_kde
import numpy as np
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER

class TrajectoryPlotter:
    def __init__(self, gdf):
        self.gdf = gdf

    def plot_density(self):
        # Extrair pontos de todas as linhas
        x = []
        y = []
        for line in self.gdf.geometry:
            xs, ys = line.xy
            x.extend(xs)
            y.extend(ys)

        # Calculando a densidade KDE
        xy = np.vstack([x, y])
        # kde = gaussian_kde(xy, bw_method='scott')
        kde = gaussian_kde(xy, bw_method=0.1)

        # Criando um grid para avaliar o KDE
        xmin, xmax = min(x), max(x)
        ymin, ymax = min(y), max(y)
        xi, yi = np.mgrid[xmin:xmax:100j, ymin:ymax:100j]
        zi = kde(np.vstack([xi.flatten(), yi.flatten()]))

        # Configuração inicial do plot
        fig, ax = plt.subplots(
            figsize=(15, 10),
            subplot_kw={'projection': ccrs.PlateCarree()}
        )
        ax.add_feature(cfeature.LAND)
        ax.add_feature(cfeature.OCEAN)
        ax.add_feature(cfeature.COASTLINE)
        ax.add_feature(cfeature.BORDERS, linestyle=':')

        # Plotando o heatmap
        cmap = plt.get_cmap('Blues')
        heatmap = ax.pcolormesh(xi, yi, zi.reshape(xi.shape), shading='auto', cmap=cmap, transform=ccrs.PlateCarree())
        plt.colorbar(heatmap, ax=ax, shrink=0.5, label='Density')

        # Adicionando grids e labels
        gl = ax.gridlines(draw_labels=True, linewidth=1, color='gray', alpha=0.5, linestyle='--')
        gl.top_labels = False
        gl.right_labels = False
        gl.xlabels_bottom = True
        gl.ylabels_left = True
        gl.xformatter = LONGITUDE_FORMATTER
        gl.yformatter = LATITUDE_FORMATTER
        gl.xlabel_style = {'size': 12, 'color': 'black', 'weight': 'bold'}
        gl.ylabel_style = {'size': 12, 'color': 'black', 'weight': 'bold'}

        plt.show()

    def plot(self):
        fig, ax = plt.subplots(
            figsize=(15, 10),
            subplot_kw={'projection': ccrs.PlateCarree()}
        )
        ax.add_feature(cfeature.LAND)
        ax.add_feature(cfeature.OCEAN)
        ax.add_feature(cfeature.COASTLINE)
        ax.add_feature(cfeature.BORDERS, linestyle=':')

        minx, miny, maxx, maxy = self.gdf.total_bounds
        ax.set_extent([minx, maxx, miny, maxy], crs=ccrs.PlateCarree())

        # Adicionando grids e labels
        gl = ax.gridlines(draw_labels=True, linewidth=1, color='gray', alpha=0.5, linestyle='--')
        gl.top_labels = False
        gl.right_labels = False
        gl.xlabels_bottom = True
        gl.ylabels_left = True

        # Utilizando formatadores padrão, modificados para remover a direção
        gl.xformatter = LONGITUDE_FORMATTER
        gl.yformatter = LATITUDE_FORMATTER
        gl.xformatter.degree_symbol = ''
        gl.yformatter.degree_symbol = ''

        # Plotar cada trajetória
        for idx, row in self.gdf.iterrows():
            xs, ys = row['geometry'].xy
            ax.plot(xs, ys, 'b-', transform=ccrs.Geodetic(), alpha=0.5)

        plt.show()        




# %%
# Exemplo de criação do GeoDataFrame e uso da classe
import geopandas as gpd
from shapely.geometry import LineString

# Criar dados de exemplo
# data = {
#     'geometry': [LineString([(2, 3), (3, 5), (5, 8)]), LineString([(2, 2), (3, 3), (4, 5)])]
# }
# gdf = gpd.GeoDataFrame(data, crs="EPSG:4326")

gdf_lines = trajs.to_line_gdf( )

gdf = gdf_lines[:]

# Instanciar a classe e plotar
plotter = TrajectoryPlotter(gdf)
plotter.plot()

# %%
plotter.plot_density( )

# %%

dist.gdf_eez_brazil

# %%

gdf_sistram.reset_index()[ dist.gdf_eez_brazil.contains( gdf_sistram.reset_index()[:]['geometry'] ) ]
# %%
dist = CalcDistanciaCosta( )
is_inside = gdf_sistram[:1000].reset_index().apply(lambda row: dist.gdf_eez_brazil.contains(row['geometry']).any(), axis=1)

# %%
gdf_sistram.reset_index()[:1000][ is_inside ]
# %%
from src.database.metamodel_base import MetamodelDB

db = MetamodelDB()
trajectories = db.get_trajectories_all( )
# %%
lines = trajectories.to_line_gdf( )

# %%

lines[ lines['t'] > '2023-01-01']

# %%
from src.database.metamodel_base import MetamodelDB
db = MetamodelDB()
db.update_metamodel_trajectories_synthetic()
# %%

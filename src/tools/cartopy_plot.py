import geopandas as gpd
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

class TrajectoryPlotter:
    def __init__(self, gdf):
        """
        Inicializa a classe com um GeoDataFrame contendo as trajetórias.

        Parâmetros:
        - gdf: GeoDataFrame com uma coluna 'geometry' que contém linhas (LineStrings).
        """
        self.gdf = gdf

    def plot(self):
        """
        Plota o mapa com os fluxos das trajetórias.
        """
        # Configuração inicial do plot
        fig, ax = plt.subplots(
            figsize=(15, 10),
            subplot_kw={'projection': ccrs.PlateCarree()}
        )
        ax.add_feature(cfeature.LAND)
        ax.add_feature(cfeature.OCEAN)
        ax.add_feature(cfeature.COASTLINE)
        ax.add_feature(cfeature.BORDERS, linestyle=':')

        # Determinar os limites do plot baseando-se no gdf
        minx, miny, maxx, maxy = self.gdf.total_bounds
        ax.set_extent([minx, maxx, miny, maxy], crs=ccrs.PlateCarree())

        # Plotar cada trajetória
        for idx, row in self.gdf.iterrows():
            xs, ys = row['geometry'].xy
            ax.plot(xs, ys, 'b-', transform=ccrs.Geodetic(), alpha=0.5)  # Trajetórias semi-transparentes

        plt.show()

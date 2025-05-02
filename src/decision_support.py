# Apoio à decisão
# Utiliza as informações processadas para fornecer insights e apoiar decisões, como a geração de alertas ou relatórios. (Nivel 4)
# Colocar aqui:
# Avaliação e resposta do especialista com relação a predição do modelo.


from src.fusion_base import DataFusionBase
from src.database.metamodel_base import MetamodelDB
from src.tools.performance import Performance
from shapely.geometry import Point, LineString, Polygon
import pandas as pd
import geopandas as gpd

class DecisionSupport:
    
    def __init__(self):
        self.db = MetamodelDB()
        self.meta_model = None

    def insert_specialist_response_row( self, row, classification, al_prediction ):
        self.db.set_classificacao_traj_performance( row, classification, classificacao_al=al_prediction )

    def insert_specialist_response_id( self, meta_id, classification, op=None ):
        print("insere classificacao: metaid = " + str(meta_id) + " classificacao = " + classification )
        # rows = self.db.get_row_by_traj_id( meta_id )
        rows = self.db.get_row_by_id( meta_id )
        print(rows)
        # After 500 trajectories rated, start to count trajectories classification to ACC calculation.
        self.set_classificacao_traj_performance( rows, classification, 600, op=op )

    def set_classificacao_traj_performance( self, row, classificacao, min_cold_start=100, classificacao_al=None, op=None ):
        row = row.iloc[0]
        self.db.set_classificacao_traj_performance( row, classificacao, min_cold_start=min_cold_start, classificacao_al=classificacao_al, op=op )

    def generate_reports(self):
        ## Test performance class
        perf = Performance()
        perf.calc_acc( )


    def alert_generation(self):
        # Geração de alertas
        pass

    # plot gdf points
    def plot_gdf( self, gdf, vessel_description, m=None, color='blue', meta_id=0 ):
        import folium

        latitude_initial = gdf.iloc[0]['lat']
        longitude_initial = gdf.iloc[0]['lon']

        if not m:
            m = folium.Map(location=[latitude_initial, longitude_initial], zoom_start=10)

        for _, row in gdf.iterrows():

            # vessel_description = vessel_type_mapping.get( int( row['VesselType'] ), "Unknown")
            # vessel_description = vessel_type_mapping.get( int( row['VesselType'] ), "Unknown")

            # Concatenar colunas para o popup
            popup_content = f"<b>meta_id:</b> {meta_id}<br><b>Traj_id:</b> {row.traj_id}<br><b>Timestamp:</b> {row.name}<br><b>VesselName:</b> {row['nome_navio']}<br><b>MMSI</b>: {row['mmsi']}<br><b>LAT:</b> {row['lat']}<br><b>LON:</b> {row['lon']}<br><b>SOG:</b> {row['veloc']}<br><b>Type:</b> {vessel_description}<br><b>COG:</b> {row['rumo']}"
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
    def plot_trajectory( self, gdf, vessel_description, m=None, color='blue', meta_id=0 ):
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
            m = self.plot_gdf( gdf, vessel_description, color=color, meta_id=meta_id )
        else:
            self.plot_gdf( gdf, vessel_description, m, color=color, meta_id=meta_id )

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
            m = self.plot_trajectory( gdf1, "vessel 1", m=None, color='blue' )
            m = self.plot_trajectory( gdf2, "vessel 2", m, color='red' )
        else:
            m = self.plot_trajectory( gdf1, "vessel 1", m=m, color='blue' )
            m = self.plot_trajectory( gdf2, "vessel 2", m, color='red' )

        return m

    def get_color( self, atividade ):
        color = "blue"
        if atividade == "atividade_suspeita":
            color = "red"
        elif atividade == "atividade_anomala":
            color = "purple"
        elif atividade == "pesca_ilegal":
            color = "orange"
        elif atividade == "Encounter Trajectory":
            color = "red"

        return color
            

    def plot_trajectory_classification( self ):
        self.meta_model = self.db.get_meta_model( )
        m = None
        for i in range( len(self.meta_model) ):
            row = self.meta_model.iloc[i]
            traj = self.db.get_trajectory( int(row["traj_fk"]) )
            if m is None:
                m = self.plot_trajectory( traj.df, row["predicao"], m=None, color=self.get_color( row["predicao"] ), meta_id=row["id"] )
            else:
                m = self.plot_trajectory( traj.df, row["predicao"], m, color=self.get_color( row["predicao"] ), meta_id=row["id"] )

        return m
    
    def plot_illegal_fishing_trajectories( self ):
        self.meta_model = self.db.get_meta_model( )
        m = None
        for index, row in self.meta_model[ self.meta_model["predicao"] == "pesca_ilegal" ].iterrows( ) :
            traj = self.db.get_trajectory( row["traj_fk"] )
            # if date is greather than 2023 is a syntetic trajectory
            first_date = traj.df.reset_index().loc[0, 'dh']
            # if first_date > pd.to_datetime('2023-01-01'):
            #     continue
            if row["classificacao"] != None:
                continue
            
            if m is None:
                m = self.plot_trajectory( traj.df, row["predicao"], m=None, color=self.get_color( row["predicao"] ), meta_id=row["id"] )
            else:
                m = self.plot_trajectory( traj.df, row["predicao"], m, color=self.get_color( row["predicao"] ), meta_id=row["id"] )

        return m

    def plot_suspected_trajectories( self ):
        self.meta_model = self.db.get_meta_model( )
        m = None
        for index, row in self.meta_model[ (self.meta_model["predicao"] == "atividade_suspeita") & ( self.meta_model["classificacao"].isnull() ) ].iterrows( ) :
            traj = self.db.get_trajectory( row["traj_fk"] )
            # if date is greather than 2023 is a syntetic trajectory
            first_date = traj.df.reset_index().loc[0, 'dh']
            if first_date > pd.to_datetime('2023-01-01'):
                continue
            if m is None:
                m = self.plot_trajectory( traj.df, row["predicao"], m=None, color=self.get_color( row["predicao"] ), meta_id=row["id"] )
            else:
                m = self.plot_trajectory( traj.df, row["predicao"], m, color=self.get_color( row["predicao"] ), meta_id=row["id"] )

        return m

    def plot_anomalous_trajectories( self ):
        self.meta_model = self.db.get_meta_model( )
        m = None
        for index, row in self.meta_model[ self.meta_model["predicao"] == "atividade_anomala" ].iterrows( ) :
            traj = self.db.get_trajectory( row["traj_fk"] )
            # if date is greather than 2023 is a syntetic trajectory
            first_date = traj.df.reset_index().loc[0, 'dh']
            if first_date > pd.to_datetime('2023-01-01'):
                continue

            ## for anounmalous trajectories not be confuded with buoy or a marine beacons
            meta_id = int(row['id'])
            traj = self.db.get_trajectory_by_metamodel_id( meta_id )
            if traj.df['distance_to_coast'].mean() < 10 or traj.df['speed_nm'].mean( ) < 2:
                continue

            if m is None:
                m = self.plot_trajectory( traj.df, row["predicao"], m=None, color=self.get_color( row["predicao"] ), meta_id=row["id"] )
            else:
                m = self.plot_trajectory( traj.df, row["predicao"], m, color=self.get_color( row["predicao"] ), meta_id=row["id"] )

            if m is None:
                m = self.plot_trajectory( traj.df, row["predicao"], m=None, color=self.get_color( row["predicao"] ), meta_id=row["id"] )
            else:
                m = self.plot_trajectory( traj.df, row["predicao"], m, color=self.get_color( row["predicao"] ), meta_id=row["id"] )

        return m

    def plot_encounter_trajectories( self ):
        self.meta_model = self.db.get_meta_model( )
        m = None
        for index, row in self.meta_model[ self.meta_model["enc"] == 1 ].iterrows( ) :
            traj = self.db.get_trajectory( row["traj_fk"] )
            # if date is greather than 2023 is a syntetic trajectory
            first_date = traj.df.reset_index().loc[0, 'dh']
            dist = traj.df.reset_index().loc[0, 'distance_to_coast']
            if first_date > pd.to_datetime('2023-01-01') or dist < 12:
                continue

            if m is None:
                m = self.plot_trajectory( traj.df, "Encounter Trajectory " + str(row['id']), m=None, color=self.get_color( "Encounter Trajectory" ), meta_id=row["id"] )
            else:
                m = self.plot_trajectory( traj.df, "Encounter Trajectory " + str(row['id']), m, color=self.get_color( "Encounter Trajectory" ), meta_id=row["id"] )

        return m
    
    def report_trajectories_by_class( self ):
        self.meta_model = self.db.get_meta_model( )        

        n_anon = len( self.meta_model[ (self.meta_model["predicao"] == "atividade_anomala") & ( self.meta_model["classificacao"].isnull() ) ] )
        n_susp = len( self.meta_model[ (self.meta_model["predicao"] == "atividade_suspeita") & ( self.meta_model["classificacao"].isnull() ) ] )
        n_norm = len( self.meta_model[ (self.meta_model["predicao"] == "atividade_normal") & ( self.meta_model["classificacao"].isnull() ) ] )
        n_fish = len( self.meta_model[ (self.meta_model["predicao"] == "pesca_ilegal") & ( self.meta_model["classificacao"].isnull() ) ] )

        print("Trajetories; number")
        print("Illegal Fishing;" + str(n_fish) )
        print("Suspicius;" + str(n_susp) )
        print("Anonmalous;" + str(n_anon) )
        print("Normal;" + str(n_norm) )

    def export_trajectories_predicted_to_csv(self, filename, activity_name ):
        trajs = self.db.get_trajectories_by_al_prediction( activity_name )

        # Export trajectories for plot in qgis
        timestamp = []
        mmsi = []
        lat = []
        lon =[]
        cog = []
        sog = []
        traj_id = []
        for traj in trajs.trajectories[:]:
            for index, row in traj.df.reset_index().iterrows():
                timestamp.append( str(row['dh']) )
                mmsi.append( row['mmsi'] )
                lat.append( row.lat )
                lon.append( row.lon )
                cog.append( row.direction )
                sog.append( row.speed_nm )
                traj_id.append( row.traj_id )

        df_export = pd.DataFrame()
        df_export['timestamp'] = timestamp
        df_export['mmsi'] = mmsi
        df_export['lat'] = lat
        df_export['lon'] = lon
        df_export['cog'] = cog
        df_export['sog'] = sog
        df_export['traj_id'] = traj_id

        df_export.to_csv(filename, header=True)







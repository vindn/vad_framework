import movingpandas as mpd
from tqdm import tqdm
from geopandas import GeoDataFrame

class CustomTrajectoryCollection(mpd.TrajectoryCollection):

    # Metodo customizado para mostrar o andamento da criacao das trajetorias
    def _df_to_trajectories(self, df, traj_id_col, obj_id_col, t, x, y, crs):
        # Inicializando a barra de progresso
        tqdm.pandas(desc="Processing trajectories")

        trajectories = []
        for traj_id, values in tqdm(df.groupby(traj_id_col), desc="Trajectories"):
            if len(values) < 2:
                continue
            if obj_id_col in values.columns:
                obj_id = values.iloc[0][obj_id_col]
            else:
                obj_id = None
            trajectory = mpd.Trajectory(
                values,
                traj_id,
                traj_id_col=traj_id_col,
                obj_id=obj_id,
                t=t,
                x=x,
                y=y,
                crs=crs,
            )
            if self.min_duration:
                if trajectory.get_duration() < self.min_duration:
                    continue
            if trajectory.df.geometry.count() < 2:
                continue
            if self.min_length > 0:
                if trajectory.get_length() < self.min_length:
                    continue
            if isinstance(df, GeoDataFrame):
                trajectory.crs = df.crs
            else:
                trajectory.crs = crs
            trajectories.append(trajectory)
        return trajectories

# Uso da classe customizada
# Substitua 'seu_dataframe' e os nomes das colunas pelos seus dados específicos
# custom_traj_collection = CustomTrajectoryCollection(seu_dataframe, 'traj_id_col', 'obj_id_col', 't', 'x', 'y', 'crs')


class CustomObservationGapSplitter( mpd.ObservationGapSplitter ):
    def _split_traj(self, traj, gap, min_length=0):
        tqdm.pandas(desc="Spliting trajectories...")
        result = []
        temp_df = traj.df.copy()
        temp_df["t"] = temp_df.index
        temp_df["gap"] = temp_df["t"].diff() > gap
        temp_df["gap"] = temp_df["gap"].apply(lambda x: 1 if x else 0).cumsum()
        dfs = [group[1] for group in temp_df.groupby(temp_df["gap"])]
        for i, df in enumerate(dfs):
            df = df.drop(columns=["t", "gap"])
            if len(df) > 1:
                result.append(
                    mpd.Trajectory(df, f"{traj.id}_{i}", traj_id_col=traj.get_traj_id_col())
                )
        return mpd.TrajectoryCollection(result, min_length=min_length)
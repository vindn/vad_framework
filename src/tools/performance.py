# %%

# from src.database.metamodel_base import MetamodelDB
from src.database.metamodel_base import MetamodelDB
import pandas as pd

# %%

class Performance:
    def __init__(self):
        self.db = MetamodelDB( )
        self.tb_classificacao = self.db.get_classificacao_table( )
        self.df_classificacao = pd.DataFrame( self.tb_classificacao )
        self.df_classificacao.drop(0, axis=1, inplace=True)
        self.df_classificacao = self.df_classificacao.rename(columns={1: 'traj_id', 2: 'al', 3: 'dbscan', 4: 'kmeans', 5: 'voting', 6: 'human', 7:'user'} )

    def calc_acc(self, coluna_correta='human'):
        df = self.df_classificacao
        acuracias = {}
        modelos = [col for col in df.columns if col not in ['traj_id', coluna_correta]]
        for modelo in modelos:
            acuracia = (df[modelo] == df[coluna_correta]).mean()
            acuracias[modelo] = acuracia
        acuracias["n"] = len(df)
        return acuracias
    
    def calc_acc_by_class(self, coluna_correta='human'):
        df = self.df_classificacao
        classes = df['al'].unique()
        modelos = [col for col in df.columns if col not in ['traj_id', 'human']]
        acc_classes = {}
        for c in classes:
            n = len(df[ df['al'] == c ] )
            acuracias = {}
            for modelo in modelos:
                acuracia = len( df[ (df[modelo] == df['human']) & (df[modelo] == c) ] )       
                acuracias[modelo] = acuracia/n
            acuracias["n"] = n
            acc_classes[c] = acuracias

        return acc_classes
    
    def confusion_matrix( self, op=None ):
        from sklearn.metrics import confusion_matrix

        if op is None:
            data_split = self.df_classificacao[['al', 'human']]
        else:
            data_split = self.df_classificacao[ self.df_classificacao['user']==op ][['al', 'human']]

        data_split['al'] = data_split['al'].str.replace("pesca_ilegal", "ilegall fishing")
        data_split['human'] = data_split['human'].str.replace("pesca_ilegal", "ilegall fishing")
        data_split['al'] = data_split['al'].str.replace("atividade_suspeita", "suspicius")
        data_split['human'] = data_split['human'].str.replace("atividade_suspeita", "suspicius")
        data_split['al'] = data_split['al'].str.replace("atividade_normal", "normal")
        data_split['human'] = data_split['human'].str.replace("atividade_normal", "normal")
        data_split['al'] = data_split['al'].str.replace("atividade_anomala", "anonmalous")
        data_split['human'] =  data_split['human'].str.replace("atividade_anomala", "anonmalous")

        # Calculate the confusion matrix
        cm = confusion_matrix(data_split['human'], data_split['al'], labels=data_split['human'].unique())

        print(data_split['human'].unique())
        # Create a DataFrame for the confusion matrix for better readability
        cm_df = pd.DataFrame(cm, index=data_split['human'].unique(), columns=data_split['human'].unique())

        return cm_df

    def confusion_matrix_pt( self, op=None ):
        from sklearn.metrics import confusion_matrix

        if op is None:
            data_split = self.df_classificacao[['al', 'human']]
        else:
            data_split = self.df_classificacao[ self.df_classificacao['user']==op ][['al', 'human']]

        data_split['al'] = data_split['al'].str.replace("pesca_ilegal", "pesca ilegal")
        data_split['human'] = data_split['human'].str.replace("pesca_ilegal", "pesca ilegal")
        data_split['al'] = data_split['al'].str.replace("atividade_suspeita", "suspeita")
        data_split['human'] = data_split['human'].str.replace("atividade_suspeita", "suspeita")
        data_split['al'] = data_split['al'].str.replace("atividade_normal", "normal")
        data_split['human'] = data_split['human'].str.replace("atividade_normal", "normal")
        data_split['al'] = data_split['al'].str.replace("atividade_anomala", "anômala")
        data_split['human'] =  data_split['human'].str.replace("atividade_anomala", "anômala")

        # Calculate the confusion matrix
        cm = confusion_matrix(data_split['human'], data_split['al'], labels=data_split['human'].unique())

        print(data_split['human'].unique())
        # Create a DataFrame for the confusion matrix for better readability
        cm_df = pd.DataFrame(cm, index=data_split['human'].unique(), columns=data_split['human'].unique())

        return cm_df


    def confusion_matrix_plot( self, op=None ):
        import seaborn as sns
        import matplotlib.pyplot as plt

        # Calculate the confusion matrix
        cm_df = self.confusion_matrix( op=op )
        # Plot the confusion matrix
        plt.figure(figsize=(10, 7))
        sns.heatmap(cm_df, annot=True, fmt='d', cmap='Blues',cbar=False)
        plt.xlabel('Predicted Labels (al)')
        plt.ylabel('True Labels (human)')
        plt.title('Confusion Matrix: AL vs. Human')
        plt.show()        

    def confusion_matrix_plot_pt( self, op=None ):
        import seaborn as sns
        import matplotlib.pyplot as plt

        # Calculate the confusion matrix
        cm_df = self.confusion_matrix_pt( op=op )
        # Plot the confusion matrix
        plt.figure(figsize=(10, 7))
        sns.heatmap(cm_df, annot=True, fmt='d', cmap='Blues',cbar=False)
        plt.xlabel('Rótulos Preditos (al)')
        plt.ylabel('Rótulos Verdadeiros (humano)')
        plt.title('Matriz de Confusão: AL vs. Humano')

        plt.show()        


    def precision_recall_f1( self ):
        from sklearn.metrics import precision_recall_fscore_support, classification_report
        
        data_split = self.df_classificacao[['al', 'human']]

        data_split['al'] = data_split['al'].str.replace("pesca_ilegal", "ilegall fishing")
        data_split['human'] = data_split['human'].str.replace("pesca_ilegal", "ilegall fishing")
        data_split['al'] = data_split['al'].str.replace("atividade_suspeita", "suspicius")
        data_split['human'] = data_split['human'].str.replace("atividade_suspeita", "suspicius")
        data_split['al'] = data_split['al'].str.replace("atividade_normal", "normal")
        data_split['human'] = data_split['human'].str.replace("atividade_normal", "normal")
        data_split['al'] = data_split['al'].str.replace("atividade_anomala", "anonmalous")
        data_split['human'] =  data_split['human'].str.replace("atividade_anomala", "anonmalous")


        # Calculando precisão, recall, f1 e suporte
        precision, recall, f1, support = precision_recall_fscore_support(data_split['human'], data_split['al'], average=None)
        classes = list( data_split['human'].unique() )
        classes.reverse()
        print(classes)

        # Exibindo os resultados com as classes
        print(f'Classes: {classes}')
        print(f'Precision: {precision}')
        print(f'Recall: {recall}')
        print(f'F1-score: {f1}')
        print(f'Support: {support}')

        # Usando classification_report para obter um relatório completo
        print("\nRelatório de Classificação:")
        print(classification_report(data_split['al'], data_split['human'], target_names=[str(cls) for cls in classes]))


    def calculate_metrics(self, op=None):
        import pandas as pd
        from sklearn.metrics import accuracy_score
        from sklearn.metrics import confusion_matrix

        """
        Calculate precision, recall, and F1-score for each class.

        Parameters:
        data (pd.DataFrame): The DataFrame containing the predictions and ground truth.
        pred_column (str): The name of the column containing the predictions.
        true_column (str): The name of the column containing the ground truth.

        Returns:
        pd.DataFrame: A DataFrame with precision, recall, and F1-score for each class.
        """
        if op is None:
            data_split = self.df_classificacao[['al', 'human']]
        else:
            data_split = self.df_classificacao[self.df_classificacao['user']==op][['al', 'human']]

        data_split['al'] = data_split['al'].str.replace("pesca_ilegal", "ilegall fishing")
        data_split['human'] = data_split['human'].str.replace("pesca_ilegal", "ilegall fishing")
        data_split['al'] = data_split['al'].str.replace("atividade_suspeita", "suspicius")
        data_split['human'] = data_split['human'].str.replace("atividade_suspeita", "suspicius")
        data_split['al'] = data_split['al'].str.replace("atividade_normal", "normal")
        data_split['human'] = data_split['human'].str.replace("atividade_normal", "normal")
        data_split['al'] = data_split['al'].str.replace("atividade_anomala", "anonmalous")
        data_split['human'] =  data_split['human'].str.replace("atividade_anomala", "anonmalous")


        # Extract predictions and ground truth
        y_pred = data_split['al']
        y_true = data_split['human']

        # Get unique class labels
        class_labels = data_split['human'].unique()
        
    # Calculate the confusion matrix
        conf_matrix = confusion_matrix(y_true, y_pred, labels=class_labels)
        
        # Calculate precision, recall, F1-score, and support for each class
        precision_per_class = {}
        recall_per_class = {}
        f1_per_class = {}
        support_per_class = {}

        for idx, cls in enumerate(class_labels):
            tp = conf_matrix[idx, idx]
            fp = conf_matrix[:, idx].sum() - tp
            fn = conf_matrix[idx, :].sum() - tp
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            support = conf_matrix[idx, :].sum()
            
            precision_per_class[cls] = precision
            recall_per_class[cls] = recall
            f1_per_class[cls] = f1
            support_per_class[cls] = support

        # Calculate overall accuracy
        accuracy = accuracy_score(y_true, y_pred)
        
        # Calculate macro average
        macro_precision = sum(precision_per_class.values()) / len(class_labels)
        macro_recall = sum(recall_per_class.values()) / len(class_labels)
        macro_f1 = sum(f1_per_class.values()) / len(class_labels)

        # Calculate weighted average
        total_support = sum(support_per_class.values())
        weighted_precision = sum(precision_per_class[cls] * support_per_class[cls] for cls in class_labels) / total_support
        weighted_recall = sum(recall_per_class[cls] * support_per_class[cls] for cls in class_labels) / total_support
        weighted_f1 = sum(f1_per_class[cls] * support_per_class[cls] for cls in class_labels) / total_support

        # Create a DataFrame to display the recalculated results
        metrics_df = pd.DataFrame({
            'Class': list(class_labels) + ['accuracy', 'macro avg', 'weighted avg'],
            'Precision': list(precision_per_class.values()) + [None, macro_precision, weighted_precision],
            'Recall': list(recall_per_class.values()) + [None, macro_recall, weighted_recall],
            'F1-Score': list(f1_per_class.values()) + [None, macro_f1, weighted_f1],
            'Support': list(support_per_class.values()) + ['', '', '']
        })

        # Insert accuracy into the DataFrame
        metrics_df.loc[metrics_df['Class'] == 'accuracy', 'Precision'] = accuracy
        metrics_df.loc[metrics_df['Class'] == 'accuracy', 'Recall'] = accuracy
        metrics_df.loc[metrics_df['Class'] == 'accuracy', 'F1-Score'] = accuracy

        return metrics_df
    
    @staticmethod
    def learning_rate( ):
        db = MetamodelDB( )    
        meta_model = db.get_meta_model()
        df_perf = meta_model[ meta_model['predicao'].notnull( ) &  meta_model['classificacao'].notnull( ) ]
        n_rated = len( meta_model[ meta_model['classificacao'].notnull( ) ] )
        n_hits = 0
        for m in df_perf.itertuples( ):
            if m.predicao == m.classificacao:
                n_hits += 1

        acc = n_hits / n_rated

        print("Acc: " + str(acc) )


    @staticmethod
    def count(op=None):
        db = MetamodelDB( )    
        classificacao = db.get_classificacao_table( )
        columns = ['id', 'traj_id', 'al', 'dbscan', 'kmeans', 'voting', 'human', 'user']

        # Converter a lista em um DataFrame
        df_classificacao = pd.DataFrame(classificacao, columns=columns)

        if op is None:
            illegal_fishing = len(df_classificacao[  (df_classificacao['al']=="pesca_ilegal") ])
            suspicius = len(df_classificacao[  (df_classificacao['al']=="atividade_suspeita") ])
            normal = len(df_classificacao[  (df_classificacao['al']=="atividade_normal") ])
            anomala = len(df_classificacao[  (df_classificacao['al']=="atividade_anomala") ])
        else:
            illegal_fishing = len(df_classificacao[ (df_classificacao['user']==op) & (df_classificacao['al']=="pesca_ilegal")])
            suspicius = len(df_classificacao[ (df_classificacao['user']==op) & (df_classificacao['al']=="atividade_suspeita")])
            normal = len(df_classificacao[ (df_classificacao['user']==op) & (df_classificacao['al']=="atividade_normal")])
            anomala = len(df_classificacao[ (df_classificacao['user']==op) & (df_classificacao['al']=="atividade_anomala")])

        print("Normal: " + str(normal))
        print("Anonmalous: " + str(anomala))
        print("Suspicius: " + str(suspicius))
        print("Illegal Fishing: " + str(illegal_fishing))



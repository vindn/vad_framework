import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from modAL.models import ActiveLearner
from modAL.uncertainty import uncertainty_sampling

class ActiveLearningModel:
    def __init__(self, df, label_column='classificacao'):
        self.df = df
        self.label_column = label_column
        self.learner = None

    def fit(self):
        X = self.df.drop(self.label_column, axis=1)
        y = self.df[self.label_column]

        unlabeled = y.isnull()
        X_train = X[~unlabeled]
        y_train = y[~unlabeled]
        X_unlabeled = X[unlabeled]

        classifier = RandomForestClassifier()
        self.learner = ActiveLearner(
            estimator=classifier,
            query_strategy=uncertainty_sampling,
            X_training=X_train.to_numpy(), y_training=y_train.to_numpy()
        )
        self.X_unlabeled = X_unlabeled

    def query_instances(self, n_instances=1):
        query_idx, query_instance = self.learner.query(self.X_unlabeled, n_instances=n_instances)
        return self.X_unlabeled.iloc[query_idx]

    def update(self, X_new, y_new):
        self.learner.teach(X_new.to_numpy(), y_new.to_numpy())
        self.X_unlabeled = self.X_unlabeled.drop(index=X_new.index)

    def predict(self, X):
        return self.learner.predict(X)
    
    def predict_all_labels( self  ):
        predictions = self.predict( self.X_unlabeled )
        return predictions

# Exemplo de uso
# df = pd.read_csv('seu_dataset.csv')
# model = ActiveLearningModel(df)
# model.fit()

# Para consultar instâncias para rotular
# instances_to_label = model.query_instances(n_instances=5)

# Após rotular as instâncias (substitua y_new pelos rótulos reais)
# model.update(X_new=instances_to_label, y_new=y_new)

# Para fazer previsões
# predictions = model.predict(X_test)

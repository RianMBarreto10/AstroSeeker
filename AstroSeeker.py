import numpy as np
import lightkurve as lk
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.metrics import accuracy_score
from sklearn.pipeline import Pipeline
from sklearn.ensemble import VotingClassifier

# Baixe as curvas de luz de um conjunto de estrelas conhecidas
lc_collection = lk.search_lightcurve('TIC 141914082', mission='TESS').download_all()

# Extraia os fluxos de luz e os rótulos de classe (1 para exoplaneta, 0 para não-exoplaneta)
fluxes = np.array([lc.flux.value for lc in lc_collection])
labels = np.array([1 if lc.meta['TARGETID'] in exoplanet_tic_ids else 0 for lc in lc_collection])

# Divida os dados em conjuntos de treinamento e teste
fluxes_train, fluxes_test, labels_train, labels_test = train_test_split(fluxes, labels, test_size=0.2, random_state=42)

# Defina os classificadores
clf1 = RandomForestClassifier(random_state=42)
clf2 = GradientBoostingClassifier(random_state=42)

# Defina os hiperparâmetros para a pesquisa em grade
param_grid = {'n_estimators': [50, 100, 200], 'max_depth': [None, 10, 20, 30]}

# Ajuste os hiperparâmetros usando pesquisa em grade e validação cruzada
grid_search1 = GridSearchCV(clf1, param_grid, cv=5)
grid_search1.fit(fluxes_train, labels_train)

grid_search2 = GridSearchCV(clf2, param_grid, cv=5)
grid_search2.fit(fluxes_train, labels_train)

# Crie um classificador de votação com os classificadores ajustados
voting_clf = VotingClassifier(estimators=[('rf', grid_search1.best_estimator_), ('gb', grid_search2.best_estimator_)], voting='soft')
voting_clf.fit(fluxes_train, labels_train)

# Avalie o classificador nos dados de teste
labels_pred = voting_clf.predict(fluxes_test)
score = accuracy_score(labels_test, labels_pred)
print(f'Acurácia: {score * 100:.2f}%')

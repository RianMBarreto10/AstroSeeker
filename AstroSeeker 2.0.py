import numpy as np
import lightkurve as lk
import sqlite3
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.pipeline import Pipeline
from sklearn.ensemble import VotingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.neural_network import MLPClassifier
import pickle
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# Baixe as curvas de luz de um conjunto de estrelas conhecidas
lc_collection = lk.search_lightcurve('TIC 141914082', mission='TESS').download_all()

# Extraia os fluxos de luz e os rótulos de classe (1 para exoplaneta, 0 para não-exoplaneta)
fluxes = np.array([lc.flux.value for lc in lc_collection])
labels = np.array([1 if lc.meta['TARGETID'] in exoplanet_tic_ids else 0 for lc in lc_collection])

# Pré-processamento: remove ruídos e tendências usando a filtragem de Fourier
fluxes = np.fft.fft(fluxes)

# Seleção de características: usando PCA para reduzir a dimensionalidade dos dados
pca = PCA(n_components=10)
fluxes = pca.fit_transform(fluxes)

# Dividindo os dados em conjuntos de treinamento e teste
fluxes_train, fluxes_test, labels_train, labels_test = train_test_split(fluxes, labels, test_size=0.2, random_state=42)

# Defina os classificadores
clf1 = RandomForestClassifier(random_state=42)
clf2 = GradientBoostingClassifier(random_state=42)
clf3 = MLPClassifier(random_state=42)  

# Defina os hiperparâmetros para a pesquisa em grade
param_grid = {'n_estimators': [50, 100, 200], 'max_depth': [None, 10, 20, 30]}

# Ajuste os hiperparâmetros usando pesquisa em grade e validação cruzada
grid_search1 = GridSearchCV(clf1, param_grid, cv=5)
grid_search1.fit(fluxes_train, labels_train)

grid_search2 = GridSearchCV(clf2, param_grid, cv=5)
grid_search2.fit(fluxes_train, labels_train)

# Treine o classificador de rede neural nos dados de treinamento
clf3.fit(fluxes_train, labels_train)

# Crie um classificador de votação com os classificadores ajustados
voting_clf = VotingClassifier(estimators=[('rf', grid_search1.best_estimator_), ('gb', grid_search2.best_estimator_), ('nn', clf3)], voting='soft')
voting_clf.fit(fluxes_train, labels_train)

# Avalie o classificador nos dados de teste
labels_pred = voting_clf.predict(fluxes_test)
score = accuracy_score(labels_test, labels_pred)

# Calcule métricas adicionais
precision = precision_score(labels_test, labels_pred)
recall = recall_score(labels_test, labels_pred)
f1 = f1_score(labels_test, labels_pred)

# Conecte-se ao banco de dados SQLite
conn = sqlite3.connect('resultados.db')
c = conn.cursor()

# Crie uma tabela para armazenar os resultados
c.execute('''
    CREATE TABLE IF NOT EXISTS resultados (
        labels_test BLOB,
        labels_pred BLOB,
        score REAL,
        precision REAL,
        recall REAL,
        f1 REAL
    )
''')

# Armazene os resultados no banco de dados
c.execute('''
    INSERT INTO resultados (labels_test, labels_pred, score, precision, recall, f1)
    VALUES (?, ?, ?, ?, ?, ?)
''', (pickle.dumps(labels_test), pickle.dumps(labels_pred), score, precision, recall, f1))

# Salve as alterações e feche a conexão com o banco de dados
conn.commit()
conn.close()

# Carregue os resultados do banco de dados
conn = sqlite3.connect('resultados.db')
c = conn.cursor()
c.execute('SELECT * FROM resultados')
rows = c.fetchall()

# Para cada linha nos resultados, carregue os dados e crie um gráfico
for row in rows:
    labels_test, labels_pred, score, precision, recall, f1 = pickle.loads(row[0]), pickle.loads(row[1]), row[2], row[3], row[4], row[5]
    
    # Crie um DataFrame com os resultados
    df = pd.DataFrame({'labels_test': labels_test, 'labels_pred': labels_pred})

    # Calcule a quantidade de planetas para cada score
    score_counts = df.groupby('labels_pred').count()

    # Crie um gráfico de barras com os resultados
    plt.bar(score_counts.index, score_counts['labels_test'])
    plt.xlabel('Score')
    plt.ylabel('Quantidade de Planetas')
    plt.title('Quantidade de Planetas por Score')
    plt.show()

    # Imprime as métricas
    print(f'Precisão: {precision * 100:.2f}%')
    print(f'Revocação: {recall * 100:.2f}%')
    print(f'Pontuação F1: {f1 * 100:.2f}%')

    # Exporte o DataFrame para um arquivo CSV
    df.to_csv('resultados.csv', index=False)

# Fecha a conexão com o banco de dados
conn.close()
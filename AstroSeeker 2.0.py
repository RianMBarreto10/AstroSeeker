import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.pipeline import Pipeline
from sklearn.ensemble import VotingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.neural_network import MLPClassifier
from sklearn.feature_selection import SelectKBest, chi2
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import sqlite3
import pickle

def load_dataset():
    light_curves = np.random.rand(1000, 200)
    labels = np.random.randint(0, 2, 1000)
    return light_curves, labels

def preprocess_light_curves(light_curves):
    light_curves = np.fft.fft(light_curves)
    light_curves = np.real(light_curves)
    light_curves = np.abs(light_curves)
    return light_curves

def split_data(light_curves, labels):
    light_curves_train, light_curves_test, labels_train, labels_test = train_test_split(light_curves, labels, test_size=0.2, random_state=42)
    return light_curves_train, light_curves_test, labels_train, labels_test

def define_classifiers():
    clf1 = Pipeline([
        ('feature_selection', SelectKBest(chi2, k=10)),
        ('classification', RandomForestClassifier(random_state=42, n_jobs=-1))
    ])
    clf2 = Pipeline([
        ('feature_selection', SelectKBest(chi2, k=10)),
        ('classification', GradientBoostingClassifier(random_state=42))
    ])
    clf3 = MLPClassifier(random_state=42)
    return clf1, clf2, clf3

def tune_hyperparameters(clf, light_curves_train, labels_train):
    param_grid = {'classification__n_estimators': [50, 100, 200], 'classification__max_depth': [None, 10, 20, 30]}
    grid_search = GridSearchCV(clf, param_grid, cv=5, n_jobs=-1)
    grid_search.fit(light_curves_train, labels_train)
    return grid_search.best_estimator_

def train_nn(clf, light_curves_train, labels_train):
    clf.fit(light_curves_train, labels_train)
    return clf

def create_voting_classifier(clf1, clf2, clf3):
    voting_clf = VotingClassifier(estimators=[('rf', clf1), ('gb', clf2), ('nn', clf3)], voting='soft', n_jobs=-1)
    return voting_clf

def evaluate_classifier(voting_clf, light_curves_test, labels_test):
    labels_pred = voting_clf.predict(light_curves_test)
    score = accuracy_score(labels_test, labels_pred)
    precision = precision_score(labels_test, labels_pred)
    recall = recall_score(labels_test, labels_pred)
    f1 = f1_score(labels_test, labels_pred)
    return labels_test, labels_pred, score, precision, recall, f1

def save_results_to_db(labels_test, labels_pred, score, precision, recall, f1):
    conn = sqlite3.connect('resultados.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS resultados (labels_test BLOB, labels_pred BLOB, score REAL, precision REAL, recall REAL, f1 REAL)')
    c.execute('INSERT INTO resultados VALUES (?, ?, ?, ?, ?, ?)', (pickle.dumps(labels_test), pickle.dumps(labels_pred), score, precision, recall, f1))
    conn.commit()
    conn.close()

def save_results_to_csv(labels_test, labels_pred, score, precision, recall, f1):
    df = pd.DataFrame({
        'labels_test': labels_test,
        'labels_pred': labels_pred,
        'score': score,
        'precision': precision,
        'recall': recall,
        'f1': f1
    })
    df.to_csv('resultados.csv', index=False)

def show_previous_results():
    conn = sqlite3.connect('resultados.db')
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='resultados'")
    if c.fetchone() is None:
        print("A tabela 'resultados' não existe no banco de dados.")
    else:
        c.execute('SELECT * FROM resultados')
        rows = c.fetchall()
        for row in rows:
            labels_test, labels_pred, score, precision, recall, f1 = pickle.loads(row[0]), pickle.loads(row[1]), row[2], row[3], row[4], row[5]
            print(f'Score: {score}, Precision: {precision}, Recall: {recall}, F1: {f1}')
    conn.close()

def compare_results():
    conn = sqlite3.connect('resultados.db')
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='resultados'")
    if c.fetchone() is None:
        print("A tabela 'resultados' não existe no banco de dados.")
    else:
        c.execute('SELECT * FROM resultados')
        rows = c.fetchall()
        scores = [row[2] for row in rows]
        plt.plot(scores)
        plt.xlabel('Run')
        plt.ylabel('Score')
        plt.title('Evolution of scores over time')
        plt.show()
    conn.close()

def plot_exoplanets_by_score():
    conn = sqlite3.connect('resultados.db')
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='resultados'")
    if c.fetchone() is None:
        print("A tabela 'resultados' não existe no banco de dados.")
    else:
        c.execute('SELECT * FROM resultados')
        rows = c.fetchall()
        scores = [row[2] for row in rows]
        plt.hist(scores, bins=10)
        plt.xlabel('Score')
        plt.ylabel('Number of Exoplanets')
        plt.title('Number of Exoplanets by Score')
        plt.show()
    conn.close()

def main():
    light_curves, labels = load_dataset()
    light_curves = preprocess_light_curves(light_curves)
    light_curves_train, light_curves_test, labels_train, labels_test = split_data(light_curves, labels)
    clf1, clf2, clf3 = define_classifiers()
    clf1 = tune_hyperparameters(clf1, light_curves_train, labels_train)
    clf2 = tune_hyperparameters(clf2, light_curves_train, labels_train)
    clf3 = train_nn(clf3, light_curves_train, labels_train)
    voting_clf = create_voting_classifier(clf1, clf2, clf3)
    voting_clf.fit(light_curves_train, labels_train)
    labels_test, labels_pred, score, precision, recall, f1 = evaluate_classifier(voting_clf, light_curves_test, labels_test)
    save_results_to_db(labels_test, labels_pred, score, precision, recall, f1)
    save_results_to_csv(labels_test, labels_pred, score, precision, recall, f1)
    
    while True:
        print("1. Show previous results")
        print("2. Compare results")
        print("3. Plot exoplanets by score")
        print("4. Exit")
        option = input("Choose an option: ")
        if option == '1':
            show_previous_results()
        elif option == '2':
            compare_results()
        elif option == '3':
            plot_exoplanets_by_score()
        elif option == '4':
            break

if __name__ == '__main__':
    main()

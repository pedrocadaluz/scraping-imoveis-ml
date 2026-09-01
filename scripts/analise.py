import os
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    r2_score,
    mean_absolute_error,
    mean_squared_error,
    mean_absolute_percentage_error,
)

# ==========================================
# 0. CARREGAMENTO DOS DADOS LIMPOS
# ==========================================
# Caminho relativo à localização deste arquivo (não ao diretório de onde o
# script é chamado), para funcionar tanto rodando pelo terminal quanto pelo
# botão "Run" da IDE.
PASTA_SCRIPTS = os.path.dirname(os.path.abspath(__file__))
PASTA_PROJETO = os.path.dirname(PASTA_SCRIPTS)
CAMINHO_CLEAN = os.path.join(PASTA_PROJETO, 'data', 'clean', 'imoveis_limpos.csv')

print("Carregando dados limpos...")
df = pd.read_csv(CAMINHO_CLEAN)
print(f"Linhas carregadas: {len(df)}")

# ==========================================
# 1. Preparação das variáveis (X e y)
# ==========================================
# Vagas/suítes ausentes no card do site normalmente significam "nenhuma"
df['vagas'] = df['vagas'].fillna(0)
if 'suites' in df.columns:
    df['suites'] = df['suites'].fillna(0)
    features = ['suites', 'metragem', 'vagas']
else:
    features = ['metragem', 'vagas']
# 'quartos' foi removido das features: seu coeficiente era praticamente nulo
# (alta colinearidade com 'metragem') e retirá-lo não muda R²/MAE/RMSE/MAPE
# de forma relevante — só deixa o modelo mais simples (ver README, seção 4).

antes = len(df)
df = df.dropna(subset=features + ['preco'])
print(f"Removidas por falta de {features + ['preco']}: {antes - len(df)}")

X = df[features]
y = df['preco']

# ==========================================
# 2. Split treino/teste
# ==========================================
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# ==========================================
# 3. Treinamento do modelo (Regressão Linear)
# ==========================================
modelo = LinearRegression()
modelo.fit(X_train, y_train)

y_pred_train = modelo.predict(X_train)
y_pred_test = modelo.predict(X_test)

# ==========================================
# 4. Métricas de avaliação
# ==========================================
n_test, p = X_test.shape

r2_treino = r2_score(y_train, y_pred_train)
r2_teste = r2_score(y_test, y_pred_test)
r2_ajustado = 1 - (1 - r2_teste) * (n_test - 1) / (n_test - p - 1)
mae = mean_absolute_error(y_test, y_pred_test)
mse = mean_squared_error(y_test, y_pred_test)
rmse = np.sqrt(mse)
mape = mean_absolute_percentage_error(y_test, y_pred_test)

# R² médio em validação cruzada (5 folds), para checar estabilidade do modelo
cv_scores = cross_val_score(LinearRegression(), X, y, cv=5, scoring='r2')

print("\n===== MÉTRICAS DO MODELO =====")
print(f"R² (treino):          {r2_treino:.4f}")
print(f"R² (teste):           {r2_teste:.4f}")
print(f"R² ajustado (teste):  {r2_ajustado:.4f}")
print(f"R² médio (5-fold CV): {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")
print(f"MAE (teste):          R$ {mae:,.2f}")
print(f"MSE (teste):          {mse:,.2f}")
print(f"RMSE (teste):         R$ {rmse:,.2f}")
print(f"MAPE (teste):         {mape:.2%}")

print("\n===== COEFICIENTES =====")
for nome, coef in zip(features, modelo.coef_):
    print(f"{nome:>10}: {coef:,.2f}")
print(f"{'intercepto':>10}: {modelo.intercept_:,.2f}")

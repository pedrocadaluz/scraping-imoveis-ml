import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Configuração visual para os gráficos ficarem mais bonitos
sns.set_theme(style="whitegrid")

# =====================================================================
# 1. CARREGAMENTO DOS DADOS
# =====================================================================
# Caminho relativo à localização deste arquivo (não ao diretório de onde o
# script é chamado), para funcionar tanto rodando pelo terminal quanto pelo
# botão "Run" da IDE.
PASTA_SCRIPTS = os.path.dirname(os.path.abspath(__file__))
PASTA_PROJETO = os.path.dirname(PASTA_SCRIPTS)
caminho_arquivo = os.path.join(PASTA_PROJETO, 'data', 'raw', 'imoveis_brutos.csv')


print("Carregando os dados...")
df = pd.read_csv(caminho_arquivo)

# =====================================================================
# 2. INSPEÇÃO BÁSICA (O "RG" do seu DataFrame)
# =====================================================================
print("\n--- 1. QUANTIDADE DE LINHAS E COLUNAS ---")
print(f"Linhas: {df.shape[0]} | Colunas: {df.shape[1]}")

print("\n--- 2. COLUNAS ---")
print(list(df.columns))

print("\n--- 3. PRIMEIRAS 5 LINHAS ---")
print(df.head())

print("\n--- 4. TIPOS DE DADOS E INFORMAÇÕES GERAIS ---")
df.info()

print("\n--- 5. VALORES AUSENTES (NULOS) POR COLUNA ---")
resumo_nulos = pd.DataFrame({
    'nulos': df.isnull().sum(),
    'percentual (%)': (df.isnull().mean() * 100).round(2)
})
print(resumo_nulos)

print("\n--- 6. LINHAS DUPLICADAS ---")
print(f"Duplicadas (linha inteira): {df.duplicated().sum()}")

print("\n--- 7. VALORES ÚNICOS POR COLUNA ---")
print(df.nunique())

# =====================================================================
# 3. ANÁLISE DE OUTLIERS
# Conversão numérica feita só em memória, apenas para esta análise —
# não altera nem salva o dataset bruto.
# =====================================================================
print("\n--- 8. ANÁLISE DE OUTLIERS (método IQR) ---")

df_num = df.copy()
df_num['preco'] = pd.to_numeric(df_num['preco'].astype(str).str.replace('.', '', regex=False), errors='coerce')
df_num['quartos'] = df_num['quartos'].astype(str).str.extract(r'(\d+)')[0].astype(float)
df_num['metragem'] = df_num['metragem'].astype(str).str.extract(r'(\d+)')[0].astype(float)
df_num['vagas'] = df_num['vagas'].astype(str).str.extract(r'(\d+)')[0].astype(float)

colunas_numericas = ['preco', 'quartos', 'metragem', 'vagas']

for coluna in colunas_numericas:
    q1 = df_num[coluna].quantile(0.25)
    q3 = df_num[coluna].quantile(0.75)
    iqr = q3 - q1
    limite_inferior = q1 - 1.5 * iqr
    limite_superior = q3 + 1.5 * iqr

    outliers = df_num[(df_num[coluna] < limite_inferior) | (df_num[coluna] > limite_superior)]

    print(f"\n> {coluna}")
    print(f"  Q1={q1:.2f} | Q3={q3:.2f} | IQR={iqr:.2f}")
    print(f"  Limites aceitáveis: [{limite_inferior:.2f}, {limite_superior:.2f}]")
    print(f"  Outliers encontrados: {len(outliers)} ({len(outliers) / len(df_num) * 100:.2f}%)")
    if len(outliers):
        print(df.loc[outliers.index, ['titulo', 'preco', 'quartos', 'metragem', 'vagas']].to_string())

# Boxplots para visualizar os outliers de cada coluna numérica
fig, axes = plt.subplots(1, len(colunas_numericas), figsize=(4 * len(colunas_numericas), 5))
for ax, coluna in zip(axes, colunas_numericas):
    sns.boxplot(y=df_num[coluna].dropna(), ax=ax, color='cyan')
    ax.set_title(coluna)
plt.tight_layout()
plt.show()


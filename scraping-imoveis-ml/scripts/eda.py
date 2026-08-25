import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Configuração visual para os gráficos ficarem mais bonitos
sns.set_theme(style="whitegrid")

# =====================================================================
# 1. CARREGAMENTO DOS DADOS
# =====================================================================
# Usamos o 'r' antes da string para o Windows entender as barras invertidas (\)
caminho_arquivo = r"C:\Ludmila\faculdade\ProjetoCienciasDados5\Regressao_imoveis\data\raw\imoveis_brutos.csv"

print("Carregando os dados...")
df = pd.read_csv(caminho_arquivo)

# =====================================================================
# 2. INSPEÇÃO BÁSICA (O "RG" do seu DataFrame)
# =====================================================================
print("\n--- 1. QUANTIDADE DE LINHAS E COLUNAS ---")
print(f"Linhas: {df.shape[0]} | Colunas: {df.shape[1]}")

print("\n--- 2. PRIMEIRAS 5 LINHAS ---")
display(df.head()) # Use print(df.head()) se não estiver no Jupyter Notebook

print("\n--- 3. INFORMAÇÕES DAS COLUNAS E TIPOS DE DADOS ---")
# O .info() mostra o tipo de dado de cada coluna e se há valores nulos
df.info() 

print("\n--- 4. VALORES AUSENTES (NULOS) POR COLUNA ---")
print(df.isnull().sum())

# =====================================================================
# 3. PREPARAÇÃO RÁPIDA PARA ANÁLISE NUMÉRICA
# Como é o dado bruto, precisamos converter texto para número para usar o .describe()
# =====================================================================
print("\n--- CONVERTENDO DADOS PARA ANÁLISE NUMÉRICA ---")

df_eda = df.copy() # Criamos uma cópia para não alterar o original carregado

# Limpeza básica (igual você fez antes) para permitir a matemática
df_eda['preco'] = df_eda['preco'].astype(str).str.replace('.', '', regex=False)
df_eda['preco'] = pd.to_numeric(df_eda['preco'], errors='coerce')

df_eda['quartos'] = df_eda['quartos'].astype(str).str.extract(r'(\d+)')[0].astype(float)
df_eda['metragem'] = df_eda['metragem'].astype(str).str.extract(r'(\d+)')[0].astype(float)
df_eda['vagas'] = df_eda['vagas'].astype(str).str.extract(r'(\d+)')[0].astype(float)

# =====================================================================
# 4. ESTATÍSTICA DESCRITIVA
# =====================================================================
print("\n--- 5. RESUMO ESTATÍSTICO DAS COLUNAS NUMÉRICAS ---")
# O .describe() traz média, desvio padrão, valores mínimos, máximos e quartis
display(df_eda.describe()) # Use print() se não estiver no Jupyter

# =====================================================================
# 5. ANÁLISE VISUAL (GRÁFICOS)
# =====================================================================
print("\n--- 6. GERANDO GRÁFICOS DE ANÁLISE ---")

# Criando uma figura com 2 gráficos lado a lado
fig, axes = plt.subplots(1, 2, figsize=(15, 5))

# Gráfico 1: Histograma (Distribuição dos Preços)
# Ajuda a ver onde está a maior concentração de preços
sns.histplot(df_eda['preco'].dropna(), bins=30, kde=True, color='blue', ax=axes[0])
axes[0].set_title('Distribuição de Preços de Aluguel')
axes[0].set_xlabel('Preço (R$)')
axes[0].set_ylabel('Quantidade de Imóveis')

# Gráfico 2: Boxplot (Identificação de Outliers/Valores Discrepantes)
# Ajuda a ver se há aluguéis com preços absurdamente altos fora do padrão
sns.boxplot(x=df_eda['preco'].dropna(), color='cyan', ax=axes[1])
axes[1].set_title('Boxplot de Preços (Visão de Outliers)')
axes[1].set_xlabel('Preço (R$)')

plt.tight_layout()
plt.show()

# =====================================================================
# 6. ANÁLISE DE CORRELAÇÃO E AGRUPAMENTOS
# =====================================================================
print("\n--- 7. PREÇO MÉDIO POR QUANTIDADE DE QUARTOS ---")
# O .groupby() é perfeito para responder perguntas de negócio
preco_por_quarto = df_eda.groupby('quartos')['preco'].mean().round(2)
print(preco_por_quarto)

# Gráfico de dispersão: Metragem vs Preço (Existe relação?)
plt.figure(figsize=(8, 5))
sns.scatterplot(data=df_eda, x='metragem', y='preco', hue='quartos', palette='viridis', alpha=0.7)
plt.title('Relação entre Metragem e Preço de Aluguel')
plt.xlabel('Metragem (m²)')
plt.ylabel('Preço (R$)')
plt.show()
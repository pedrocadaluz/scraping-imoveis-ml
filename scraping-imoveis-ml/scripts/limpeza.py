import os
import pandas as pd

# ==========================================
# 0. CARREGAMENTO DOS DADOS BRUTOS
# ==========================================
CAMINHO_BRUTOS = 'data/raw/imoveis_brutos.csv'
CAMINHO_SUBTITULOS = 'data/raw/subtitulos.csv'
CAMINHO_CLEAN = 'data/clean/imoveis_limpos.csv'

print("Iniciando a limpeza dos dados...")
df = pd.read_csv(CAMINHO_BRUTOS)
print(f"Linhas carregadas: {len(df)}")

# Versões antigas da raspagem salvaram a coluna de link como 'href'
if 'link' not in df.columns and 'href' in df.columns:
    df = df.rename(columns={'href': 'link'})

# ==========================================
# 1. Remover "lançamentos" (empreendimento inteiro, não uma unidade)
# ==========================================

eh_lancamento = df['link'].str.contains(r'/imovel/lancamento-', case=False, na=False)
sem_quartos_e_vagas = df['quartos'].isna() & df['vagas'].isna()
remover_lancamento = eh_lancamento | sem_quartos_e_vagas
print(f"Removidos por serem lançamento/empreendimento (não unidade única): {remover_lancamento.sum()}")
df = df[~remover_lancamento].copy()

# ==========================================
# 2. Remover imóveis vendidos com ÁGIO
# ==========================================

if os.path.exists(CAMINHO_SUBTITULOS):
    df_subtitulos = pd.read_csv(CAMINHO_SUBTITULOS)
    df = df.merge(df_subtitulos, on='link', how='left')
else:
    df['subtitulo'] = pd.NA
    print(f"Aviso: '{CAMINHO_SUBTITULOS}' não encontrado — checagem de ágio via "
          "subtítulo pulada (rode scraping_subtitulo.py para habilitá-la).")

eh_agio = (
    df['subtitulo'].astype(str).str.contains('ágio', case=False, na=False)
    | df['titulo'].astype(str).str.contains('ágio', case=False, na=False)
)
print(f"Removidos por venda com ágio: {eh_agio.sum()}")
df = df[~eh_agio].copy()
df = df.drop(columns=['subtitulo'])

# ==========================================
# 3. Conversão de tipos (texto -> número)
# ==========================================
def extrair_inteiro(serie):
    return serie.astype(str).str.extract(r'(\d+)')[0].astype('Int64')

df['quartos'] = extrair_inteiro(df['quartos'])
df['metragem'] = extrair_inteiro(df['metragem'])
df['vagas'] = extrair_inteiro(df['vagas'])
if 'suites' in df.columns:
    df['suites'] = extrair_inteiro(df['suites'])

df['preco'] = df['preco'].astype(str).str.replace('.', '', regex=False)
df['preco'] = pd.to_numeric(df['preco'], errors='coerce')

# Descarta linhas sem preço ou metragem numéricos válidos: sem essas duas
# variáveis não é possível usar o registro nem para EDA nem para o modelo.
antes = len(df)
df = df.dropna(subset=['preco', 'metragem']).copy()
print(f"Removidos por preço/metragem não numéricos: {antes - len(df)}")

# ==========================================
# 4. Remoção de outliers reais (método IQR) em preço, metragem e preço/m²
# ==========================================

df['preco_m2'] = df['preco'] / df['metragem']

def limites_iqr(serie):
    q1, q3 = serie.quantile(0.25), serie.quantile(0.75)
    iqr = q3 - q1
    return q1 - 1.5 * iqr, q3 + 1.5 * iqr

for coluna in ['preco', 'metragem', 'preco_m2']:
    inferior, superior = limites_iqr(df[coluna])
    fora_do_padrao = (df[coluna] < inferior) | (df[coluna] > superior)
    print(f"Outliers removidos em '{coluna}': {fora_do_padrao.sum()} "
          f"(limites aceitáveis: [{inferior:.2f}, {superior:.2f}])")
    df = df[~fora_do_padrao].copy()

df = df.drop(columns=['preco_m2'])

# Resetar o index para organizar as linhas
df = df.reset_index(drop=True)

# ==========================================
# 5. Salvamento do DataFrame LIMPO
# ==========================================
os.makedirs('data/clean', exist_ok=True)
df.to_csv(CAMINHO_CLEAN, index=False, encoding='utf-8')

print(f"\n--> Dados LIMPOS salvos em: {CAMINHO_CLEAN} ({len(df)} imóveis)")
print("Visualização dos dados limpos:")
print(df.head(10))

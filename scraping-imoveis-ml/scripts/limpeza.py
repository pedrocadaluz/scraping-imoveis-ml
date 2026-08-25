
# ==========================================
# 6. Limpeza dos Dados
# ==========================================
print("Iniciando a limpeza dos dados...")

# 1. Limpar 'titulo': Manter APENAS linhas que contenham indicativos de endereço
indicativos_endereco = 'Rua|Avenida|Av\.|Lote|Quadra|Qd|Residencial|Edifício|Condomínio|Praça|SQ'
df = df[df['titulo'].str.contains(indicativos_endereco, case=False, na=False)].copy()

# 2. Limpar 'quartos'
df['quartos'] = df['quartos'].str.extract(r'(\d+)')[0].astype('Int64')

# 3. Limpar 'metragem'
df['metragem'] = df['metragem'].astype(str).str.extract(r'(\d+)')[0].astype('Int64')

# 4. Limpar 'vagas'
df['vagas'] = df['vagas'].astype(str).str.extract(r'(\d+)')[0].astype('Int64')

# 5. Limpar 'preco'
df['preco'] = df['preco'].astype(str).str.replace('.', '', regex=False)
df['preco'] = pd.to_numeric(df['preco'], errors='coerce')

# Resetar o index para organizar as linhas
df = df.reset_index(drop=True)

# ==========================================
# 7. Salvamento do DataFrame LIMPO
# ==========================================
caminho_clean = 'data/clean/imoveis_limpos.csv'
df.to_csv(caminho_clean, index=False, encoding='utf-8')

print(f"--> Dados LIMPOS salvos em: {caminho_clean}\n")
print("Visualização dos dados limpos:")
print(df.head(10))
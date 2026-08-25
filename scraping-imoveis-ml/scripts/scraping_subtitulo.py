import os
import pandas as pd
from time import sleep

# Libs para Web Scraping
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==========================================
# 0. CONFIGURAÇÕES
# ==========================================
# Esse script complementa o webScraping.py: ele visita a página de CADA
# imóvel (não só o card da listagem) para pegar o subtítulo, onde aparecem
# indicações tipo "Venda de Ágio ou quitado!" que não existem no card.
#
# Como isso significa uma requisição a mais por imóvel, ele roda em LOTES
# e é retomável: cada execução coleta até QUANTIDADE_POR_EXECUCAO imóveis
# que ainda não têm subtítulo salvo, e você pode rodar de novo depois para
# continuar de onde parou, até coletar todos.
CAMINHO_BRUTOS = 'data/raw/imoveis_brutos.csv'
CAMINHO_SUBTITULOS = 'data/raw/subtitulos.csv'
CAMINHO_FINAL = 'data/raw/imoveis_brutos_completo.csv'
QUANTIDADE_POR_EXECUCAO = 100

os.makedirs('data/raw', exist_ok=True)

options = webdriver.ChromeOptions()
options.add_argument("--ignore-certificate-errors")
options.add_argument("--disable-blink-features=AutomationControlled")

driver = webdriver.Chrome(options=options)
driver.delete_all_cookies()
wait = WebDriverWait(driver, 10)

# ==========================================
# 1. Carrega os imóveis já raspados e o progresso já feito
# ==========================================
df_imoveis = pd.read_csv(CAMINHO_BRUTOS)

if 'link' not in df_imoveis.columns:
    raise SystemExit(
        f"'{CAMINHO_BRUTOS}' não tem a coluna 'link'. Rode o webScraping.py "
        "novamente (com a versão atual) para gerar esse arquivo com os links."
    )

if os.path.exists(CAMINHO_SUBTITULOS):
    df_subtitulos = pd.read_csv(CAMINHO_SUBTITULOS)
else:
    df_subtitulos = pd.DataFrame(columns=['link', 'subtitulo'])

links_unicos = df_imoveis['link'].dropna().unique()
links_ja_feitos = set(df_subtitulos['link'])
pendentes = [link for link in links_unicos if link not in links_ja_feitos]

print(f"Total de imóveis únicos: {len(links_unicos)}")
print(f"Já coletados: {len(links_ja_feitos)}")
print(f"Pendentes: {len(pendentes)}")

lote = pendentes[:QUANTIDADE_POR_EXECUCAO]
print(f"Coletando subtítulo de {len(lote)} imóveis nesta execução...\n")

# ==========================================
# 2. Visita cada imóvel do lote e extrai o subtítulo
# ==========================================
resultados = []
for i, link in enumerate(lote, start=1):
    print(f"[{i}/{len(lote)}] {link}")
    try:
        driver.get(link)
        wait.until(EC.presence_of_element_located((By.XPATH, "//h1[@itemprop='name']")))

        try:
            subtitulo = driver.find_element(By.XPATH, "//h1[@itemprop='name']/following-sibling::span[1]").text
        except Exception:
            subtitulo = None

        resultados.append({'link': link, 'subtitulo': subtitulo})
    except Exception as e:
        print(f"  Falhou nesse imóvel, seguindo para o próximo: {e}")

    sleep(4)  # pausa maior que na listagem: página de imóvel carrega mais coisa e é mais sensível a bloqueio

driver.quit()

# ==========================================
# 3. Salva o progresso (acumulando com o que já existia)
# ==========================================
df_novo = pd.DataFrame(resultados, columns=['link', 'subtitulo'])
df_subtitulos = pd.concat([df_subtitulos, df_novo], ignore_index=True)
df_subtitulos = df_subtitulos.drop_duplicates(subset=['link'], keep='first')
df_subtitulos.to_csv(CAMINHO_SUBTITULOS, index=False, encoding='utf-8')

total_coletado = df_subtitulos['link'].nunique()
print(f"\n--> Progresso salvo em: {CAMINHO_SUBTITULOS}")
print(f"--> Total coletado até agora: {total_coletado} / {len(links_unicos)}")

# ==========================================
# 4. Quando tudo estiver coletado, junta os dois DataFrames em um só
# ==========================================
if total_coletado >= len(links_unicos):
    print("\nTodos os subtítulos foram coletados! Fazendo o merge com os dados brutos...")
    df_final = df_imoveis.merge(df_subtitulos, on='link', how='left')
    df_final.to_csv(CAMINHO_FINAL, index=False, encoding='utf-8')
    print(f"--> Dataset combinado (raspagem + subtítulo) salvo em: {CAMINHO_FINAL}")
else:
    print("\nAinda faltam imóveis. Rode este script de novo para continuar de onde parou.")

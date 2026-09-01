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
# Script único: raspa a listagem (título, preço, quartos, suítes, metragem,
# vagas, link) e, na sequência, visita a página de CADA imóvel encontrado
# para pegar o subtítulo (onde aparecem indicações tipo "Venda de Ágio ou
# quitado!" que não existem no card da listagem). Tudo em uma única execução.
CAMINHO_BRUTOS = 'data/raw/imoveis_brutos.csv'
CAMINHO_SUBTITULOS = 'data/raw/subtitulos.csv'
CAMINHO_FINAL = 'data/raw/imoveis_brutos_completo.csv'
URL = 'https://www.dfimoveis.com.br/venda/df/taguatinga/apartamento'

os.makedirs('data/raw', exist_ok=True)
os.makedirs('data/clean', exist_ok=True)

options = webdriver.ChromeOptions()
options.add_argument("--ignore-certificate-errors")
options.add_argument("--disable-blink-features=AutomationControlled")

driver = webdriver.Chrome(options=options)
driver.delete_all_cookies()
wait = WebDriverWait(driver, 10)

# ==========================================
# 1. Raspagem da listagem
# ==========================================
print("Acessando a página de resultados...")
driver.get(URL)

lst_imoveis = []
pagina = 1

while True:
    print(f"Coletando dados da página {pagina}...")
    if pagina > 1:
        # Navega direto para a página via parâmetro de URL: clicar no botão "Próximo"
        # via JS não avança a listagem de forma confiável neste site.
        driver.get(f"{URL}?pagina={pagina}")
    sleep(3)  # Pausa para garantir que a página carregou

    try:
        wait.until(EC.presence_of_element_located((By.ID, "resultadoDaBuscaDeImoveis")))
        elementos = driver.find_elements(By.XPATH, "//div[@id='resultadoDaBuscaDeImoveis']//a[contains(@href, '/imovel/')]")
    except Exception:
        print("Fim dos resultados ou a estrutura dos cards também mudou.")
        break

    if not elementos:
        print("Nenhum anúncio encontrado nesta página.")
        break

    for elem in elementos:
        try:
            titulo = elem.find_element(By.XPATH, ".//h2[@itemprop='name']").text
            preco = elem.find_element(By.CLASS_NAME, 'body-large').text
            link = elem.get_attribute('href')

            try:
                quartos = elem.find_element(By.XPATH, ".//div[contains(text(), 'Quarto') and contains(@class, 'rounded-pill')]").text
            except Exception:
                quartos = None

            try:
                suites = elem.find_element(By.XPATH, ".//div[contains(text(), 'Suíte') and contains(@class, 'rounded-pill')]").text
            except Exception:
                suites = None

            try:
                metragem = elem.find_element(By.XPATH, ".//div[contains(@class, 'web-view') and contains(text(), 'm²')]").text
            except Exception:
                metragem = None

            try:
                vagas = elem.find_element(By.XPATH, ".//div[contains(@class, 'rounded-pill') and (contains(text(), 'Vaga') or contains(text(), 'Vagas'))]").text
            except Exception:
                vagas = None

            lst_imoveis.append({
                'titulo': titulo,
                'preco': preco,
                'quartos': quartos,
                'suites': suites,
                'metragem': metragem,
                'vagas': vagas,
                'link': link
            })

        except Exception:
            continue  # Se der erro em um card específico, pula para o próximo

    try:
        botao_proximo = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'span.btn.next')))
        if "disabled" in botao_proximo.get_attribute("class"):
            print("Última página alcançada.")
            break
        pagina += 1
    except Exception:
        print("Não há mais páginas ou ocorreu um erro na paginação.")
        break

df_imoveis = pd.DataFrame(lst_imoveis)
df_imoveis = df_imoveis.drop_duplicates(subset=['titulo', 'preco', 'metragem'], keep='first')

df_imoveis.to_csv(CAMINHO_BRUTOS, index=False, encoding='utf-8')
print(f"\nColeta da listagem finalizada! {len(df_imoveis)} imóveis únicos coletados.")
print(f"--> Dados BRUTOS salvos em: {CAMINHO_BRUTOS}\n")

# ==========================================
# 2. Visita cada imóvel e extrai o subtítulo
# ==========================================
links_unicos = df_imoveis['link'].dropna().unique()
print(f"Coletando subtítulo de {len(links_unicos)} imóveis...\n")

resultados_subtitulo = []
for i, link in enumerate(links_unicos, start=1):
    print(f"[{i}/{len(links_unicos)}] {link}")
    try:
        driver.get(link)
        wait.until(EC.presence_of_element_located((By.XPATH, "//h1[@itemprop='name']")))

        try:
            subtitulo = driver.find_element(By.XPATH, "//h1[@itemprop='name']/following-sibling::span[1]").text
        except Exception:
            subtitulo = None

        resultados_subtitulo.append({'link': link, 'subtitulo': subtitulo})
    except Exception as e:
        print(f"  Falhou nesse imóvel, seguindo para o próximo: {e}")

    sleep(4)  # pausa maior que na listagem: página de imóvel carrega mais coisa e é mais sensível a bloqueio

driver.quit()

df_subtitulos = pd.DataFrame(resultados_subtitulo, columns=['link', 'subtitulo'])
df_subtitulos = df_subtitulos.drop_duplicates(subset=['link'], keep='first')
df_subtitulos.to_csv(CAMINHO_SUBTITULOS, index=False, encoding='utf-8')
print(f"\n--> Subtítulos salvos em: {CAMINHO_SUBTITULOS}")

# ==========================================
# 3. Junta os dois DataFrames em um só
# ==========================================
df_final = df_imoveis.merge(df_subtitulos, on='link', how='left')
df_final.to_csv(CAMINHO_FINAL, index=False, encoding='utf-8')
print(f"--> Dataset combinado (raspagem + subtítulo) salvo em: {CAMINHO_FINAL}")

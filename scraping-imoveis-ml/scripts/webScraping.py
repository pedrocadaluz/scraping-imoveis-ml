import os
import pandas as pd
from time import sleep

# Libs para Web Scraping
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==========================================
# 0. CRIANDO AS PASTAS DE DESTINO
# ==========================================
os.makedirs('data/raw', exist_ok=True)
os.makedirs('data/clean', exist_ok=True)

# ==========================================
# 1. Configurações do Navegador
# ==========================================
options = webdriver.ChromeOptions()
options.add_argument("--ignore-certificate-errors")
options.add_argument("--disable-blink-features=AutomationControlled")

driver = webdriver.Chrome(options=options)
driver.delete_all_cookies()

# ==========================================
# 2. DEFINA A URL DA SUA BUSCA AQUI
# ==========================================
url = 'https://www.dfimoveis.com.br/venda/df/taguatinga/apartamento'

print("Acessando a página de resultados...")
driver.get(url)
wait = WebDriverWait(driver, 10)

# ==========================================
# 3. Raspagem dos dados
# ==========================================
lst_imoveis = []
pagina = 1

while True:
    print(f"Coletando dados da página {pagina}...")
    if pagina > 1:
        # Navega direto para a página via parâmetro de URL: clicar no botão "Próximo"
        # via JS não avança a listagem de forma confiável neste site.
        driver.get(f"{url}?pagina={pagina}")
    sleep(3) # Pausa para garantir que a página carregou
    
    try:
        # Aguarda os resultados aparecerem na tela
        wait.until(EC.presence_of_element_located((By.ID, "resultadoDaBuscaDeImoveis")))
        elementos = driver.find_elements(By.XPATH, "//div[@id='resultadoDaBuscaDeImoveis']//a[contains(@href, '/imovel/')]")
    except Exception as e:
        print("Fim dos resultados ou a estrutura dos cards também mudou.")
        break

    if not elementos:
        print("Nenhum anúncio encontrado nesta página.")
        break

    # Extraindo as informações de cada card de imóvel
    for elem in elementos:
        try:
            titulo = elem.find_element(By.XPATH, ".//h2[@itemprop='name']").text
            preco = elem.find_element(By.CLASS_NAME, 'body-large').text
            link = elem.get_attribute('href')

            # Quartos
            try:
                quartos = elem.find_element(By.XPATH, ".//div[contains(text(), 'Quarto') and contains(@class, 'rounded-pill')]").text
            except: quartos = None

            # Suítes (campo separado de quartos, o site já mostra os dois como badges distintos)
            try:
                suites = elem.find_element(By.XPATH, ".//div[contains(text(), 'Suíte') and contains(@class, 'rounded-pill')]").text
            except: suites = None

            # Metragem
            try:
                metragem = elem.find_element(By.XPATH, ".//div[contains(@class, 'web-view') and contains(text(), 'm²')]").text
            except: metragem = None

            # Vagas
            try:
                vagas = elem.find_element(By.XPATH, ".//div[contains(@class, 'rounded-pill') and (contains(text(), 'Vaga') or contains(text(), 'Vagas'))]").text
            except: vagas = None

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
            continue # Se der erro em um card específico, pula para o próximo

    # 4. Verifica se existe próxima página
    try:
        botao_proximo = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'span.btn.next')))

        # Verifica se o botão "Próximo" está desabilitado (última página)
        if "disabled" in botao_proximo.get_attribute("class"):
            print("Última página alcançada.")
            break

        pagina += 1
    except Exception:
        print("Não há mais páginas ou ocorreu um erro na paginação.")
        break

driver.quit()

# ==========================================
# 5. Criação e Salvamento do DataFrame BRUTO
# ==========================================
df = pd.DataFrame(lst_imoveis)
df = df.drop_duplicates(subset=['titulo', 'preco', 'metragem'], keep='first')

# Salvando os dados brutos
caminho_raw = 'data/raw/imoveis_brutos.csv'
df.to_csv(caminho_raw, index=False, encoding='utf-8')
print(f"\nColeta finalizada! {len(df)} imóveis únicos coletados.")
print(f"--> Dados BRUTOS salvos em: {caminho_raw}\n")
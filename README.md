# Documentação Técnica — Pipeline de Dados para Análise do Mercado Imobiliário (Apartamentos)

## Como rodar (uv)

Este projeto usa [uv](https://github.com/astral-sh/uv) para gerenciar dependências (`pyproject.toml` + `uv.lock`) em vez de `pip`/`requirements.txt`.

**Primeira vez (nunca usou uv):**

1. Instale o uv:
   - Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
   - macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
2. Na raiz do projeto (`scraping-imoveis-ml/`), rode:
   ```
   uv sync
   ```
   Isso cria a `.venv` local e instala Python (se necessário) e todas as dependências travadas no `uv.lock`.
3. Rode qualquer script com `uv run`, sem precisar ativar a venv manualmente:
   ```
   uv run scripts/scraping.py
   uv run scripts/limpeza.py
   uv run scripts/eda.py
   ```

**Já tem o projeto, só quer sincronizar as bibliotecas (ex.: após um `git pull` que mudou o `uv.lock`):**

```
uv sync
```

## Visão Geral do Projeto

Este documento descreve o pipeline de dados construído para coletar, analisar e preparar informações sobre apartamentos à venda no portal DF Imóveis (região de Taguatinga/DF), com o objetivo de alimentar um modelo de regressão para estimativa de preços. O pipeline está dividido em três fases: **Web Scraping**, **Análise Exploratória de Dados (EDA)** e **Limpeza de Dados / Feature Engineering**.

> Este README também funciona como um log técnico do projeto: além de descrever o processo, registra as dificuldades reais encontradas e como foram tratadas, para que decisões não se percam ao longo do desenvolvimento.

---

## 1. Web Scraping

### 1.1 Objetivo

Coletar de forma automatizada os anúncios de apartamentos, extraindo atributos estruturais do imóvel (título/endereço, preço, quartos, suítes, metragem, vagas de garagem e link do anúncio) para formar a base bruta de dados (`data/raw/imoveis_brutos.csv`).

### 1.2 Abordagem Técnica (`webScraping.py`)

- **Selenium WebDriver** para renderizar as páginas de listagem, já que o conteúdo é carregado via JavaScript e não está disponível em uma requisição HTTP simples.
- Navegação por paginação via parâmetro de URL (`?pagina=N`) — abandonamos o clique programático no botão "Próximo" após constatar que ele não avançava a listagem de forma confiável.
- Extração campo a campo via **XPath**/seletores de classe, com tratamento de exceção individual por campo (`try/except`), evitando que a ausência de um único atributo (ex.: imóvel sem suíte) descartasse o card inteiro.
- Deduplicação por `título + preço + metragem`, evitando anúncios repetidos entre execuções.

### 1.3 Principal Desafio: Mapeamento dos Campos e Falta de Padronização

A maior dificuldade desta fase não foi de automação, e sim de **mapeamento semântico da página**: descobrir com precisão quais elementos do HTML correspondiam a quais atributos do imóvel.

- **Badges intercambiáveis**: quartos, suítes e vagas são renderizados com a mesma classe visual (`rounded-pill`), diferenciando-se apenas pelo texto interno (ex.: "3 Quartos", "1 Suíte", "2 Vagas"). Foi necessário usar XPath com `contains(text(), ...)` para cada termo, em vez de depender de posição ou classe.
- **Atributos opcionais**: nem todo imóvel exibe suíte ou vaga — quando ausente, o elemento simplesmente não existe no DOM, exigindo tratamento explícito por campo (`None` quando não encontrado).
- **Inconsistência entre anúncios de diferentes imobiliárias**: pequenas variações de formatação exigiram diversas iterações até chegar a seletores estáveis e generalizáveis.

Esse trabalho de engenharia reversa da página consumiu mais esforço do que a própria lógica de navegação/paginação.

### 1.4 Segunda Rodada de Scraping: o Campo "Subtítulo" (`scraping_subtitulo.py`)

Durante a fase de EDA (ver seção 2.4), identificamos que o card da listagem **não continha uma informação crítica**: se o imóvel estava sendo vendido com **ágio**. Essa informação só existe na página individual do imóvel, em um subtítulo do tipo *"Venda de Ágio ou quitado!"*.

Isso exigiu uma segunda rodada de coleta, complementar à primeira:

- Visita à página de cada imóvel individualmente (uma requisição a mais por item, ao invés de apenas ler o card da listagem).
- Execução **em lotes retomáveis** (`QUANTIDADE_POR_EXECUCAO`): cada rodada coleta apenas os links ainda pendentes (comparando com `data/raw/subtitulos.csv`), permitindo interromper e continuar sem perder progresso — importante dado o volume de requisições e o risco de bloqueio pelo site.
- Pausa maior entre requisições (4s, contra 3s na listagem), já que a página individual carrega mais conteúdo e se mostrou mais sensível a bloqueio.
- Ao final, merge dos subtítulos com o dataset bruto original (`data/raw/imoveis_brutos_completo.csv`), usando `link` como chave.

Esse é um exemplo direto de como a fase de **EDA retroalimentou a fase de Scraping**: um outlier mal compreendido revelou a ausência de um campo relevante na coleta original.

---

## 2. Análise Exploratória de Dados (EDA)

### 2.1 Objetivo

Entender a distribuição das variáveis coletadas, avaliar a qualidade dos dados (nulos, duplicidade, tipos) e investigar a presença de **outliers** — sem alterar ou descartar dados do arquivo bruto nesta etapa (as conversões numéricas em `eda.py` são feitas só em memória, exclusivamente para análise).

### 2.2 Etapas Realizadas (`eda.py`)

- Inspeção estrutural: shape, tipos de dados, nulos por coluna, valores únicos, duplicidade.
- Conversão temporária de `preco`, `quartos`, `metragem` e `vagas` para numérico (regex + `pd.to_numeric`), apenas para viabilizar a análise.
- Identificação de outliers pelo **método IQR** (Q1, Q3, limites em `Q1 - 1.5×IQR` / `Q3 + 1.5×IQR`), com boxplots de apoio para cada variável numérica.

### 2.3 Abordagem Criteriosa com Outliers

Princípio adotado: **outlier estatístico não é sinônimo de dado inválido**. Em vez de remover automaticamente todo registro fora dos limites do IQR, cada outlier foi investigado individualmente — voltando ao anúncio original — para identificar a causa, entre duas hipóteses:

1. **Erro de digitação/cadastro da plataforma** → candidato à correção manual ou remoção.
2. **Comportamento real, porém fora do padrão do mercado** → dado legítimo, mantido no dataset.

### 2.4 Caso Real 1 — Erro de Digitação: "62 Quartos"

Durante a checagem manual dos outliers de `quartos`, encontramos o anúncio:

> [Apartamento 4 quartos - Taguatinga Norte](https://www.dfimoveis.com.br/imovel/apartamento-4-quartos-venda-taguatinga-norte-taguatinga-df-st-area-especiais-setor-c-norte-1402445)

O card constava **62 quartos**, um valor claramente incompatível com um apartamento residencial. Ao investigar o anúncio original, constatou-se que se tratava, na realidade, de um **apartamento de 3 quartos com suíte** no Residencial Esplanada — Taguatinga Norte, muito provavelmente um erro de digitação do próprio anunciante na plataforma. Esse registro foi **tratado manualmente**, dado que a discrepância era grande demais para ser corrigida por uma regra genérica.

### 2.5 Caso Real 2 — Comportamento Real do Mercado: Imóveis com "Ágio"

Também durante a análise de `preco`, identificamos outliers fortemente distorcidos (muito acima do limite superior do IQR) que, ao contrário do caso anterior, **não eram erro de cadastro**: tratavam-se de apartamentos anunciados com cobrança de **ágio** — um valor adicional embutido no preço de venda (tipicamente ligado à diferença entre o saldo devedor financiado e o valor de mercado do imóvel).

Esse achado é relevante porque o "preço com ágio" **mascara o preço real de mercado**, distorcendo a comparação entre imóveis de características semelhantes. Como essa informação não estava disponível no card da listagem, a investigação desse outlier motivou diretamente a criação do scraper de subtítulo descrito na seção 1.4 — permitindo, nas próximas etapas, identificar e tratar separadamente os imóveis vendidos com ágio em vez de simplesmente excluí-los como ruído estatístico.

Esses dois casos ilustram por que a investigação manual dos outliers é indispensável: uma exclusão automática por IQR trataria "62 quartos" e "preço com ágio" da mesma forma, quando na verdade um é erro de cadastro e o outro é uma característica real (porém não diretamente comparável) do mercado.

### 2.6 Caso Real 3 — Outlier Estrutural: "Empreendimento Inteiro" Anunciado como Apartamento

Um terceiro padrão de outlier apareceu nas colunas `preco` e `metragem`: alguns anúncios tinham metragem em **faixa** (ex.: "31 a 38 m²"), preço como **"A partir de ..."** ou **"Sob Consulta"**, e vinham sem `quartos`/`vagas` preenchidos. Investigando os links (todos contendo `/imovel/lancamento-` na URL), constatamos que **não são um apartamento específico**: são o **empreendimento/prédio inteiro** sendo anunciado, com várias tipologias e unidades pequenas disponíveis — semelhante ao caso de uma casa grande dividida em vários apartamentos, mas comercializada como um imóvel só.

Diferente dos casos anteriores, aqui a causa não é erro de digitação nem uma característica válida de um imóvel individual: é uma **unidade de análise diferente** (empreendimento vs. apartamento) se misturando ao dataset, e por isso precisa ser removida antes de qualquer análise de preço/m² ou modelagem — mantê-la distorceria tanto `preco` quanto `metragem` para o que deveria representar uma única unidade residencial.

---

## 3. Limpeza de Dados e Feature Engineering

### 3.1 Objetivo

Transformar o dataset bruto — com campos textuais, heterogêneos e por vezes inconsistentes — em uma base estruturada e corretamente tipada, pronta para uso em modelos estatísticos e de machine learning (`limpeza.py`).

`limpeza.py` agora roda de forma independente (lê `data/raw/imoveis_brutos.csv` diretamente, em vez de depender de um `df` já em memória vindo do `webScraping.py`), o que facilita reexecutar só a limpeza depois de ajustes. O pipeline aplica, nesta ordem, os passos abaixo.

### 3.2 Remoção de Registros que Não São uma Unidade Válida

- **Empreendimento inteiro ("lançamento")**: registros cujo link contém `/imovel/lancamento-`, ou que estejam sem `quartos` **e** `vagas` preenchidos (o mesmo padrão descrito no caso real da seção 2.6), são removidos antes de qualquer conversão de tipo — eles não representam uma unidade específica.
- **Venda com ágio**: se `data/raw/subtitulos.csv` já existir (gerado por `scraping_subtitulo.py`), é feito o merge por `link` e removemos os registros cujo `subtitulo` (ou, como reforço, o próprio `titulo`) contenha "ágio", eliminando o preço mascarado descrito na seção 2.5. Enquanto essa coleta não estiver completa para todos os imóveis, o script apenas avisa no console e segue sem essa checagem — a coluna some do dataset final, então não há risco de vazar um `subtitulo` incompleto para o modelo.
> **Nota sobre erros de digitação (ex.: "62 quartos", seção 2.4)**: esse tipo de caso foi identificado e corrigido manualmente durante a investigação da EDA, mas não entrou como uma regra automática dentro de `limpeza.py` — é uma correção pontual em um registro específico, não um padrão a ser tratado programaticamente. Se aparecer de novo em uma rodada futura de coleta, precisa ser reinvestigado (ver seção 2.3).

> **Nota sobre `titulo`**: a versão anterior deste script filtrava linhas sem indicativo de endereço no título (ex.: "Rua", "Quadra"). Ao rodar contra dados mais recentes, percebemos que o card de listagem do site deixou de exibir endereço no título de anúncios de revenda normais (agora mostra selos como "IMÓVEL SEGURO" ou "SUPER DESTAQUE") — só os "lançamentos" ainda trazem texto de endereço no título. Esse filtro sozinho descartaria praticamente todo o dataset de revenda, então ele foi removido: a remoção de lançamentos (acima) já cobre o problema que ele tentava resolver.

### 3.3 Padronização e Transformação de Tipos

Os campos numéricos chegam da raspagem como texto, cada um com sua própria máscara de formatação:

- **`preco`**: remoção do separador de milhar (`.`) do formato brasileiro (ex.: `"1.250.000"` → `1250000`) e conversão via `pd.to_numeric` (com `errors='coerce'`, atribuindo `NaN` a valores não conversíveis em vez de interromper o pipeline). Linhas sem `preco` ou `metragem` numéricos válidos após a conversão são descartadas, já que o registro não é utilizável nem em EDA nem no modelo.
- **`quartos`, `metragem`, `vagas`** (e `suites`, quando a coluna existir): extração do componente numérico via regex (`\d+`) e conversão para `Int64` (inteiro anulável do pandas), preservando `NaN` quando o dado não existia, sem forçar conversão para `float`.

### 3.4 Caso Prático: Feature Engineering na Coluna `vagas`

A coluna de **vagas de garagem** chegava da raspagem como uma string livre no formato `"3 Vagas"` (ou `"1 Vaga"`) — adequada para exibição no site, mas inutilizável diretamente em cálculos estatísticos ou como entrada de modelo.

Tratamento aplicado:

1. Extração do componente numérico da string via regex (`str.extract(r'(\d+)')`).
2. Conversão para `Int64`, preservando `NaN` para imóveis sem vaga informada (elemento ausente já na fase de scraping).

Com isso, `vagas` deixou de ser um atributo textual e passou a ser uma **feature numérica íntegra**, apta para análises de correlação, agregações estatísticas e uso como variável preditiva no modelo de regressão de preços — mesmo padrão aplicado a `quartos` e `metragem`.

### 3.5 Remoção Efetiva de Outliers (Método IQR)

Diferente do `eda.py`, que só identifica e visualiza outliers sem alterar o dataset, o `limpeza.py` **remove de fato** os registros fora do padrão, usando o mesmo método IQR (`Q1 - 1.5×IQR` / `Q3 + 1.5×IQR`), aplicado a três variáveis:

- `preco`
- `metragem`
- `preco_m2` (preço ÷ metragem, calculado só para essa checagem e descartado depois)

O `preco_m2` foi incluído porque é o indicador mais direto do outlier estrutural descrito na seção 2.6: mesmo depois de remover os "lançamentos" pelo padrão de link, um imóvel individual com metragem ou preço desproporcionais ao restante da região ainda pode passar despercebido olhando só para `preco` ou `metragem` isoladamente. Cada etapa imprime no console quantos registros foram removidos e os limites aceitáveis usados, para manter o processo auditável.

### 3.6 Saída da Fase

O dataset limpo é salvo em `data/clean/imoveis_limpos.csv`, com o índice reorganizado (`reset_index(drop=True)`) após todas as filtragens, servindo como base de entrada para a etapa de modelagem preditiva.

---

## 4. Modelagem Preditiva (`analise.py`)

### 4.1 Objetivo

Ajustar um modelo de **Regressão Linear** para estimar `preco` a partir das features numéricas geradas na limpeza, e avaliar sua qualidade com métricas além do R² (MAE, RMSE, MAPE, R² ajustado e R² por validação cruzada de 5 folds), para não tirar conclusão de uma única métrica isolada nem de um único split treino/teste.

### 4.2 Decisão: Remoção da Feature `quartos`

O modelo inicial usava `quartos`, `suites`, `metragem` e `vagas` como preditoras, e chegou a um R² de teste de **0,578**, com o coeficiente de `quartos` praticamente nulo (**-745**, contra +95.286 de `suites` e +3.361 de `metragem`) — efeito esperado de **colinearidade**: apartamentos maiores tendem a ter mais quartos, então, controlando por `metragem`, um quarto a mais no mesmo tamanho não agrega valor perceptível (às vezes até indica cômodos menores/subdivididos).

Testado o modelo sem `quartos` (mesmas 3 features restantes), o resultado foi:

| Métrica | Com `quartos` | Sem `quartos` |
|---|---|---|
| R² teste | 0,5780 | 0,5776 |
| R² ajustado | 0,5636 | 0,5668 |
| R² médio (CV 5-fold) | 0,5628 | 0,5682 |
| MAE | R$ 59.835 | R$ 59.796 |
| RMSE | R$ 81.142 | R$ 81.185 |
| MAPE | 17,60% | 17,59% |

A diferença é irrelevante em todas as métricas — como esperado, já que o coeficiente já era próximo de zero — e o R² ajustado e o R² de validação cruzada até melhoram ligeiramente, por o modelo deixar de "gastar" um grau de liberdade em uma variável que não explica nada. Por isso, `quartos` foi removido de `analise.py`: **não é um ganho de capacidade preditiva, é simplificação** — um modelo mais enxuto com desempenho equivalente.

### 4.3 Leitura dos Resultados Atuais

Com `suites`, `metragem` e `vagas`, o modelo explica ~58% da variação do preço (R² teste 0,5776), com erro médio de ~R$ 60 mil (MAE) e ~17,6% do valor do imóvel (MAPE). Os ~42% de variação não explicada apontam para a ausência de uma variável de **localização** (bairro/setor) no modelo — hoje só disponível como texto livre dentro de `titulo` — que é tipicamente o fator de maior peso no preço de imóveis e é o próximo candidato natural de feature engineering para melhorar o modelo de fato.

---

## Próximos Passos

- Extrair uma feature de **localização** (bairro/setor) a partir de `titulo` e incluí-la no modelo (`analise.py`) — maior candidata a melhorar o R² de 0,58 atual, já que hoje o modelo não usa nenhuma informação geográfica.
- Concluir a coleta do campo `subtitulo` (agora parte de `scraping.py`) para todos os imóveis, para que a remoção de ágio em `limpeza.py` deixe de depender de arquivo parcial.
- Reavaliar o filtro de "lançamento" caso o site volte a preencher `quartos`/`vagas` também para empreendimentos (hoje a regra combina padrão de URL + campos vazios como reforço).
- Definir como tratar erros de digitação pontuais (ex.: "62 quartos") de forma sistemática, caso passem a aparecer com frequência — hoje exigem investigação manual a cada rodada de EDA.

## Considerações Finais

O maior aprendizado deste pipeline foi que a qualidade do dado começa muito antes da limpeza estatística: ela depende de um mapeamento cuidadoso da fonte (scraping) e de uma investigação genuína do significado por trás de cada anomalia (EDA) — e, quando necessário, de voltar à etapa de coleta para buscar a informação que faltava, como no caso do ágio.

# 📊 Grafo de Dependências DAX — Power BI

Uma solução interativa desenvolvida para mapear a linhagem de dados e dependências de medidas em modelos complexos do Power BI. Este projeto nasceu da necessidade de otimizar a documentação técnica e facilitar auditorias de impacto antes de alterações em medidas críticas.



## 🚀 Funcionalidades

- **Mapeamento Visual:** Visualização em grafo hierárquico das dependências.
- **Identificação de Tipos:** Cores distintas para `MEASURE`, `COLUMN`, `TABLE` e objetos desconhecidos.
- **Painel de Detalhes:** Clique em qualquer nó para visualizar a expressão DAX formatada e limpa em um popup profissional.
- **Filtros Inteligentes:** Seleção por tipo de objeto e escolha de "Medidas Raízes" para focar em análises específicas.
- **Health Check:** Identificação visual de medidas que não servem de base para outros cálculos (potenciais medidas órfãs).

## 🛠️ Tecnologias Utilizadas

- **Python 3.11+**
- **Streamlit:** Interface web interativa.
- **NetworkX:** Inteligência de grafos e processamento de conexões.
- **Pyvis:** Renderização dinâmica e interativa do grafo.
- **Pandas:** Manipulação e tratamento dos dados extraídos do Power BI.

## 📋 Como usar

1. **Extração:** No Power BI Desktop, utilize a "Visualização de Consulta DAX" e execute a query `INFO.CALCDEPENDENCY()` (modelo disponível no app).
2. **Carregamento:** Salve os resultados em um arquivo `.csv` ou `.xlsx`.
3. **Exploração:** Faça o upload no app, selecione os tipos de objeto e a medida destino que deseja investigar.
4. **Análise:** Navegue pelo grafo, clique nos nós para conferir as expressões e entenda toda a árvore de cálculo.

## 🔧 Instalação Local

```bash
# Clone o repositório
git clone [https://github.com/gabrielavillagran/Dependencias_PBI.git](https://github.com/gabrielavillagran/Dependencias_PBI.git)

# Crie um ambiente virtual
python -m venv .venv
source .venv/bin/activate  # No Windows: .venv\Scripts\activate

# Instale as dependências
pip install -r requirements.txt

# Execute o App
streamlit run app.py

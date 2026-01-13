import streamlit as st
import pandas as pd
import networkx as nx
from pyvis.network import Network
import tempfile
import os
import json
from streamlit.components.v1 import html
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(layout="wide", page_title="Grafo de Dependências PBI")

# --- CSS PERSONALIZADO ---
st.markdown("""
    <style>
        [data-testid="stSidebar"] { min-width: 400px; max-width: 400px; }
        .stMetric { background-color: #f8f9fb; padding: 10px; border-radius: 10px; border: 1px solid #e6e9ef; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Grafo de Dependências — Power BI")

# --- FUNÇÃO DE LIMPEZA DAX ---
def limpar_dax(texto):
    if pd.isnull(texto) or texto == "None":
        return ""
    return str(texto).replace("_x000D_", "").strip()

# --- 1. SESSÃO DE INSTRUÇÕES E DOWNLOAD ---
with st.expander("📖 Como gerar o arquivo de dependências?", expanded=False):
    st.markdown("""
    ### Passo a Passo:
    1. Abra o seu relatório no **Power BI Desktop**.
    2. Vá até a aba **Exibição** e selecione **Visualização de consulta DAX**.
    3. Copie o código abaixo, cole na janela de consulta e clique em **Executar**.
    """)
    
    dax_query = """EVALUATE
VAR Medidas = INFO.MEASURES()
VAR Dependencias = INFO.CALCDEPENDENCY()
RETURN
SELECTCOLUMNS(
    FILTER(Dependencias, [OBJECT_TYPE] = "MEASURE"),
    "Tipo Origem", [REFERENCED_OBJECT_TYPE],
    "Origem", [REFERENCED_OBJECT],
    "Expressão Origem", IF([REFERENCED_OBJECT_TYPE] = "MEASURE", MAXX(FILTER(Medidas, [Name] = [REFERENCED_OBJECT]), [Expression]), BLANK()),
    "Tipo Destino", [OBJECT_TYPE],
    "Destino", [OBJECT],
    "Expressão Destino", MAXX(FILTER(Medidas, [Name] = [OBJECT]), [Expression])
)"""
    st.code(dax_query, language="sql")

    # --- CORREÇÃO: GERAR CSV COM BOM PARA ACENTOS ---
    buffer_csv = io.BytesIO()
    # Adiciona o BOM do UTF-8 para o Excel reconhecer o til (~) e acentos
    buffer_csv.write('\ufeff'.encode('utf-8'))
    
    df_template = pd.DataFrame(columns=[
        "[Tipo Origem]", "[Origem]", "[Expressão Origem]", 
        "[Tipo Destino]", "[Destino]", "[Expressão Destino]"
    ])
    
    df_template.to_csv(buffer_csv, index=False, sep=";", encoding='utf-8', mode='ab')
    
    st.download_button(
        label="📥 Baixar Modelo CSV para Preencher",
        data=buffer_csv.getvalue(),
        file_name="modelo_dependencias.csv",
        mime="text/csv"
    )

# --- 2. CARREGAMENTO ---
uploaded_file = st.file_uploader("Envie o arquivo preenchido", type=["csv", "xlsx"])

if uploaded_file:
    if uploaded_file.name.endswith('.xlsx'):
        df = pd.read_excel(uploaded_file)
    else:
        # --- CORREÇÃO: LER CSV COM UTF-8-SIG PARA ACENTOS ---
        df = pd.read_csv(uploaded_file, sep=None, engine='python', encoding='utf-8-sig')

    df.columns = df.columns.str.strip()
    
    col_origem, col_destino = "[Origem]", "[Destino]"
    col_tipo_origem, col_exp_origem, col_exp_destino = "[Tipo Origem]", "[Expressão Origem]", "[Expressão Destino]"

    if col_origem in df.columns and col_destino in df.columns:
        df[col_origem] = df[col_origem].astype(str).replace('nan', None)
        df[col_destino] = df[col_destino].astype(str).replace('nan', None)
        df = df.dropna(subset=[col_origem, col_destino])

        # --- 3. FILTROS ---
        st.sidebar.header("⚙️ Filtros do Grafo")
        tipos_disponiveis = sorted(df[col_tipo_origem].unique().astype(str).tolist())
        selecionar_todos = st.sidebar.checkbox("Selecionar todos os tipos", value=True)
        
        if selecionar_todos:
            tipos_selecionados = st.sidebar.multiselect("Filtrar Origens por Tipo:", options=tipos_disponiveis, default=tipos_disponiveis)
        else:
            tipos_selecionados = st.sidebar.multiselect("Filtrar Origens por Tipo:", options=tipos_disponiveis, default=[])

        df_filtrado = df[df[col_tipo_origem].isin(tipos_selecionados)]
        todas_destinos = sorted([str(m) for m in df_filtrado[col_destino].unique()])
        medidas_selecionadas = st.sidebar.multiselect("Selecione as Medidas Destino (Raízes):", options=todas_destinos, default=[])

        # Mapeamento de Info Limpo
        info_map = {}
        for _, row in df.iterrows():
            dest = str(row[col_destino])
            orig = str(row[col_origem])
            info_map[dest] = {"exp": limpar_dax(row[col_exp_destino]), "tipo": "MEASURE"}
            if orig not in info_map or not info_map[orig]["exp"]:
                info_map[orig] = {"exp": limpar_dax(row[col_exp_origem]), "tipo": str(row[col_tipo_origem])}

        if medidas_selecionadas:
            arestas, visitados, fila = [], set(), list(medidas_selecionadas)
            while fila:
                atual = fila.pop(0)
                if atual not in visitados:
                    visitados.add(atual)
                    filhos = df_filtrado[df_filtrado[col_destino] == atual][col_origem].tolist()
                    for filho in filhos:
                        arestas.append((atual, filho))
                        if filho not in visitados: fila.append(filho)
            
            G = nx.DiGraph()
            G.add_edges_from(arestas)

            # --- 4. MÉTRICAS ---
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Objetos no Modelo", df[col_origem].nunique())
            c2.metric("Nós no Grafo", len(G.nodes()))
            c3.metric("Relacionamentos", len(arestas))
            c4.metric("Tipos Ativos", len(tipos_selecionados))

            # --- 5. LEGENDA ---
            cores = {"MEASURE": "#88B995", "COLUMN": "#5E9AE9", "TABLE": "#F4A460", "UNKNOWN": "#CCCCCC"}
            st.write("###")
            cols_leg = st.columns(4)
            for i, (k, v) in enumerate(list(cores.items())[:4]):
                cols_leg[i].markdown(f'<div style="display:flex;align-items:center;gap:10px;background:#f8f9fb;padding:5px 15px;border-radius:8px;border:1px solid #ddd;"><div style="width:12px;height:12px;background:{v};border-radius:2px;"></div><span style="font-size:14px;font-weight:bold;">{k}</span></div>', unsafe_allow_html=True)
            st.write("###")

            # --- 6. GERAÇÃO DO GRAFO ---
            net = Network(height="600px", width="100%", directed=True, bgcolor="#ffffff")
            for node in G.nodes():
                tipo = info_map.get(node, {}).get("tipo", "UNKNOWN")
                net.add_node(node, label=node, title="Clique para ver o DAX", color=cores.get(tipo, cores["UNKNOWN"]), shape="box", margin=10, font={"face": "Segoe UI"})
            for u, v in G.edges():
                net.add_edge(u, v, color="#CCCCCC", width=1)

            net.set_options(json.dumps({
                "nodes": {"shadow": True},
                "layout": {"hierarchical": {"enabled": True, "direction": "UD", "sortMethod": "directed", "levelSeparation": 150, "nodeSpacing": 200}},
                "physics": {"enabled": False},
                "interaction": {"hover": True}
            }))

            path = os.path.join(tempfile.gettempdir(), "graph_pbi.html")
            net.save_graph(path)
            with open(path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            info_json = json.dumps(info_map)
            custom_js = f"""
            <div id="dax-panel" style="position:fixed; top:20px; right:20px; width:450px; max-height:80vh; background:#ffffff; color:#31333f; border-radius:12px; padding:20px; overflow-y:auto; z-index:99999; display:none; box-shadow: 0 4px 16px rgba(0,0,0,0.15); font-family: 'Source Sans Pro', sans-serif; border: 1px solid #e6e9ef;">
                <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:12px; border-bottom: 1px solid #e6e9ef; padding-bottom:10px;">
                    <div>
                        <div id="panel-title" style="font-size:16px; font-weight:bold; color:#1f77b4; margin-bottom:2px;">Objeto</div>
                        <div id="panel-type" style="font-size:11px; color:#7d7d7d; text-transform:uppercase; font-weight: 600;">TIPO</div>
                    </div>
                    <button onclick="document.getElementById('dax-panel').style.display='none'" style="background:none; border:none; color:#999; cursor:pointer; font-size:24px; line-height:1; padding:0 5px;">&times;</button>
                </div>
                <pre id="panel-exp" style="white-space: pre-wrap; word-wrap: break-word; font-size: 14px; line-height: 1.6; color: #000000; margin: 0; background-color: #f0f2f6; padding: 16px; border-radius: 8px; font-family: 'Source Code Pro', monospace;"></pre>
            </div>
            <script>
                var infoData = {info_json};
                network.on("click", function (params) {{
                    if (params.nodes.length > 0) {{
                        var id = params.nodes[0];
                        var item = infoData[id];
                        document.getElementById('panel-title').innerText = id;
                        document.getElementById('panel-type').innerText = item.tipo;
                        document.getElementById('panel-exp').innerText = (item.exp && item.exp !== 'None') ? item.exp : "Sem expressão DAX disponível.";
                        document.getElementById('dax-panel').style.display = 'block';
                    }}
                }});
            </script>
            """
            full_html = html_content.replace("</body>", f"{custom_js}</body>")
            html(full_html, height=650)

            st.markdown("---")
            st.subheader("📑 Detalhes dos Objetos (DAX)")
            nos_ordenados = sorted(list(G.nodes()))
            col_a, col_b = st.columns(2)
            for i, n in enumerate(nos_ordenados):
                info = info_map.get(n, {})
                exp, tipo = info.get("exp", ""), info.get("tipo", "UNKNOWN")
                target = col_a if i % 2 == 0 else col_b
                with target:
                    if exp:
                        with st.expander(f"📌 {tipo}: {n}"): st.code(exp, language="sql")
                    else:
                        with st.expander(f"⚪ {tipo}: {n}"): st.write("Objeto nativo ou sem expressão DAX.")
        else:
            st.info("Selecione pelo menos uma Medida Raiz na barra lateral.")
    else:
        st.error("Colunas [Origem] ou [Destino] não encontradas no arquivo.")
else:
    st.info("Aguardando upload do arquivo para gerar o grafo.")
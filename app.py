import streamlit as st
import pandas as pd
import time
import re

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Precificador 2026 - V46 Stable", layout="centered", page_icon="💎")

# --- 2. ESTADO ---
if 'lista_produtos' not in st.session_state:
    st.session_state.lista_produtos = []

def init_state(key, value):
    if key not in st.session_state:
        st.session_state[key] = value

# Variáveis
init_state('n_mlb', '') 
init_state('n_sku', '') 
init_state('n_nome', '')
init_state('n_cmv', 32.57)
init_state('n_extra', 0.00)
init_state('n_frete', 18.86)
init_state('n_taxa', 16.5)
init_state('n_erp', 85.44)
init_state('n_merp', 20.0)

# --- 3. CSS (APPLE DESIGN) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&display=swap');
    .stApp { background-color: #FAFAFA; font-family: 'Inter', sans-serif; }
    
    /* Cards */
    .input-card { background: white; border-radius: 20px; padding: 24px; box-shadow: 0 10px 30px -10px rgba(0,0,0,0.05); border: 1px solid #EFEFEF; margin-bottom: 20px; }
    .feed-card { background: white; border-radius: 16px; border: 1px solid #DBDBDB; box-shadow: 0 2px 5px rgba(0,0,0,0.02); margin-bottom: 15px; overflow: hidden; }
    
    .card-header { padding: 15px 20px; border-bottom: 1px solid #F0F0F0; display: flex; justify-content: space-between; align-items: center; }
    .card-body { padding: 20px; text-align: center; }

    /* Texto */
    .sku-text { font-size: 11px; color: #8E8E8E; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }
    .title-text { font-size: 16px; font-weight: 600; color: #262626; margin-top: 2px; }
    .price-hero { font-size: 32px; font-weight: 800; letter-spacing: -1px; color: #262626; margin: 5px 0; }
    
    /* Pills */
    .pill { padding: 6px 12px; border-radius: 20px; font-size: 13px; font-weight: 700; display: inline-block; }
    .pill-green { background-color: #E6FFFA; color: #047857; border: 1px solid #D1FAE5; }
    .pill-yellow { background-color: #FFFBEB; color: #B45309; border: 1px solid #FCD34D; }
    .pill-red { background-color: #FEF2F2; color: #DC2626; border: 1px solid #FEE2E2; }

    /* Inputs e Botões */
    div[data-testid="stNumberInput"] input, div[data-testid="stTextInput"] input { background-color: #FAFAFA !important; border: 1px solid #E5E5E5 !important; color: #333 !important; border-radius: 8px !important; }
    div.stButton > button[kind="primary"] { background: linear-gradient(135deg, #2563EB, #1D4ED8); color: white; border-radius: 10px; height: 50px; border: none; font-weight: 600; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2); }
    
    /* Search Container */
    .search-container {
        position: sticky; top: 0; z-index: 100; background: #FAFAFA; padding-bottom: 10px; padding-top: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --- 4. FUNÇÕES ---
def limpar_valor_dinheiro(valor):
    if pd.isna(valor) or valor == "" or valor == "-": return 0.0
    if isinstance(valor, (int, float)): return float(valor)
    valor_str = str(valor).strip()
    valor_str = re.sub(r'[^\d,\.-]', '', valor_str)
    if not valor_str: return 0.0
    if ',' in valor_str and '.' in valor_str: valor_str = valor_str.replace('.', '').replace(',', '.') 
    elif ',' in valor_str: valor_str = valor_str.replace(',', '.')
    try: return float(valor_str)
    except: return 0.0

def reiniciar_app():
    time.sleep(0.1)
    if hasattr(st, 'rerun'): st.rerun()
    else: st.experimental_rerun()

# --- 5. SIDEBAR ---
with st.sidebar:
    st.header("Ajustes")
    imposto_padrao = st.number_input("Impostos (%)", value=27.0, step=0.5)
    with st.expander("Tabela Frete ML (<79)", expanded=True):
        taxa_12_29 = st.number_input("12-29", value=6.25)
        taxa_29_50 = st.number_input("29-50", value=6.50)
        taxa_50_79 = st.number_input("50-79", value=6.75)
        taxa_minima = st.number_input("Min", value=3.25)
    st.divider()
    
    st.markdown("### 📂 Importar")
    uploaded_file = st.file_uploader("Excel/CSV", type=['xlsx', 'csv'])
    
    if uploaded_file:
        try:
            xl = pd.ExcelFile(uploaded_file)
            aba = st.selectbox("Aba:", xl.sheet_names)
            header = st.number_input("Linha Cabeçalho:", value=8, min_value=0)
            
            if st.button("Preview / Mapear", type="primary"):
                st.session_state.df_preview = xl.parse(aba, header=header, nrows=2)
                st.session_state.import_config = {'file': uploaded_file, 'aba': aba, 'header': header}
                st.rerun()
                
        except Exception as e: st.error(f"Erro: {e}")

    if 'import_config' in st.session_state and 'df_preview' in st.session_state:
        df_p = st.session_state.df_preview
        cols = list(df_p.columns)
        
        st.caption("Mapeie as colunas:")
        def g_idx(k): 
            for i, c in enumerate(cols): 
                if k.lower() in str(c).lower(): return i
            return 0
            
        c_prod = st.selectbox("Produto", cols, index=g_idx("Produto"))
        c_cmv = st.selectbox("CMV", cols, index=g_idx("CMV"))
        c_prc = st.selectbox("Preço Venda", cols, index=g_idx("Preço"))
        c_erp = st.selectbox("Preço ERP/Base", cols, index=g_idx("GRA"))
        
        if st.button("Confirmar Importação"):
            try:
                cfg = st.session_state.import_config
                df = pd.read_excel(cfg['file'], sheet_name=cfg['aba'], header=cfg['header'])
                cnt = 0
                st.session_state.lista_produtos = [] # Limpa ao importar
                for i, row in df.iterrows():
                    try:
                        p = str(row[c_prod])
                        if not p or p == 'nan': continue
                        c = limpar_valor_dinheiro(row[c_cmv])
                        pb = limpar_valor_dinheiro(row[c_prc])
                        erp = limpar_valor_dinheiro(row[c_erp])
                        if erp == 0: erp = pb
                        
                        st.session_state.lista_produtos.append({
                            "id": int(time.time()*1000)+i, "MLB": "", "SKU": "", "Produto": p,
                            "CMV": c, "FreteManual": 18.86, "TaxaML": 16.5, "Extra": 0.0,
                            "PrecoERP": erp, "MargemERP": 20.0, "PrecoBase": pb, "DescontoPct": 0.0, "Bonus": 0.0
                        })
                        cnt += 1
                    except: continue
                st.toast(f"{cnt} importados!")
                del st.session_state['import_config']
                time.sleep(1)
                reiniciar_app()
            except: st.error("Erro na importação final")

# --- 6. LÓGICA ---
def identificar_faixa_frete(preco):
    if preco >= 79.00: return "manual", 0.0
    elif 50.00 <= preco < 79.00: return "Tab. 50-79", taxa_50_79
    elif 29.00 <= preco < 50.00: return "Tab. 29-50", taxa_29_50
    elif 12.50 <= preco < 29.00: return "Tab. 12-29", taxa_12_29
    else: return "Tab. Mínima", taxa_minima

def calcular_preco_sugerido_reverso(custo_base, lucro_alvo_reais, taxa_ml_pct, imposto_pct, frete_manual):
    custos_fixos_1 = custo_base + frete_manual
    divisor = 1 - ((taxa_ml_pct + imposto_pct) / 100)
    if divisor <= 0: return 0.0, "Erro"
    preco_est_1 = (custos_fixos_1 + lucro_alvo_reais) / divisor
    if preco_est_1 >= 79.00: return preco_est_1, "Frete Manual"
    for taxa, nome, p_min, p_max in [
        (taxa_50_79, "Tab. 50-79", 50, 79), (taxa_29_50, "Tab. 29-50", 29, 50), (taxa_12_29, "Tab. 12-29", 12.5, 29)
    ]:
        custos = custo_base + taxa
        preco = (custos + lucro_alvo_reais) / divisor
        if p_min <= preco < p_max: return preco, nome
    return preco_est_1, "Frete Manual"

def adicionar_produto_action():
    if not st.session_state.n_nome:
        st.toast("Nome obrigatório!", icon="⚠️")
        return
    lucro_alvo = st.session_state.n_erp * (st.session_state.n_merp / 100)
    preco_sug, _ = calcular_preco_sugerido_reverso(
        st.session_state.n_cmv + st.session_state.n_extra, lucro_alvo,
        st.session_state.n_taxa, imposto_padrao, st.session_state.n_frete
    )
    novo_item = {
        "id": int(time.time() * 1000),
        "MLB": st.session_state.n_mlb, "SKU": st.session_state.n_sku, "Produto": st.session_state.n_nome,
        "CMV": st.session_state.n_cmv, "FreteManual": st.session_state.n_frete,
        "TaxaML": st.session_state.n_taxa, "Extra": st.session_state.n_extra,
        "PrecoERP": st.session_state.n_erp, "MargemERP": st.session_state.n_merp,
        "PrecoBase": preco_sug, "DescontoPct": 0.0, "Bonus": 0.0,
    }
    st.session_state.lista_produtos.append(novo_item)
    st.toast("Salvo!", icon="✅")
    st.session_state.n_mlb = ""
    st.session_state.n_sku = "" 
    st.session_state.n_nome = ""
    st.session_state.n_cmv = 0.00
    st.session_state.n_extra = 0.00

# ==============================================================================
# 7. INTERFACE PRINCIPAL
# ==============================================================================

# --- HEADER E SEARCH (FLUTUANTE) ---
st.markdown('<div class="search-container">', unsafe_allow_html=True)
c_tit, c_search, c_sort = st.columns([1.5, 3, 1.5])
c_tit.markdown("### Precificador")
termo_busca = c_search.text_input("", placeholder="🔍 Buscar...", label_visibility="collapsed")
ordem_sort = c_sort.selectbox("", ["Recentes", "A-Z", "Maior Margem", "Menor Margem", "Maior Preço"], label_visibility="collapsed")
st.markdown('</div>', unsafe_allow_html=True)

# --- MODO DE EXIBIÇÃO ---
# Se estiver buscando, esconde o cadastro para focar no resultado
modo_busca = True if termo_busca else False

if not modo_busca:
    # --- INPUT CARD ---
    st.markdown('<div class="input-card">', unsafe_allow_html=True)
    st.caption("CADASTRAR NOVO")
    st.text_input("MLB", key="n_mlb", placeholder="Ex: MLB-12345")
    c1, c2 = st.columns([1, 2])
    c1.text_input("SKU", key="n_sku")
    c2.text_input("Produto", key="n_nome")
    c3, c4 = st.columns(2)
    c3.number_input("Custo (CMV)", step=0.01, format="%.2f", key="n_cmv")
    c4.number_input("Frete Manual", step=0.01, format="%.2f", key="n_frete")
    st.markdown("<hr style='margin: 10px 0; border-color: #eee;'>", unsafe_allow_html=True)
    c5, c6, c7 = st.columns(3)
    c5.number_input("Taxa ML %", step=0.5, format="%.1f", key="n_taxa")
    c6.number_input("Preço ERP", step=0.01, format="%.2f", key="n_erp")
    c7.number_input("Margem ERP %", step=1.0, format="%.1f", key="n_merp")
    st.write("")
    st.button("Cadastrar Item", type="primary", use_container_width=True, on_click=adicionar_produto_action)
    st.markdown('</div>', unsafe_allow_html=True)

# --- PROCESSAMENTO DA LISTA (ORDENAÇÃO E FILTRO) ---
if st.session_state.lista_produtos:
    
    # 1. Copia para não alterar o original durante a ordenação visual
    lista_view = []
    
    # Pré-cálculo para poder ordenar por margem/lucro
    for item in st.session_state.lista_produtos:
        pf = item['PrecoBase'] * (1 - item['DescontoPct']/100)
        _, fr = identificar_faixa_frete(pf)
        if _ == "manual": fr = item['FreteManual']
        luc = pf - (item['CMV'] + item['Extra'] + fr + (pf*(imposto_padrao+item['TaxaML'])/100)) + item['Bonus']
        mrg = (luc/pf*100) if pf > 0 else 0
        
        # Cria objeto de visualização
        view_item = item.copy()
        view_item['_calc_preco'] = pf
        view_item['_calc_lucro'] = luc
        view_item['_calc_margem'] = mrg
        lista_view.append(view_item)

    # 2. Filtro de Texto
    if termo_busca:
        t = termo_busca.lower()
        lista_view = [p for p in lista_view if t in p['Produto'].lower() or t in str(p['MLB']).lower() or t in str(p['SKU']).lower()]

    # 3. Ordenação
    if ordem_sort == "A-Z": lista_view.sort(key=lambda x: x['Produto'].lower())
    elif ordem_sort == "Maior Margem": lista_view.sort(key=lambda x: x['_calc_margem'], reverse=True)
    elif ordem_sort == "Menor Margem": lista_view.sort(key=lambda x: x['_calc_margem'])
    elif ordem_sort == "Maior Preço": lista_view.sort(key=lambda x: x['_calc_preco'], reverse=True)
    else: lista_view.reverse() # Recentes (Padrão)

    if modo_busca: st.caption(f"Resultados: {len(lista_view)}")

    # --- RENDERIZAÇÃO ---
    for item in lista_view:
        
        # Recupera valores calculados
        preco_final_calc = item['_calc_preco']
        lucro_final = item['_calc_lucro']
        margem_final = item['_calc_margem']
        
        # Cores (Semáforo)
        if margem_final < 8.0: pill_cls = "pill-red"
        elif 8.0 <= margem_final < 15.0: pill_cls = "pill-yellow"
        else: pill_cls = "pill-green"

        # Texto Invertido (Pedido V30)
        txt_pill = f"{margem_final:.1f}%" # Margem na Pill
        txt_lucro = f"R$ {lucro_final:.2f}"
        if lucro_final > 0: txt_lucro = "+ " + txt_lucro
        
        sku_show = item.get('SKU', '')
        
        st.markdown(f"""
        <div class="feed-card">
            <div class="card-header">
                <div>
                    <div class="sku-text">{item['MLB']} {sku_show}</div>
                    <div class="title-text">{item['Produto']}</div>
                </div>
                <div class="{pill_cls} pill">{txt_pill}</div>
            </div>
            <div class="card-body">
                <div style="font-size: 11px; color:#888; font-weight:600;">PREÇO DE VENDA</div>
                <div class="price-hero">R$ {preco_final_calc:.2f}</div>
                <div style="font-size: 13px; color:#555;">Lucro Líquido: <b>{txt_lucro}</b></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("⚙️ Editar"):
            
            # ATENÇÃO: Encontrar o índice real no session_state para editar o item certo
            real_idx = -1
            for idx, org in enumerate(st.session_state.lista_produtos):
                if org['id'] == item['id']: 
                    real_idx = idx
                    break
            
            if real_idx != -1:
                def up_field(k, f, i=real_idx): st.session_state.lista_produtos[i][f] = st.session_state[k]

                ec1, ec2, ec3 = st.columns(3)
                ec1.number_input("Preço Tabela", value=float(item['PrecoBase']), step=0.5, key=f"p_{item['id']}", on_change=up_field, args=(f"p_{item['id']}", 'PrecoBase'))
                ec2.number_input("Desconto %", value=float(item['DescontoPct']), step=0.5, key=f"d_{item['id']}", on_change=up_field, args=(f"d_{item['id']}", 'DescontoPct'))
                ec3.number_input("Rebate R$", value=float(item['Bonus']), step=0.01, key=f"b_{item['id']}", on_change=up_field, args=(f"b_{item['id']}", 'Bonus'))
                
                st.divider()
                
                # DRE Nativa (Simplificada para Mobile)
                col_dre1, col_dre2 = st.columns([2, 1])
                col_dre1.caption("Detalhes de Custo")
                
                # Recalcula custos para mostrar
                _, fr_real = identificar_faixa_frete(preco_final_calc)
                if _ == "manual": fr_real = item['FreteManual']
                taxs = preco_final_calc * ((imposto_padrao + item['TaxaML']) / 100)
                
                col_dre1.write(f"Impostos + Comissões: R$ {taxs:.2f}")
                col_dre1.write(f"Frete + Custos: R$ {(fr_real + item['CMV'] + item['Extra']):.2f}")
                
                # Botão Deletar Seguro
                def del_item(i=real_idx):
                    del st.session_state.lista_produtos[i]
                    # Não precisa de rerun aqui se estiver dentro do form, mas ajuda
                
                if st.button("🗑️ Excluir", key=f"del_{item['id']}"):
                    del st.session_state.lista_produtos[real_idx]
                    reiniciar_app()

else:
    if not modo_busca:
        st.markdown("""
        <div style="text-align: center; color: #BBB; padding: 40px;">
            <h3 style="color: #DDD;">Lista Vazia</h3>
            Preencha os dados acima.
        </div>
        """, unsafe_allow_html=True)

import streamlit as st
import pandas as pd
import time
import re

# --- 1. CONFIGURAÇÃO (APP SHELL) ---
st.set_page_config(page_title="Precificador 2026 - V57 Blindada", layout="centered", page_icon="💎")

# Tenta importar Plotly
try:
    import plotly.express as px
    has_plotly = True
except ImportError:
    has_plotly = False

# --- 2. ESTADO (MEMORY) ---
if 'lista_produtos' not in st.session_state:
    st.session_state.lista_produtos = []

def init_state(key, value):
    if key not in st.session_state:
        st.session_state[key] = value

init_state('n_mlb', '') 
init_state('n_sku', '') 
init_state('n_nome', '')
init_state('n_cmv', 32.57)
init_state('n_extra', 0.00)
init_state('n_frete', 18.86)
init_state('n_taxa', 16.5)
init_state('n_erp', 85.44)
init_state('n_merp', 20.0)

# --- 3. DESIGN SYSTEM ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&display=swap');
    .stApp { background-color: #FAFAFA; font-family: 'Inter', sans-serif; }
    
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: white; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .stTabs [aria-selected="true"] { background-color: #2563EB !important; color: white !important; }

    .input-card { background: white; border-radius: 20px; padding: 24px; box-shadow: 0 10px 30px -10px rgba(0,0,0,0.05); border: 1px solid #EFEFEF; margin-bottom: 20px; }
    .feed-card { background: white; border-radius: 16px; border: 1px solid #DBDBDB; box-shadow: 0 2px 5px rgba(0,0,0,0.02); margin-bottom: 15px; overflow: hidden; }
    .card-header { padding: 15px 20px; border-bottom: 1px solid #F0F0F0; display: flex; justify-content: space-between; align-items: center; }
    .card-body { padding: 20px; text-align: center; }

    .sku-text { font-size: 11px; color: #8E8E8E; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }
    .title-text { font-size: 16px; font-weight: 600; color: #262626; margin-top: 2px; }
    .price-hero { font-size: 32px; font-weight: 800; letter-spacing: -1px; color: #262626; margin: 5px 0; }
    
    .pill { padding: 6px 12px; border-radius: 20px; font-size: 13px; font-weight: 700; display: inline-block; }
    .pill-green { background-color: #E6FFFA; color: #047857; border: 1px solid #D1FAE5; }
    .pill-yellow { background-color: #FFFBEB; color: #B45309; border: 1px solid #FCD34D; }
    .pill-red { background-color: #FEF2F2; color: #DC2626; border: 1px solid #FEE2E2; }

    .audit-box { background-color: #F8F9FA; border: 1px solid #E9ECEF; border-radius: 8px; padding: 15px; font-family: 'Courier New', monospace; font-size: 12px; color: #333; margin-top: 10px; }
    .audit-line { display: flex; justify-content: space-between; margin-bottom: 4px; }
    .audit-bold { font-weight: bold; color: #000; }

    div[data-testid="stNumberInput"] input, div[data-testid="stTextInput"] input { background-color: #FAFAFA !important; border: 1px solid #E5E5E5 !important; color: #333 !important; border-radius: 8px !important; }
    div.stButton > button[kind="primary"] { background: linear-gradient(135deg, #2563EB, #1D4ED8); color: white; border-radius: 10px; height: 50px; font-weight: 600; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2); }
    div[data-testid="stSelectbox"] > div > div { background-color: white !important; border: 1px solid #2563EB !important; border-radius: 12px !important; box-shadow: 0 4px 15px rgba(37, 99, 235, 0.1); }
</style>
""", unsafe_allow_html=True)

# --- 4. FUNÇÕES ---
def limpar_valor_dinheiro(valor):
    try:
        if pd.isna(valor) or str(valor).strip() == "" or str(valor).strip() == "-": return 0.0
        if isinstance(valor, (int, float)): return float(valor)
        valor_str = str(valor).strip()
        valor_str = re.sub(r'[^\d,\.-]', '', valor_str)
        if not valor_str: return 0.0
        if ',' in valor_str and '.' in valor_str: valor_str = valor_str.replace('.', '').replace(',', '.') 
        elif ',' in valor_str: valor_str = valor_str.replace(',', '.')
        return float(valor_str)
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
    
    # --- IMPORTAÇÃO ---
    st.markdown("### 📂 Importar")
    uploaded_file = st.file_uploader("Excel/CSV", type=['xlsx', 'csv'])
    
    if uploaded_file is not None:
        try:
            xl = pd.ExcelFile(uploaded_file)
            aba_selecionada = st.selectbox("1. Aba:", xl.sheet_names, index=0)
            header_row = st.number_input("2. Linha Cabeçalho:", value=8, min_value=0)
            
            df_preview = xl.parse(aba_selecionada, header=header_row, nrows=3)
            cols = [str(c) for c in df_preview.columns if "Unnamed" not in str(c)]
            
            st.caption("3. Mapear Colunas:")
            def get_idx(opts, keys):
                if isinstance(keys, str): keys = [keys]
                for i, o in enumerate(opts):
                    for k in keys: 
                        if k.lower() in str(o).lower(): return i
                return 0

            c_prod = st.selectbox("Produto", cols, index=get_idx(cols, ["Produto", "Nome"]))
            c_mlb = st.selectbox("MLB", cols, index=get_idx(cols, ["Anúncio", "MLB"]))
            c_sku = st.selectbox("SKU", cols, index=get_idx(cols, ["SKU", "Ref"]))
            c_cmv = st.selectbox("CMV", cols, index=get_idx(cols, "CMV"))
            c_prc = st.selectbox("Preço Venda", cols, index=get_idx(cols, ["Preço", "Venda"]))
            c_erp = st.selectbox("Preço ERP", cols, index=get_idx(cols, ["ERP", "Base", "GRA"]))
            c_desc = st.selectbox("Desconto %", cols, index=get_idx(cols, ["Desconto", "%"]))
            c_bonus = st.selectbox("Rebate/Bônus", cols, index=get_idx(cols, ["Bônus", "Rebate", "Bonus"]))
            
            if st.button("✅ Importar", type="primary"):
                df = xl.parse(aba_selecionada, header=header_row)
                cnt = 0
                st.session_state.lista_produtos = []
                for _, row in df.iterrows():
                    try:
                        p = str(row[c_prod])
                        if not p or p == 'nan': continue
                        
                        cmv = limpar_valor_dinheiro(row[c_cmv])
                        pb = limpar_valor_dinheiro(row[c_prc])
                        erp = limpar_valor_dinheiro(row[c_erp])
                        if erp == 0: erp = pb
                        
                        desc = limpar_valor_dinheiro(row[c_desc])
                        bonus = limpar_valor_dinheiro(row[c_bonus])
                        
                        if 0 < desc < 1.0: desc = desc * 100
                        
                        sku_val = str(row[c_sku]) if c_sku in row else ""
                        if sku_val == 'nan': sku_val = ""

                        st.session_state.lista_produtos.append({
                            "id": int(time.time()*1000)+_, 
                            "MLB": str(row[c_mlb]), 
                            "SKU": sku_val, 
                            "Produto": p,
                            "CMV": cmv, 
                            "FreteManual": 18.86, 
                            "TaxaML": 16.5, 
                            "Extra": 0.0,
                            "PrecoERP": erp, 
                            "MargemERP": 20.0, 
                            "PrecoBase": pb, 
                            "DescontoPct": desc, 
                            "Bonus": bonus       
                        })
                        cnt += 1
                    except: continue
                st.toast(f"{cnt} importados!", icon="🚀")
                time.sleep(1)
                reiniciar_app()
        except Exception as e: st.error(f"Erro: {e}")

# --- 6. LÓGICA ---
def identificar_faixa_frete(preco):
    if preco >= 79.00: return "manual", 0.0, "Acima de 79 (Manual)"
    elif 50.00 <= preco < 79.00: return "Tab. 50-79", taxa_50_79, "Faixa R$ 50-79"
    elif 29.00 <= preco < 50.00: return "Tab. 29-50", taxa_29_50, "Faixa R$ 29-50"
    elif 12.50 <= preco < 29.00: return "Tab. 12-29", taxa_12_29, "Faixa R$ 12-29"
    else: return "Tab. Mínima", taxa_minima, "Abaixo de R$ 12.50"

def calcular_preco_sugerido_reverso(custo_base, lucro_alvo_reais, taxa_ml_pct, imposto_pct, frete_manual):
    custos_fixos_1 = custo_base + frete_manual
    divisor = 1 - ((taxa_ml_pct + imposto_pct) / 100)
    if divisor <= 0: return 0.0, "Erro"
    
    preco_est_1 = (custos_fixos_1 + lucro_alvo_reais) / divisor
    if preco_est_1 >= 79.00: return preco_est_1, "Frete Manual"
    
    for taxa, nome, p_min, p_max in [
        (taxa_50_79, "Tab. 50-79", 50, 79),
        (taxa_29_50, "Tab. 29-50", 29, 50),
        (taxa_12_29, "Tab. 12-29", 12.5, 29)
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
    st.session_state.lista_produtos.append({
        "id": int(time.time()*1000), "MLB": st.session_state.n_mlb, "SKU": st.session_state.n_sku, 
        "Produto": st.session_state.n_nome, "CMV": st.session_state.n_cmv, "FreteManual": st.session_state.n_frete,
        "TaxaML": st.session_state.n_taxa, "Extra": st.session_state.n_extra, "PrecoERP": st.session_state.n_erp, 
        "MargemERP": st.session_state.n_merp, "PrecoBase": preco_sug, "DescontoPct": 0.0, "Bonus": 0.0
    })
    st.toast("Salvo!", icon="✅")
    st.session_state.n_mlb = ""
    st.session_state.n_sku = "" 
    st.session_state.n_nome = ""
    st.session_state.n_cmv = 0.00
    st.session_state.n_extra = 0.00

# ==============================================================================
# 7. INTERFACE PRINCIPAL
# ==============================================================================

st.markdown('<div style="text-align:center; padding-bottom:10px;">', unsafe_allow_html=True)
st.title("Precificador 2026")
st.markdown('</div>', unsafe_allow_html=True)

tab_op, tab_bi = st.tabs(["⚡ Operacional", "📊 Dashboards"])

# --- ABA 1: OPERACIONAL ---
with tab_op:
    
    # --- BUSCA BLINDADA ---
    mapa_busca = {}
    opcoes_busca = []
    
    if st.session_state.lista_produtos:
        for p in st.session_state.lista_produtos:
            # Cria label único para evitar colisão no selectbox
            label = f"{p['Produto']} | {p['MLB']} | #{p['id']}" 
            opcoes_busca.append(label)
            mapa_busca[label] = p

    c_busca, c_sort = st.columns([3, 1])
    selecao_busca = c_busca.selectbox("Busca", options=opcoes_busca, index=None, placeholder="🔍 Buscar...", label_visibility="collapsed")
    ordem_sort = c_sort.selectbox("", ["Recentes", "A-Z", "Z-A", "Maior Margem", "Menor Margem", "Maior Preço"], label_visibility="collapsed")

    lista_final = []
    
    # TRY-EXCEPT para evitar crash no filtro/sort
    try:
        if selecao_busca and selecao_busca in mapa_busca:
            lista_final = [mapa_busca[selecao_busca]]
        else:
            # Cópia segura para ordenação
            lista_final = [p.copy() for p in st.session_state.lista_produtos]
            
            # Pré-cálculo seguro
            for item in lista_final:
                pf = item['PrecoBase'] * (1 - item['DescontoPct']/100)
                _, fr, _ = identificar_faixa_frete(pf)
                if _ == "manual": fr = item['FreteManual']
                luc = pf - (item['CMV'] + item['Extra'] + fr + (pf*(imposto_padrao+item['TaxaML'])/100)) + item['Bonus']
                item['_mrg'] = (luc/pf*100) if pf > 0 else 0
                item['_prc'] = pf
            
            if ordem_sort == "A-Z": lista_final.sort(key=lambda x: str(x['Produto']).lower())
            elif ordem_sort == "Z-A": lista_final.sort(key=lambda x: str(x['Produto']).lower(), reverse=True)
            elif ordem_sort == "Maior Margem": lista_final.sort(key=lambda x: x['_mrg'], reverse=True)
            elif ordem_sort == "Menor Margem": lista_final.sort(key=lambda x: x['_mrg'])
            elif ordem_sort == "Maior Preço": lista_final.sort(key=lambda x: x['_prc'], reverse=True)
            else: lista_final.reverse()
    except Exception as e:
        st.error(f"Erro ao ordenar: {e}")
        lista_final = st.session_state.lista_produtos # Fallback

    # --- CADASTRO ---
    if not selecao_busca:
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

    # --- LISTA ---
    if lista_final:
        st.caption(f"Visualizando {len(lista_final)} produtos")
        for item in lista_final:
            
            # Recálculo para exibição
            preco_base_calc = item['PrecoBase']
            desc_calc = item['DescontoPct']
            preco_final_calc = preco_base_calc * (1 - (desc_calc / 100))
            
            nome_frete_real, valor_frete_real, motivo_frete = identificar_faixa_frete(preco_final_calc)
            if nome_frete_real == "manual": valor_frete_real = item['FreteManual']
            
            imposto_val = preco_final_calc * (imposto_padrao / 100)
            comissao_val = preco_final_calc * (item['TaxaML'] / 100)
            custos_totais = item['CMV'] + item['Extra'] + valor_frete_real + imposto_val + comissao_val
            lucro_final = preco_final_calc - custos_totais + item['Bonus']
            margem_final = (lucro_final / preco_final_calc * 100) if preco_final_calc > 0 else 0
            
            if margem_final < 8.0: pill_cls = "pill-red"
            elif margem_final < 15.0: pill_cls = "pill-yellow"
            else: pill_cls = "pill-green"

            txt_pill = f"{margem_final:.1f}%"
            txt_luc = f"+ R$ {lucro_final:.2f}" if lucro_final > 0 else f"- R$ {abs(lucro_final):.2f}"
            sku_show = item.get('SKU', '')
            
            st.markdown(f"""
            <div class="feed-card">
                <div class="card-header">
                    <div><div class="sku-text">{item['MLB']} {sku_show}</div><div class="title-text">{item['Produto']}</div></div>
                    <div class="{pill_cls} pill">{txt_pill}</div>
                </div>
                <div class="card-body">
                    <div style="font-size: 11px; color:#888; font-weight:600;">PREÇO DE VENDA</div>
                    <div class="price-hero">R$ {preco_final_calc:.2f}</div>
                    <div style="font-size: 13px; color:#555;">Lucro Líquido: <b>{txt_luc}</b></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.expander("⚙️ Editar e Detalhes"):
                # Busca Indice Real (Vital para edição correta)
                real_idx = next((i for i, x in enumerate(st.session_state.lista_produtos) if x['id'] == item['id']), -1)
                
                if real_idx != -1:
                    def up_f(k, f, i=real_idx): st.session_state.lista_produtos[i][f] = st.session_state[k]
                    c1, c2, c3 = st.columns(3)
                    c1.number_input("Preço", value=float(item['PrecoBase']), key=f"p{item['id']}", on_change=up_f, args=(f"p{item['id']}", 'PrecoBase'))
                    c2.number_input("Desc %", value=float(item['DescontoPct']), key=f"d{item['id']}", on_change=up_f, args=(f"d{item['id']}", 'DescontoPct'))
                    c3.number_input("Bônus", value=float(item['Bonus']), key=f"b{item['id']}", on_change=up_f, args=(f"b{item['id']}", 'Bonus'))
                    
                    st.divider()
                    
                    # --- MEMÓRIA DE CÁLCULO RESTAURADA ---
                    st.markdown("##### 🧮 Memória de Cálculo (Audit)")
                    st.markdown(f"""
                    <div class="audit-box">
                        <div class="audit-line"><span>(+) Preço Tabela</span> <span>R$ {preco_base_calc:.2f}</span></div>
                        <div class="audit-line" style="color:red;"><span>(-) Desconto ({desc_calc}%)</span> <span>R$ {preco_base_calc - preco_final_calc:.2f}</span></div>
                        <div class="audit-line audit-bold"><span>(=) VENDA FINAL</span> <span>R$ {preco_final_calc:.2f}</span></div>
                        <br>
                        <div class="audit-line"><span>(-) Impostos ({imposto_padrao}%)</span> <span>R$ {imposto_val:.2f}</span></div>
                        <div class="audit-line"><span>(-) Comissão ({item['TaxaML']}%)</span> <span>R$ {comissao_val:.2f}</span></div>
                        <div class="audit-line"><span>(-) Frete ({nome_frete_real})</span> <span>R$ {valor_frete_real:.2f}</span></div>
                        <div class="audit-line" style="font-size:10px; color:#888;">&nbsp;&nbsp;&nbsp;↳ {motivo_frete}</div>
                        <div class="audit-line"><span>(-) Custo CMV</span> <span>R$ {item['CMV']:.2f}</span></div>
                        <div class="audit-line"><span>(-) Extras</span> <span>R$ {item['Extra']:.2f}</span></div>
                        <br>
                        <div class="audit-line" style="color:green;"><span>(+) Bônus / Rebate</span> <span>R$ {item['Bonus']:.2f}</span></div>
                        <hr style="border-top: 1px dashed #ccc;">
                        <div class="audit-line audit-bold"><span>(=) LUCRO LÍQUIDO</span> <span>R$ {lucro_final:.2f}</span></div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.write("")
                    if st.button("🗑️ Excluir", key=f"del{item['id']}"):
                        del st.session_state.lista_produtos[real_idx]
                        reiniciar_app()
        
        # --- FOOTER ---
        st.markdown("---")
        col_d, col_c = st.columns([2, 1])
        
        csv_data = []
        for it in st.session_state.lista_produtos:
            pf = it['PrecoBase'] * (1 - it['DescontoPct']/100)
            _, fr, _ = identificar_faixa_frete(pf)
            if _ == "manual": fr = it['FreteManual']
            luc = pf - (it['CMV'] + it['Extra'] + fr + (pf*(imposto_padrao+it['TaxaML'])/100)) + it['Bonus']
            mrg = (luc/pf*100) if pf else 0
            csv_data.append({
                "MLB": it['MLB'], "SKU": it.get('SKU', ''), "Produto": it['Produto'],
                "Preco Venda": pf, "Lucro": luc, "Margem %": mrg
            })
        
        df_export = pd.DataFrame(csv_data)
        csv_file = df_export.to_csv(index=False).encode('utf-8')
        col_d.download_button("📥 Baixar Relatório", csv_file, "precificacao.csv", "text/csv")
        
        def limpar_tudo_action(): st.session_state.lista_produtos = []
        col_c.button("🗑️ LIMPAR TUDO", on_click=limpar_tudo_action, type="secondary")
        
    else:
        if not selecao_busca: st.info("Lista vazia.")

# --- ABA 2: DASHBOARDS ---
with tab_bi:
    if not has_plotly:
        st.error("⚠️ Adicione 'plotly' no requirements.txt")
    elif len(st.session_state.lista_produtos) > 0:
        rows = []
        for item in st.session_state.lista_produtos:
            pf = item['PrecoBase'] * (1 - item['DescontoPct']/100)
            _, fr, _ = identificar_faixa_frete(pf)
            if _ == "manual": fr = item['FreteManual']
            luc = pf - (item['CMV'] + item['Extra'] + fr + (pf*(imposto_padrao+item['TaxaML'])/100)) + item['Bonus']
            mrg = (luc/pf*100) if pf else 0
            
            status = 'Saudável'
            if mrg < 8: status = 'Crítico'
            elif mrg < 15: status = 'Atenção'
            
            rows.append({'Produto': item['Produto'], 'Margem': mrg, 'Lucro': luc, 'Status': status, 'Venda': pf, 
                         'Custo': item['CMV'], 'Imposto': pf*(imposto_padrao/100), 'Comissão': pf*(item['TaxaML']/100), 'Frete': fr})
        
        df_dash = pd.DataFrame(rows)
        k1, k2, k3 = st.columns(3)
        k1.metric("Produtos", len(df_dash))
        k2.metric("Média Margem", f"{df_dash['Margem'].mean():.1f}%")
        k3.metric("Lucro Total", f"R$ {df_dash['Lucro'].sum():.2f}")
        st.divider()
        
        counts = df_dash['Status'].value_counts().reset_index()
        counts.columns = ['Status', 'Qtd']
        fig = px.bar(counts, x='Status', y='Qtd', color='Status', 
                     color_discrete_map={'Crítico': '#EF4444', 'Atenção': '#F59E0B', 'Saudável': '#10B981'})
        st.plotly_chart(fig, use_container_width=True)
        
        # Decomposição (Stacked)
        st.subheader("Anatomia do Preço (Top 10)")
        df_top = df_dash.sort_values(by='Venda', ascending=False).head(10)
        fig3 = px.bar(df_top, y='Produto', x=['Custo', 'Frete', 'Comissão', 'Imposto', 'Lucro'], orientation='h')
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("Adicione produtos para ver os gráficos.")

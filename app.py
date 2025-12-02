import streamlit as st
import pandas as pd
import time
import re

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="Precificador 2026 - Mapeamento", layout="centered", page_icon="💎")

# --- 2. ESTADO ---
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

# --- 3. CSS (DESIGN SYSTEM V30) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&display=swap');
    .stApp { background-color: #FAFAFA; font-family: 'Inter', sans-serif; }
    
    .input-card { background: white; border-radius: 20px; padding: 24px; box-shadow: 0 10px 30px -10px rgba(0,0,0,0.05); border: 1px solid #EFEFEF; margin-bottom: 30px; }
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
    div[data-testid="stNumberInput"] input, div[data-testid="stTextInput"] input { background-color: #FAFAFA !important; border: 1px solid #E5E5E5 !important; color: #333 !important; border-radius: 8px !important; }
    div.stButton > button[kind="primary"] { background: linear-gradient(135deg, #2563EB, #1D4ED8); color: white; border-radius: 10px; height: 50px; border: none; font-weight: 600; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2); }
</style>
""", unsafe_allow_html=True)

# --- 4. FUNÇÕES ---
def limpar_valor_dinheiro(valor):
    if pd.isna(valor) or valor == "" or valor == "-": return 0.0
    if isinstance(valor, (int, float)): return float(valor)
    valor_str = str(valor).strip()
    # Remove R$, espaços e caracteres que não sejam numeros, virgula, ponto ou traço
    valor_str = re.sub(r'[^\d,\.-]', '', valor_str)
    if not valor_str: return 0.0
    
    # Lógica Brasil (1.200,00) vs EUA (1,200.00)
    # Se tem vírgula no final (ex: ,00 ou ,5), é decimal Brasil
    if ',' in valor_str:
        if valor_str.count('.') > 0: # Tem ponto de milhar (1.500,00)
            valor_str = valor_str.replace('.', '').replace(',', '.')
        else: # Só tem virgula (1500,00)
            valor_str = valor_str.replace(',', '.')
            
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
    
    # --- ÁREA DE IMPORTAÇÃO (MAPEAMENTO MANUAL) ---
    st.markdown("### 📂 Importar Planilha")
    uploaded_file = st.file_uploader("Arraste seu Excel", type=['xlsx'])
    
    if uploaded_file is not None:
        try:
            xl = pd.ExcelFile(uploaded_file)
            aba_selecionada = st.selectbox("1. Selecione a aba:", xl.sheet_names, index=0)
            header_row = st.number_input("2. Linha do Cabeçalho (Teste 8 ou 9):", value=8, min_value=0, step=1)
            
            # Carrega prévia
            df_preview = xl.parse(aba_selecionada, header=header_row, nrows=5)
            
            # Limpa colunas vazias ou sem nome
            cols_validas = [c for c in df_preview.columns if "Unnamed" not in str(c)]
            
            st.write("---")
            st.caption("3. Mapeie as Colunas (Selecione a coluna correspondente):")
            
            # Função para tentar adivinhar o indice padrão
            def get_idx(options, keyword):
                for i, opt in enumerate(options):
                    if keyword.lower() in str(opt).lower(): return i
                return 0

            # SELETORES DE MAPEAMENTO
            col_nome = st.selectbox("Nome do Produto", cols_validas, index=get_idx(cols_validas, "Produto"))
            col_mlb = st.selectbox("Código / MLB / Anúncio", cols_validas, index=get_idx(cols_validas, "Anúncio"))
            col_cmv = st.selectbox("Custo (CMV)", cols_validas, index=get_idx(cols_validas, "CMV"))
            col_preco = st.selectbox("Preço de Venda (Usado)", cols_validas, index=get_idx(cols_validas, "Preço Usado"))
            col_frete = st.selectbox("Frete Manual (>79)", cols_validas, index=get_idx(cols_validas, "Frete do anúncio"))
            col_taxa = st.selectbox("Taxa ML (%)", cols_validas, index=get_idx(cols_validas, "TX ML"))
            col_desc = st.selectbox("Desconto (%)", cols_validas, index=get_idx(cols_validas, "Desconto"))
            col_bonus = st.selectbox("Bônus / Rebate", cols_validas, index=get_idx(cols_validas, "Bônus"))
            
            st.info(f"Prévia do Preço lido: {df_preview[col_preco].iloc[0]}")

            if st.button("✅ Importar com este Mapeamento", type="primary"):
                # Lê o arquivo inteiro
                df = xl.parse(aba_selecionada, header=header_row)
                count = 0
                
                for index, row in df.iterrows():
                    try:
                        # Pega valores brutos baseado na escolha do usuário
                        produto = str(row[col_nome])
                        if not produto or produto == 'nan': continue

                        mlb = str(row[col_mlb])
                        
                        # Limpeza Pesada nos Valores
                        cmv = limpar_valor_dinheiro(row[col_cmv])
                        preco_base = limpar_valor_dinheiro(row[col_preco])
                        frete = limpar_valor_dinheiro(row[col_frete])
                        tx_ml = limpar_valor_dinheiro(row[col_taxa])
                        desc = limpar_valor_dinheiro(row[col_desc])
                        bonus = limpar_valor_dinheiro(row[col_bonus])
                        
                        # Defaults
                        if frete == 0: frete = 18.86
                        if tx_ml == 0: tx_ml = 16.5

                        novo_item = {
                            "id": int(time.time() * 1000) + index,
                            "MLB": mlb,
                            "SKU": "",
                            "Produto": produto,
                            "CMV": cmv,
                            "FreteManual": frete,
                            "TaxaML": tx_ml,
                            "Extra": 0.0,
                            "PrecoERP": 0.0, "MargemERP": 0.0,
                            "PrecoBase": preco_base,
                            "DescontoPct": desc,
                            "Bonus": bonus
                        }
                        st.session_state.lista_produtos.append(novo_item)
                        count += 1
                    except: continue
                
                st.toast(f"{count} produtos importados!", icon="🚀")
                time.sleep(1)
                reiniciar_app()
                
        except Exception as e:
            st.error(f"Erro: {e}")

# --- 6. LÓGICA DE NEGÓCIO ---
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
        (taxa_50_79, "Tab. 50-79", 50, 79),
        (taxa_29_50, "Tab. 29-50", 29, 50),
        (taxa_12_29, "Tab. 12-29", 12.5, 29)
    ]:
        custos = custo_base + taxa
        preco = (custos + lucro_alvo_reais) / divisor
        if p_min <= preco < p_max: return preco, nome
    return preco_est_1, "Frete Manual"

# --- 7. CALLBACK ---
def adicionar_produto_action():
    if not st.session_state.n_nome:
        st.toast("Nome obrigatório!", icon="⚠️")
        return

    lucro_alvo = st.session_state.n_erp * (st.session_state.n_merp / 100)
    preco_sug, _ = calcular_preco_sugerido_reverso(
        st.session_state.n_cmv + st.session_state.n_extra,
        lucro_alvo,
        st.session_state.n_taxa,
        imposto_padrao,
        st.session_state.n_frete
    )

    novo_item = {
        "id": int(time.time() * 1000),
        "MLB": st.session_state.n_mlb,
        "SKU": st.session_state.n_sku, 
        "Produto": st.session_state.n_nome,
        "CMV": st.session_state.n_cmv,
        "FreteManual": st.session_state.n_frete,
        "TaxaML": st.session_state.n_taxa,
        "Extra": st.session_state.n_extra,
        "PrecoERP": st.session_state.n_erp,
        "MargemERP": st.session_state.n_merp,
        "PrecoBase": preco_sug,
        "DescontoPct": 0.0,
        "Bonus": 0.0,
    }
    st.session_state.lista_produtos.append(novo_item)
    st.toast("Salvo!", icon="✅")

    st.session_state.n_mlb = ""
    st.session_state.n_sku = "" 
    st.session_state.n_nome = ""
    st.session_state.n_cmv = 0.00
    st.session_state.n_extra = 0.00

# ==============================================================================
# 8. INTERFACE PRINCIPAL
# ==============================================================================

col_t, col_c = st.columns([3, 1])
col_t.title("Precificador")
col_c.caption(f"{len(st.session_state.lista_produtos)} itens")

# --- INPUT CARD ---
st.markdown('<div class="input-card">', unsafe_allow_html=True)

st.text_input("MLB (ID do Anúncio)", key="n_mlb", placeholder="Ex: MLB-12345678")

c1, c2 = st.columns([1, 2])
c1.text_input("SKU (Interno)", key="n_sku", placeholder="Cód.")
c2.text_input("Produto", key="n_nome", placeholder="Nome do item")

c3, c4 = st.columns(2)
c3.number_input("Custo (CMV)", step=0.01, format="%.2f", key="n_cmv")
c4.number_input("Frete (>79)", step=0.01, format="%.2f", key="n_frete")

st.markdown("<hr style='margin: 15px 0; border-color: #eee;'>", unsafe_allow_html=True)

c5, c6, c7 = st.columns(3)
c5.number_input("Comissão %", step=0.5, format="%.1f", key="n_taxa")
c6.number_input("Preço ERP", step=0.01, format="%.2f", key="n_erp")
c7.number_input("Margem ERP %", step=1.0, format="%.1f", key="n_merp")

st.write("")
st.button("✨ Precificar e Adicionar", type="primary", use_container_width=True, on_click=adicionar_produto_action)
st.markdown('</div>', unsafe_allow_html=True)

# --- FEED ---
if st.session_state.lista_produtos:
    
    total_itens = len(st.session_state.lista_produtos)
    
    for i in range(total_itens - 1, -1, -1):
        item = st.session_state.lista_produtos[i]
        
        # --- CÁLCULO ---
        preco_base_calc = item['PrecoBase']
        desc_calc = item['DescontoPct']
        preco_final_calc = preco_base_calc * (1 - (desc_calc / 100))
        
        nome_frete_real, valor_frete_real = identificar_faixa_frete(preco_final_calc)
        if nome_frete_real == "manual": valor_frete_real = item['FreteManual']
        
        imposto_val = preco_final_calc * (imposto_padrao / 100)
        comissao_val = preco_final_calc * (item['TaxaML'] / 100)
        custos_totais = item['CMV'] + item['Extra'] + valor_frete_real + imposto_val + comissao_val
        lucro_final = preco_final_calc - custos_totais + item['Bonus']
        margem_final = (lucro_final / preco_final_calc * 100) if preco_final_calc > 0 else 0
        
        # --- CORES ---
        if margem_final < 8.0:
            pill_class = "pill-red"
            box_style = "background-color: #FEF2F2; color: #DC2626; border: 1px solid #FEE2E2;"
        elif 8.0 <= margem_final < 15.0:
            pill_class = "pill-yellow"
            box_style = "background-color: #FFFBEB; color: #B45309; border: 1px solid #FCD34D;"
        else:
            pill_class = "pill-green"
            box_style = "background-color: #E6FFFA; color: #047857; border: 1px solid #D1FAE5;"

        txt_pill = f"{margem_final:.1f}%"
        txt_lucro_reais = f"R$ {lucro_final:.2f}"
        if lucro_final > 0: txt_lucro_reais = "+ " + txt_lucro_reais

        # --- CARD ---
        sku_display = item.get('SKU', '-')
        
        st.markdown(f"""
        <div class="feed-card">
            <div class="card-header">
                <div>
                    <div class="sku-text">{item['MLB']} • {sku_display}</div>
                    <div class="title-text">{item['Produto']}</div>
                </div>
                <div class="{pill_class} pill">{txt_pill}</div>
            </div>
            <div class="card-body">
                <div style="font-size: 11px; color:#888; font-weight:600;">PREÇO DE VENDA</div>
                <div class="price-hero">R$ {preco_final_calc:.2f}</div>
                <div style="font-size: 13px; color:#555;">Lucro Líquido: <b>{txt_lucro_reais}</b></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("⚙️ Editar e Detalhes"):
            st.caption("AJUSTES RÁPIDOS")
            
            def update_item(idx=i, key_id=item['id'], field=None, key_st=None):
                st.session_state.lista_produtos[idx][field] = st.session_state[key_st]

            ec1, ec2, ec3 = st.columns(3)
            ec1.number_input("Preço Tabela", value=float(item['PrecoBase']), step=0.5, key=f"pb_{item['id']}", 
                             on_change=update_item, args=(i, item['id'], 'PrecoBase', f"pb_{item['id']}"))
            
            ec2.number_input("Desconto %", value=float(item['DescontoPct']), step=0.5, key=f"dc_{item['id']}", 
                             on_change=update_item, args=(i, item['id'], 'DescontoPct', f"dc_{item['id']}"))
            
            ec3.number_input("Rebate (R$)", value=float(item['Bonus']), step=0.01, key=f"bn_{item['id']}", 
                             on_change=update_item, args=(i, item['id'], 'Bonus', f"bn_{item['id']}"))
            
            st.divider()
            
            # --- DRE ---
            st.caption("EXTRATO FINANCEIRO")
            
            r1, r2 = st.columns([3, 1])
            r1.write("(+) Preço Tabela")
            r2.write(f"R$ {preco_base_calc:.2f}")
            
            if desc_calc > 0:
                r1, r2 = st.columns([3, 1])
                r1.markdown(f":red[(-) Desconto ({desc_calc}%) ]")
                r2.markdown(f":red[- R$ {preco_base_calc - preco_final_calc:.2f}]")
            
            st.markdown("---")
            
            r1, r2 = st.columns([3, 1])
            r1.markdown("**(=) RECEITA BRUTA**")
            r2.markdown(f"**R$ {preco_final_calc:.2f}**")
            
            st.write("") 
            
            custos = [
                (f"Impostos ({imposto_padrao}%)", imposto_val),
                (f"Comissão ({item['TaxaML']}%)", comissao_val),
                (f"Frete ({nome_frete_real})", valor_frete_real),
                ("Custo CMV", item['CMV']),
                ("Extras", item['Extra'])
            ]
            
            for lbl, val in custos:
                c_lbl, c_val = st.columns([3, 1])
                c_lbl.caption(f"(-) {lbl}")
                c_val.caption(f"- R$ {val:.2f}")
            
            if item['Bonus'] > 0:
                st.write("")
                r1, r2 = st.columns([3, 1])
                r1.markdown(":green[(+) Rebate / Bônus]")
                r2.markdown(f":green[+ R$ {item['Bonus']:.2f}]")
            
            st.write("")
            
            # --- CAIXA DE DESTAQUE DO RESULTADO ---
            st.markdown(f"""
            <div style="{box_style} padding: 15px; border-radius: 10px; display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: 700; font-size: 14px;">LUCRO LÍQUIDO</span>
                <span style="font-weight: 800; font-size: 18px;">R$ {lucro_final:.2f}</span>
            </div>
            """, unsafe_allow_html=True)
            
            st.write("")
            
            def deletar(idx_del=i):
                del st.session_state.lista_produtos[idx_del]
                
            st.button("Remover Item", key=f"del_{item['id']}", on_click=deletar)

    # Footer
    st.divider()
    col_d, col_c = st.columns(2)
    
    dados_csv = []
    for it in st.session_state.lista_produtos:
        pf = it['PrecoBase'] * (1 - it['DescontoPct']/100)
        _, fr = identificar_faixa_frete(pf)
        if _ == "manual": fr = it['FreteManual']
        luc = pf - (it['CMV'] + it['Extra'] + fr + (pf*(imposto_padrao+it['TaxaML'])/100)) + it['Bonus']
        dados_csv.append({
            "MLB": it['MLB'], 
            "SKU": it.get('SKU', ''), 
            "Produto": it['Produto'], 
            "Preco Final": pf, 
            "Lucro": luc
        })
        
    df_final = pd.DataFrame(dados_csv)
    csv = df_final.to_csv(index=False).encode('utf-8')
    
    col_d.download_button("📥 Baixar Excel", csv, "precificacao_2026.csv", "text/csv", use_container_width=True)
    
    def limpar_tudo(): st.session_state.lista_produtos = []
    col_c.button("🗑️ Limpar Tudo", on_click=limpar_tudo, use_container_width=True)

else:
    st.markdown("""
    <div style="text-align: center; color: #BBB; padding: 40px;">
        <h3 style="color: #DDD;">Lista Vazia</h3>
        Preencha os dados acima para começar.
    </div>
    """, unsafe_allow_html=True)

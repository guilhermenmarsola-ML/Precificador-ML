import streamlit as st
import pandas as pd
import time

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Precificador ML - V24", layout="wide", page_icon="")

# --- ESTADO E INICIALIZAÇÃO ---
if 'lista_produtos' not in st.session_state:
    st.session_state.lista_produtos = []

def init_state(key, value):
    if key not in st.session_state:
        st.session_state[key] = value

# Variáveis
init_state('n_mlb', '')
init_state('n_nome', '')
init_state('n_cmv', 32.57)
init_state('n_extra', 0.00)
# Persistentes
init_state('n_frete', 18.86)
init_state('n_taxa', 16.5)
init_state('n_erp', 85.44)
init_state('n_merp', 20.0)

# --- CSS: APPLE DESIGN SYSTEM (FORÇANDO MODO CLARO) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* FORÇAR MODO CLARO GERAL */
    [data-testid="stAppViewContainer"] {
        background-color: #F2F2F7 !important; /* Cinza Fundo Apple */
    }
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
    }
    [data-testid="stHeader"] {
        background-color: rgba(0,0,0,0) !important;
    }

    /* Textos Gerais - Forçar Escuro */
    h1, h2, h3, h4, p, div, span, label {
        color: #1D1D1F !important;
        font-family: 'Inter', sans-serif !important;
    }
    
    /* Inputs - Fundo Branco e Texto Preto */
    div[data-testid="stTextInput"] input, div[data-testid="stNumberInput"] input {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 1px solid #D1D1D6 !important;
        border-radius: 8px !important;
    }
    div[data-testid="stNumberInput"] button {
        color: #000000 !important;
    }

    /* Card Principal (Inputs) */
    .apple-card {
        background-color: #FFFFFF;
        border-radius: 18px;
        padding: 20px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        margin-bottom: 20px;
        border: 1px solid #E5E5EA;
    }

    /* Card de Produto na Lista */
    .product-card {
        background-color: #FFFFFF;
        border-radius: 14px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
        border: 1px solid #E5E5EA;
    }
    
    /* Destaques de Texto */
    .product-title { font-size: 16px; font-weight: 600; color: #000000 !important; margin-bottom: 4px; }
    .product-sku { font-size: 12px; color: #86868B !important; text-transform: uppercase; }
    
    .price-display { font-size: 14px; color: #1D1D1F !important; font-weight: 500; }
    .profit-display-pos { color: #34C759 !important; font-weight: 700; } /* Verde */
    .profit-display-neg { color: #FF3B30 !important; font-weight: 700; } /* Vermelho */

    /* Botão Principal */
    div.stButton > button[kind="primary"] {
        background-color: #0071E3 !important; /* Azul Apple */
        color: white !important;
        border-radius: 12px !important;
        padding: 12px 24px;
        font-weight: 600;
        font-size: 16px;
        border: none;
        width: 100%;
        height: 50px;
    }
    
    /* Botões Pequenos (Lixeira) */
    div.stButton > button[kind="secondary"] {
        background-color: #F5F5F7 !important;
        color: #FF3B30 !important;
        border: none;
        border-radius: 8px;
    }

    /* DRE Visual */
    .dre-line {
        display: flex; justify-content: space-between;
        padding: 6px 0; border-bottom: 1px dashed #E5E5EA;
        font-size: 13px;
        color: #1D1D1F !important;
    }
    .dre-sub { color: #86868B !important; font-size: 12px; }
    
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.header("Ajustes")
    imposto_padrao = st.number_input("Impostos (%)", value=27.0, step=0.5)
    
    with st.expander("Regras de Frete", expanded=True):
        taxa_12_29 = st.number_input("Faixa 12-29", value=6.25)
        taxa_29_50 = st.number_input("Faixa 29-50", value=6.50)
        taxa_50_79 = st.number_input("Faixa 50-79", value=6.75)
        taxa_minima = st.number_input("Mínimo", value=3.25)

# --- LÓGICA ---
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

    # Limpeza
    st.session_state.n_mlb = ""
    st.session_state.n_nome = ""
    st.session_state.n_cmv = 0.00
    st.session_state.n_extra = 0.00

# ==============================================================================
# INTERFACE PRINCIPAL
# ==============================================================================

st.title("Precificação ML")

# 1. BLOCO DE INPUT
st.markdown('<div class="apple-card">', unsafe_allow_html=True)
st.markdown("### Novo Item")

c1, c2 = st.columns(2)
c1.text_input("Código (SKU)", key="n_mlb", placeholder="Opcional")
c2.number_input("Custo (CMV)", step=0.01, format="%.2f", key="n_cmv")

st.text_input("Nome do Produto", key="n_nome", placeholder="Ex: Lona 4x4")

c3, c4 = st.columns(2)
c3.number_input("Frete Manual (>79)", step=0.01, format="%.2f", key="n_frete")
c4.number_input("Extras / Emb.", step=0.01, format="%.2f", key="n_extra")

st.markdown("---")
st.markdown("### Estratégia")

c5, c6 = st.columns(2)
c5.number_input("Comissão ML %", step=0.5, format="%.1f", key="n_taxa")
c6.number_input("Margem ERP %", step=1.0, format="%.1f", key="n_merp")

st.number_input("Preço Base ERP (R$)", step=0.01, format="%.2f", key="n_erp")

# SUGESTÃO
lucro_alvo_view = st.session_state.n_erp * (st.session_state.n_merp / 100)
preco_sug_view, nome_frete_view = calcular_preco_sugerido_reverso(
    st.session_state.n_cmv + st.session_state.n_extra, 
    lucro_alvo_view, 
    st.session_state.n_taxa, 
    imposto_padrao, 
    st.session_state.n_frete
)

# Estilo inline para garantir cor preta
st.markdown(f"""
<div style="background-color: #F2F2F7; padding: 15px; border-radius: 12px; display: flex; gap: 10px; margin-top: 10px; border: 1px solid #D1D1D6;">
    <div style="flex: 1; text-align: center;">
        <div style="font-size: 10px; color: #86868B; font-weight: bold; text-transform: uppercase;">META (R$)</div>
        <div style="font-size: 20px; color: #1D1D1F; font-weight: bold;">{lucro_alvo_view:.2f}</div>
    </div>
    <div style="flex: 1; text-align: center; background-color: #E3F2FD; border-radius: 8px;">
        <div style="font-size: 10px; color: #0071E3; font-weight: bold; text-transform: uppercase; margin-top: 5px;">SUGERIDO</div>
        <div style="font-size: 20px; color: #0071E3; font-weight: bold;">{preco_sug_view:.2f}</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.write("")
st.button("Adicionar à Lista", type="primary", use_container_width=True, on_click=adicionar_produto_action)
st.markdown('</div>', unsafe_allow_html=True)

# 2. LISTA DE PRODUTOS
if st.session_state.lista_produtos:
    st.markdown("### Seus Produtos")
    
    for i, item in enumerate(reversed(st.session_state.lista_produtos)):
        
        # Cálculos
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
        
        # CARD
        st.markdown('<div class="product-card">', unsafe_allow_html=True)
        
        # Cabeçalho
        col_txt, col_del = st.columns([4, 1])
        with col_txt:
            st.markdown(f"""
            <div class="product-sku">{item['MLB']}</div>
            <div class="product-title">{item['Produto']}</div>
            """, unsafe_allow_html=True)
        with col_del:
            def deletar(idx=i): del st.session_state.lista_produtos[idx]
            st.button("✕", key=f"del_{item['id']}", on_click=deletar)

        # Resumo
        st.markdown("---")
        kp1, kp2 = st.columns(2)
        
        cor_lucro = "profit-display-pos" if lucro_final > 0 else "profit-display-neg"
        
        kp1.markdown(f"<div class='price-display'>Venda<br><b>R$ {preco_final_calc:.2f}</b></div>", unsafe_allow_html=True)
        kp2.markdown(f"<div class='price-display'>Lucro<br><span class='{cor_lucro}'>R$ {lucro_final:.2f}</span></div>", unsafe_allow_html=True)
        
        # EXPANDER COM DRE (Agora está aqui!)
        with st.expander("Editar & Ver DRE Completa"):
            
            # Edição
            ec1, ec2 = st.columns(2)
            
            def update_preco(idx=i, k=f"pb_{item['id']}"): st.session_state.lista_produtos[idx]['PrecoBase'] = st.session_state[k]
            def update_desc(idx=i, k=f"dc_{item['id']}"): st.session_state.lista_produtos[idx]['DescontoPct'] = st.session_state[k]
            def update_bonus(idx=i, k=f"bn_{item['id']}"): st.session_state.lista_produtos[idx]['Bonus'] = st.session_state[k]
            def update_cmv(idx=i, k=f"cmv_{item['id']}"): st.session_state.lista_produtos[idx]['CMV'] = st.session_state[k]

            ec1.number_input("Preço Tabela", value=float(item['PrecoBase']), step=0.5, key=f"pb_{item['id']}", on_change=update_preco)
            ec2.number_input("Desconto %", value=float(item['DescontoPct']), step=0.5, key=f"dc_{item['id']}", on_change=update_desc)
            
            ec3, ec4 = st.columns(2)
            ec3.number_input("Bônus R$", value=float(item['Bonus']), step=0.01, key=f"bn_{item['id']}", on_change=update_bonus)
            ec4.number_input("CMV", value=float(item['CMV']), step=0.01, key=f"cmv_{item['id']}", on_change=update_cmv)
            
            st.divider()
            
            # --- DRE DENTRO DO CARD ---
            st.caption("DEMONSTRATIVO (DRE)")
            
            st.markdown(f"""
            <div class="dre-line"><span>(+) Preço Tabela</span><span>R$ {preco_base_calc:.2f}</span></div>
            """, unsafe_allow_html=True)
            
            if desc_calc > 0:
                st.markdown(f"""
                <div class="dre-line" style="color: #FF3B30 !important;"><span>(-) Desconto ({desc_calc}%)</span><span>- R$ {preco_base_calc - preco_final_calc:.2f}</span></div>
                """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div class="dre-line" style="font-weight: 700; background-color: #F2F2F7; padding: 5px;"><span>(=) PREÇO VENDA</span><span>R$ {preco_final_calc:.2f}</span></div>
            <div class="dre-line"><span class="dre-sub">(-) Impostos ({imposto_padrao}%)</span><span class="dre-sub">- R$ {imposto_val:.2f}</span></div>
            <div class="dre-line"><span class="dre-sub">(-) Comissão ML ({item['TaxaML']}%)</span><span class="dre-sub">- R$ {comissao_val:.2f}</span></div>
            <div class="dre-line"><span class="dre-sub">(-) Frete ({nome_frete_real})</span><span class="dre-sub">- R$ {valor_frete_real:.2f}</span></div>
            <div class="dre-line"><span class="dre-sub">(-) Custo CMV</span><span class="dre-sub">- R$ {item['CMV']:.2f}</span></div>
            <div class="dre-line"><span class="dre-sub">(-) Extras</span><span class="dre-sub">- R$ {item['Extra']:.2f}</span></div>
            """, unsafe_allow_html=True)
            
            if item['Bonus'] > 0:
                st.markdown(f"""
                <div class="dre-line" style="color: #34C759 !important;"><span>(+) Bônus / Rebate</span><span>+ R$ {item['Bonus']:.2f}</span></div>
                """, unsafe_allow_html=True)
                
            cor_final_hex = "#34C759" if lucro_final > 0 else "#FF3B30"
            st.markdown(f"""
            <div style="margin-top: 10px; padding-top: 10px; border-top: 2px solid #D1D1D6; display: flex; justify-content: space-between; font-weight: 800; font-size: 16px; color: {cor_final_hex};">
                <span>RESULTADO</span>
                <span>R$ {lucro_final:.2f}</span>
            </div>
            <div style="text-align: right; font-size: 12px; color: {cor_final_hex};">Margem: {margem_final:.1f}%</div>
            """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # Footer
    st.write("")
    df_final = pd.DataFrame(st.session_state.lista_produtos)
    csv = df_final.to_csv(index=False).encode('utf-8')
    st.download_button("Baixar Planilha", csv, "precificacao.csv", "text/csv", use_container_width=True)
    
    def limpar_tudo(): st.session_state.lista_produtos = []
    if st.button("Limpar Tudo", on_click=limpar_tudo, use_container_width=True): pass

else:
    st.markdown("""
    <div style="text-align: center; color: #86868B; padding: 40px;">
        Adicione produtos para começar.
    </div>
    """, unsafe_allow_html=True)

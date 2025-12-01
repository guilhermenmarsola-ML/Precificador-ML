import streamlit as st
import pandas as pd

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Gerenciador ML - V5 (Promoções)", layout="wide")

if 'lista_produtos' not in st.session_state:
    st.session_state.lista_produtos = []

# --- CSS (ESTILO) ---
st.markdown("""
<style>
    .metric-card { background-color: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #dee2e6; }
    .promo-card { background-color: #e3f2fd; padding: 10px; border-radius: 8px; border-left: 5px solid #2196f3; }
    .dre-line { border-bottom: 1px solid #ddd; padding: 5px 0; display: flex; justify-content: space-between; }
    .dre-total { font-weight: bold; background-color: #eee; padding: 10px; border-radius: 5px; margin-top: 5px; }
    .positive { color: #28a745; font-weight: bold; }
    .negative { color: #dc3545; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR: REGRAS ---
st.sidebar.header("⚙️ Regras Globais")
imposto_padrao = st.sidebar.number_input("Impostos (%)", value=27.0, step=0.5, format="%.2f")

st.sidebar.markdown("### 🚚 Frete ML (< R$ 79)")
taxa_12_29 = st.sidebar.number_input("R$ 12,50 a 29,00", value=6.25)
taxa_29_50 = st.sidebar.number_input("R$ 29,00 a 50,00", value=6.50)
taxa_50_79 = st.sidebar.number_input("R$ 50,00 a 79,00", value=6.75)
taxa_minima = st.sidebar.number_input("Abaixo de R$ 12,50", value=3.25)

# --- FUNÇÃO DE FRETE INTELIGENTE ---
def calcular_frete_real(preco_final, frete_manual_input):
    if preco_final >= 79.00:
        return frete_manual_input, "Frete Manual (>79)"
    elif 50.00 <= preco_final < 79.00:
        return taxa_50_79, "Tab. (50-79)"
    elif 29.00 <= preco_final < 50.00:
        return taxa_29_50, "Tab. (29-50)"
    elif 12.50 <= preco_final < 29.00:
        return taxa_12_29, "Tab. (12-29)"
    else:
        return taxa_minima, "Tab. Mínima (<12)"

st.title("🛒 Precificador ML Pro (Com Promoções)")

# --- 1. DADOS CADASTRAIS ---
with st.container():
    c1, c2, c3, c4 = st.columns([1, 2, 1, 1])
    with c1: codigo_mlb = st.text_input("Código MLB", "MLB-")
    with c2: nome_produto = st.text_input("Produto", "Lona Plástica 4x10")
    with c3: cmv = st.number_input("Custo (CMV)", value=32.57, step=0.01, format="%.2f")
    with c4: frete_anuncio = st.number_input("Frete Cheio (>79)", value=17.23, step=0.01, format="%.2f")

    col_taxas, col_meta = st.columns(2)
    with col_taxas:
        cc1, cc2 = st.columns(2)
        taxa_ml = cc1.number_input("Comissão ML (%)", value=16.5, step=0.5, format="%.1f")
        custo_extra = cc2.number_input("Embalagem (R$)", value=0.00, step=0.01, format="%.2f")
        
    with col_meta:
        c_erp1, c_erp2 = st.columns(2)
        preco_erp = c_erp1.number_input("Preço ERP (R$)", value=0.00, step=0.01, format="%.2f", help="Apenas referência")
        margem_erp = c_erp2.number_input("Margem ERP (%)", value=20.0, step=1.0, format="%.1f")
        lucro_alvo = preco_erp * (margem_erp / 100) if preco_erp > 0 else 0

# --- 2. PREÇO BASE E SIMULAÇÃO ---
st.markdown("---")
st.subheader("⚖️ Definição de Preço e Promoção")

col_input, col_promo = st.columns([1, 1.5])

with col_input:
    # Este é o preço "Cheio" (DE)
    preco_base = st.number_input(
        "Preço Base / Tabela (DE:)", 
        value=32.57, 
        step=0.01, 
        format="%.2f",
        help="Preço original antes do desconto"
    )

with col_promo:
    st.markdown("<div class='promo-card'>", unsafe_allow_html=True)
    st.markdown("<b>⚡ Configurar Promoção / Rebate</b>", unsafe_allow_html=True)
    
    cp1, cp2 = st.columns(2)
    desconto_pct = cp1.number_input("% Desconto", value=13.0, step=0.5, format="%.1f")
    bonus_ml = cp2.number_input("Bônus ML (R$)", value=0.52, step=0.01, format="%.2f", help="Valor que o ML devolve/abate")
    
    # Cálculo do Preço PROMOCIONAL (POR)
    preco_final_venda = preco_base * (1 - (desconto_pct / 100))
    st.markdown(f"Preço Final de Venda (POR): <b style='font-size:18px'>R$ {preco_final_venda:.2f}</b>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# --- 3. MOTOR DE CÁLCULO FINAL ---

# A. Identifica Frete baseado no PREÇO FINAL (Com Desconto)
frete_aplicado, nome_frete = calcular_frete_real(preco_final_venda, frete_anuncio)

# B. Custos Variáveis sobre o preço de venda
imposto_reais = preco_final_venda * (imposto_padrao / 100)
comissao_reais = preco_final_venda * (taxa_ml / 100)

# C. Lucro Líquido
# Lucro = Receita - (CMV + Frete + Extra + Imposto + Comissão) + BONUS
custos_totais = cmv + custo_extra + frete_aplicado + imposto_reais + comissao_reais
lucro_liquido = preco_final_venda - custos_totais + bonus_ml
margem_final = (lucro_liquido / preco_final_venda * 100) if preco_final_venda > 0 else 0

# --- 4. EXIBIÇÃO DE RESULTADOS ---
st.markdown("### 📊 Resultado Financeiro")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Frete Aplicado", f"R$ {frete_aplicado:.2f}", nome_frete)
k2.metric("Comissão + Imposto", f"R$ {(imposto_reais + comissao_reais):.2f}")
k3.metric("Bônus (Entrada)", f"R$ {bonus_ml:.2f}", "Rebate ML", delta_color="off")

cor_lucro = "normal"
if lucro_alvo > 0:
    diff = lucro_liquido - lucro_alvo
    if diff < -0.1: cor_lucro = "inverse"

k4.metric("Lucro Líquido", f"R$ {lucro_liquido:.2f}", f"{margem_final:.1f}%", delta_color=cor_lucro)

# --- 5. BOTÃO DRE (DETALHAMENTO) ---
st.markdown("<br>", unsafe_allow_html=True)
if st.button("📄 Verificar DRE Detalhado"):
    st.markdown("### 📑 Demonstrativo do Resultado (DRE)")
    
    # HTML para o DRE
    html_dre = f"""
    <div style='background-color: white; padding: 20px; border-radius: 10px; border: 1px solid #ddd; max-width: 600px;'>
        <div class='dre-line'><span>(+) Preço Tabela</span> <span>R$ {preco_base:.2f}</span></div>
        <div class='dre-line' style='color: #dc3545;'><span>(-) Desconto ({desconto_pct}%)</span> <span>- R$ {(preco_base - preco_final_venda):.2f}</span></div>
        <div class='dre-line' style='font-weight:bold; background:#f9f9f9'><span>(=) Preço Venda (Fat)</span> <span>R$ {preco_final_venda:.2f}</span></div>
        <br>
        <div class='dre-line'><span>(-) Impostos ({imposto_padrao}%)</span> <span>- R$ {imposto_reais:.2f}</span></div>
        <div class='dre-line'><span>(-) Comissão ML ({taxa_ml}%)</span> <span>- R$ {comissao_reais:.2f}</span></div>
        <div class='dre-line'><span>(-) Frete ({nome_frete})</span> <span>- R$ {frete_aplicado:.2f}</span></div>
        <div class='dre-line'><span>(-) Custo Produto (CMV)</span> <span>- R$ {cmv:.2f}</span></div>
        <div class='dre-line'><span>(-) Custos Extras</span> <span>- R$ {custo_extra:.2f}</span></div>
        <br>
        <div class='dre-line' style='color: #28a745;'><span>(+) Bônus / Rebate ML</span> <span>+ R$ {bonus_ml:.2f}</span></div>
        <div class='dre-total'>
            <span>(=) LUCRO LÍQUIDO</span>
            <span style='float:right; color: {"#28a745" if lucro_liquido > 0 else "#dc3545"}'>R$ {lucro_liquido:.2f} ({margem_final:.1f}%)</span>
        </div>
    </div>
    """
    st.markdown(html_dre, unsafe_allow_html=True)

# --- 6. LISTA ---
st.markdown("---")
btn_col, _ = st.columns([1, 3])
if btn_col.button("➕ Adicionar à Lista"):
    if nome_produto:
        novo_item = {
            "MLB": codigo_mlb,
            "Produto": nome_produto,
            "Preço Base": preco_base,
            "Desc %": desconto_pct,
            "Preço Promo": round(preco_final_venda, 2),
            "Frete Pago": frete_aplicado,
            "Bônus ML": bonus_ml,
            "Lucro Real": round(lucro_liquido, 2),
            "Margem %": round(margem_final, 1)
        }
        st.session_state.lista_produtos.append(novo_item)
        st.success(f"{nome_produto} adicionado!")
    else:
        st.warning("Preencha o nome do produto.")

if st.session_state.lista_produtos:
    st.write("### 📋 Itens Precificados")
    df = pd.DataFrame(st.session_state.lista_produtos)
    st.dataframe(df, use_container_width=True)
    
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Baixar CSV Completo", csv, "precificacao_promo_ml.csv", "text/csv")
    
    if st.button("Limpar Lista"):
        st.session_state.lista_produtos = []
        st.experimental_rerun()



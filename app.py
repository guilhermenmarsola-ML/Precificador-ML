import streamlit as st
import pandas as pd

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Gerenciador ML - V3 (Frete Dinâmico)", layout="wide")

if 'lista_produtos' not in st.session_state:
    st.session_state.lista_produtos = []

# --- CSS ---
st.markdown("""
<style>
    .metric-card { background-color: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #dee2e6; }
    .highlight-green { color: #28a745; font-weight: bold; }
    .highlight-red { color: #dc3545; font-weight: bold; }
    .small-font { font-size: 14px; color: #666; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR (CONFIGURAÇÕES GLOBAIS) ---
st.sidebar.header("⚙️ Taxas Globais")
imposto_padrao = st.sidebar.number_input("Impostos Médios (%)", value=27.0, step=0.5, format="%.2f")

st.sidebar.markdown("### 🚚 Regra de Frete (< R$ 79)")
st.sidebar.info("Custo fixo aplicado quando o preço é menor que R$ 79,00.")
taxa_12_29 = st.sidebar.number_input("R$ 12,50 a R$ 29,00", value=6.25, step=0.01)
taxa_29_50 = st.sidebar.number_input("R$ 29,00 a R$ 50,00", value=6.50, step=0.01)
taxa_50_79 = st.sidebar.number_input("R$ 50,00 a R$ 79,00", value=6.75, step=0.01)
taxa_minima = st.sidebar.number_input("Abaixo de R$ 12,50", value=3.12, step=0.01, help="Metade da taxa básica")

st.sidebar.markdown("---")
st.sidebar.caption("Versão 3.0 - Frete Inteligente")

# --- FUNÇÃO DE CÁLCULO DE CUSTO DE FRETE ---
def obter_custo_frete(preco_venda, frete_manual_input):
    """
    Define qual custo de envio será descontado do vendedor baseada no preço final.
    Regra: Acima de 79 usa o manual. Abaixo usa a taxa fixa por faixa.
    """
    if preco_venda >= 79.00:
        return frete_manual_input, "Frete Grátis (Manual)"
    elif 50.00 <= preco_venda < 79.00:
        return taxa_50_79, "Taxa Fixa (50-79)"
    elif 29.00 <= preco_venda < 50.00:
        return taxa_29_50, "Taxa Fixa (29-50)"
    elif 12.50 <= preco_venda < 29.00:
        return taxa_12_29, "Taxa Fixa (12-29)"
    else:
        return taxa_minima, "Taxa Mínima (<12.50)"

# --- TÍTULO ---
st.title("🛒 Gerenciador Precificação ML (Lógica Dinâmica)")

# --- INPUTS ---
with st.container():
    c1, c2, c3, c4 = st.columns([1, 2, 1, 1])
    with c1:
        codigo_mlb = st.text_input("Código MLB", "MLB-")
    with c2:
        nome_produto = st.text_input("Nome do Produto", "Produto Teste")
    with c3:
        cmv = st.number_input("Custo (CMV) R$", value=36.59, step=0.01, format="%.2f", min_value=0.0)
    with c4:
        preco_atual = st.number_input("Preço Atual (R$)", value=0.0, step=0.01, format="%.2f", help="Preço praticado hoje")

    st.markdown("---")
    
    col_custos, col_estrategia = st.columns(2)
    
    with col_custos:
        st.subheader("📦 Taxas e Frete Manual")
        cc1, cc2 = st.columns(2)
        with cc1:
            taxa_ml = st.number_input("Comissão ML (%)", value=16.5, step=0.5, format="%.1f")
        with cc2:
            frete_anuncio = st.number_input("Frete (> R$ 79) R$", value=18.86, step=0.01, format="%.2f", help="Valor cobrado pelo ML se o produto for acima de R$ 79")
        
        custo_extra = st.number_input("Embalagem/Outros (R$)", value=0.0, step=0.01, format="%.2f")
            
    with col_estrategia:
        st.subheader("🎯 Meta (Estratégia ERP)")
        # Focando na estratégia ERP que você usa
        tipo_meta = st.radio("Meta:", ("Lucro Fixo (ERP)", "Margem %"), horizontal=True)
        
        lucro_alvo_reais = 0.0
        meta_percentual = 0.0
        
        if tipo_meta == "Lucro Fixo (ERP)":
            cm1, cm2 = st.columns(2)
            p_erp = cm1.number_input("Preço Base ERP (R$)", value=85.44, step=0.01, format="%.2f")
            m_erp = cm2.number_input("Margem ERP (%)", value=20.0, step=1.0, format="%.1f")
            lucro_alvo_reais = p_erp * (m_erp / 100)
            st.success(f"💰 Lucro Alvo: **R$ {lucro_alvo_reais:.2f}**")
        else:
            meta_percentual = st.number_input("Margem Líquida Alvo (%)", value=20.0)

# --- MOTOR DE CÁLCULO (Iterativo) ---
# Precisamos calcular iterativamente pois o frete muda o preço, e o preço muda o frete.

def calcular_preco_sugerido(target_lucro_reais=None, target_margem_pct=None):
    # Tentativa 1: Assume que o preço vai ser Alto (>79) e usa o Frete Manual
    custo_frete_temp = frete_anuncio 
    
    # Define o custo fixo base
    custos_base = cmv + custo_extra + custo_frete_temp
    
    divisor = 0
    preco_estimado = 0
    
    if target_lucro_reais is not None:
        numerador = custos_base + target_lucro_reais
        divisor = 1 - ((taxa_ml + imposto_padrao) / 100)
        preco_estimado = numerador / divisor if divisor > 0 else 0
    else:
        divisor = 1 - ((taxa_ml + imposto_padrao + target_margem_pct) / 100)
        preco_estimado = custos_base / divisor if divisor > 0 else 0

    # Verificação: O preço estimado condiz com o frete usado?
    custo_frete_real, tipo_frete = obter_custo_frete(preco_estimado, frete_anuncio)
    
    # Se o frete real for diferente do usado na estimativa, recalcula
    if custo_frete_real != custo_frete_temp:
        custos_base_2 = cmv + custo_extra + custo_frete_real
        if target_lucro_reais is not None:
            numerador = custos_base_2 + target_lucro_reais
            preco_estimado = numerador / divisor if divisor > 0 else 0
        else:
            preco_estimado = custos_base_2 / divisor if divisor > 0 else 0
            
        # Pega o tipo final de frete
        _, tipo_frete = obter_custo_frete(preco_estimado, frete_anuncio)
        
    return preco_estimado, tipo_frete, custo_frete_real

# Executa o cálculo
preco_sugerido = 0.0
tipo_frete_usado = ""
valor_frete_usado = 0.0

if tipo_meta == "Lucro Fixo (ERP)":
    preco_sugerido, tipo_frete_usado, valor_frete_usado = calcular_preco_sugerido(target_lucro_reais=lucro_alvo_reais)
else:
    preco_sugerido, tipo_frete_usado, valor_frete_usado = calcular_preco_sugerido(target_margem_pct=meta_percentual)

# --- CÁLCULO DOS DADOS ATUAIS (Para Comparação) ---
frete_real_atual, tipo_frete_atual = obter_custo_frete(preco_atual, frete_anuncio)
custos_fixos_atual = cmv + custo_extra + frete_real_atual
impostos_atual = preco_atual * (imposto_padrao / 100)
comissao_atual = preco_atual * (taxa_ml / 100)
lucro_atual = preco_atual - (custos_fixos_atual + impostos_atual + comissao_atual)
margem_atual = (lucro_atual / preco_atual * 100) if preco_atual > 0 else 0

# --- CÁLCULO DOS DADOS SUGERIDOS (Para Exibição) ---
lucro_sugerido = 0
margem_sugerida = 0
if preco_sugerido > 0:
    impostos_sug = preco_sugerido * (imposto_padrao / 100)
    comissao_sug = preco_sugerido * (taxa_ml / 100)
    lucro_sugerido = preco_sugerido - (cmv + custo_extra + valor_frete_usado + impostos_sug + comissao_sug)
    margem_sugerida = (lucro_sugerido / preco_sugerido * 100)

# --- EXIBIÇÃO ---
st.markdown("### 📊 Resultado da Análise")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Preço Atual", f"R$ {preco_atual:.2f}", f"Frete: {tipo_frete_atual}")
k2.metric("Lucro Atual", f"R$ {lucro_atual:.2f}", f"{margem_atual:.1f}% Margem")
k3.metric("Preço Sugerido", f"R$ {preco_sugerido:.2f}", f"Usando: {tipo_frete_usado}", delta_color="off")

cor_meta = "normal"
msg_meta = "Meta Atingida"
if tipo_meta == "Lucro Fixo (ERP)":
    diff = lucro_sugerido - lucro_alvo_reais
    if diff < -0.05: cor_meta = "inverse"
    k4.metric("Lucro no Sugerido", f"R$ {lucro_sugerido:.2f}", f"Alvo: R$ {lucro_alvo_reais:.2f}")
else:
    k4.metric("Margem Sugerida", f"{margem_sugerida:.1f}%")

# --- BOTÃO ADICIONAR ---
st.markdown("---")
col_btn, _ = st.columns([1, 2])
if col_btn.button("➕ Adicionar à Lista de Precificação"):
    if nome_produto:
        novo_item = {
            "MLB": codigo_mlb,
            "Produto": nome_produto,
            "Preço ERP": p_erp if tipo_meta == "Lucro Fixo (ERP)" else 0,
            "Meta Lucro (R$)": round(lucro_alvo_reais, 2),
            "Preço Sugerido": round(preco_sugerido, 2),
            "Lucro Previsto": round(lucro_sugerido, 2),
            "Tipo Frete": tipo_frete_usado,
            "Custo Frete": round(valor_frete_usado, 2),
            "Preço Atual": preco_atual,
            "Diferença": round(preco_sugerido - preco_atual, 2)
        }
        st.session_state.lista_produtos.append(novo_item)
        st.success(f"{nome_produto} adicionado!")
    else:
        st.warning("Preencha o nome do produto.")

# --- TABELA ---
if st.session_state.lista_produtos:
    st.markdown("### 📋 Produtos Salvos")
    df = pd.DataFrame(st.session_state.lista_produtos)
    st.dataframe(df, use_container_width=True)
    
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Baixar Planilha Final", data=csv, file_name="precificacao_ml_v3.csv", mime="text/csv")
    
    if st.button("Limpar Lista"):
        st.session_state.lista_produtos = []
        st.experimental_rerun()

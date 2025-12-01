import streamlit as st
import pandas as pd

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Gerenciador ML - V2", layout="wide")

# Inicializa a lista de produtos na memória do navegador (Session State)
if 'lista_produtos' not in st.session_state:
    st.session_state.lista_produtos = []

# --- CSS (ESTILO) ---
st.markdown("""
<style>
    .metric-card { background-color: #f0f2f6; padding: 15px; border-radius: 8px; border-left: 5px solid #28a745; }
    .stButton>button { width: 100%; background-color: #ffc107; color: black; font-weight: bold; }
    .big-font { font-size: 20px !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR (CONFIGURAÇÕES GLOBAIS) ---
st.sidebar.header("⚙️ Configurações Globais")
imposto_padrao = st.sidebar.number_input("Impostos Médios (%)", value=27.0, step=0.5, format="%.2f")
frete_limite = st.sidebar.number_input("Limite Frete Grátis (R$)", value=79.0, step=1.0, format="%.2f")
custo_fixo_transacao = st.sidebar.number_input("Custo Fixo por Venda (R$)", value=0.0, step=0.01, format="%.2f")
st.sidebar.markdown("---")
st.sidebar.info("Preencha os dados à direita e clique em 'Adicionar' para montar sua lista.")

# --- TÍTULO ---
st.title("🛒 Gerenciador de Precificação ML")

# --- ÁREA DE INPUTS (DADOS DO PRODUTO) ---
with st.container():
    c1, c2, c3, c4 = st.columns([1, 2, 1, 1])
    with c1:
        codigo_mlb = st.text_input("Código MLB", "MLB-")
    with c2:
        nome_produto = st.text_input("Nome do Produto", "")
    with c3:
        # Custo do Produto
        cmv = st.number_input("Custo (CMV) R$", value=0.0, step=0.01, format="%.2f", min_value=0.0)
    with c4:
        # Preço Atual (o que você já pratica)
        preco_atual = st.number_input("Preço Atual (R$)", value=0.0, step=0.01, format="%.2f", min_value=0.0, help="Preço que está no anúncio hoje")

    st.markdown("---")
    
    col_custos, col_estrategia = st.columns(2)
    
    with col_custos:
        st.subheader("📦 Taxas e Custos")
        cc1, cc2 = st.columns(2)
        with cc1:
            taxa_ml = st.number_input("Comissão ML (%)", value=16.5, step=0.5, format="%.1f")
            frete_anuncio = st.number_input("Frete Anúncio (R$)", value=18.90, step=0.01, format="%.2f")
        with cc2:
            custo_extra = st.number_input("Embalagem/Outros (R$)", value=0.0, step=0.01, format="%.2f")
            
    with col_estrategia:
        st.subheader("🎯 Definição de Meta")
        tipo_meta = st.radio("Sua Meta é:", ("Margem %", "Lucro Fixo (ERP)"), horizontal=True)
        
        meta_valor = 0.0
        lucro_alvo_reais = 0.0
        
        if tipo_meta == "Margem %":
            meta_valor = st.number_input("Margem Desejada (%)", value=20.0, step=1.0, format="%.1f")
        else:
            cm1, cm2 = st.columns(2)
            p_erp = cm1.number_input("Preço Base ERP (R$)", value=0.0, step=0.01, format="%.2f")
            m_erp = cm2.number_input("Margem ERP (%)", value=20.0, step=1.0, format="%.1f")
            lucro_alvo_reais = p_erp * (m_erp / 100)
            st.caption(f"Meta: Garantir R$ {lucro_alvo_reais:.2f} de lucro.")

# --- CÁLCULOS (MOTOR MATEMÁTICO) ---

# 1. Calcular Resultados do Preço ATUAL (O que você digitou)
custos_fixos_venda = cmv + frete_anuncio + custo_extra + custo_fixo_transacao
imposto_atual = preco_atual * (imposto_padrao / 100)
comissao_atual = preco_atual * (taxa_ml / 100)
custo_total_atual = custos_fixos_venda + imposto_atual + comissao_atual
lucro_atual = preco_atual - custo_total_atual
margem_atual_pct = (lucro_atual / preco_atual * 100) if preco_atual > 0 else 0

# 2. Calcular Preço SUGERIDO (Engenharia Reversa)
preco_sugerido = 0.0
if tipo_meta == "Margem %":
    divisor = 1 - ((taxa_ml + imposto_padrao + meta_valor) / 100)
    if divisor > 0.0001:
        preco_sugerido = custos_fixos_venda / divisor
else:
    # Meta ERP (Lucro em Reais Fixo)
    numerador = custos_fixos_venda + lucro_alvo_reais
    divisor = 1 - ((taxa_ml + imposto_padrao) / 100)
    if divisor > 0.0001:
        preco_sugerido = numerador / divisor

# Calcular lucro do sugerido para exibir
imposto_sug = preco_sugerido * (imposto_padrao / 100)
comissao_sug = preco_sugerido * (taxa_ml / 100)
lucro_sugerido = preco_sugerido - (custos_fixos_venda + imposto_sug + comissao_sug)
margem_sugerida_pct = (lucro_sugerido / preco_sugerido * 100) if preco_sugerido > 0 else 0

# --- EXIBIÇÃO COMPARATIVA ---
st.markdown("### 📊 Comparativo: Atual vs Sugerido")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

# KPI 1: Preço Atual (Entrada)
kpi1.metric("Preço Atual", f"R$ {preco_atual:.2f}", help="Preço que você informou")

# KPI 2: Lucro Atual (Resultado Real)
cor_delta = "normal" if lucro_atual > 0 else "inverse"
kpi2.metric("Lucro Real (Atual)", f"R$ {lucro_atual:.2f}", f"{margem_atual_pct:.1f}% Margem", delta_color=cor_delta)

# KPI 3: Preço Sugerido (Meta)
kpi3.metric("Preço Sugerido (Meta)", f"R$ {preco_sugerido:.2f}", help="Preço ideal para atingir sua meta")

# KPI 4: Diferença
diff = preco_sugerido - preco_atual
kpi4.metric("Diferença de Preço", f"R$ {diff:.2f}", "Ajuste necessário", delta_color="off")

# --- BOTÃO DE ADICIONAR ---
st.markdown("---")
col_btn, col_blank = st.columns([1, 2])

with col_btn:
    add_btn = st.button("➕ Adicionar Produto à Lista")

if add_btn:
    if nome_produto == "":
        st.warning("Preencha o nome do produto antes de adicionar.")
    else:
        # Cria um dicionário com os dados da linha
        novo_item = {
            "MLB": codigo_mlb,
            "Produto": nome_produto,
            "Preço Atual": round(preco_atual, 2),
            "Lucro Atual (R$)": round(lucro_atual, 2),
            "Margem Atual (%)": round(margem_atual_pct, 1),
            "Preço Sugerido": round(preco_sugerido, 2),
            "Lucro Sugerido (R$)": round(lucro_sugerido, 2),
            "Margem Sugerida (%)": round(margem_sugerida_pct, 1),
            "CMV": cmv,
            "Frete": frete_anuncio
        }
        # Adiciona à memória
        st.session_state.lista_produtos.append(novo_item)
        st.success(f"Produto '{nome_produto}' adicionado com sucesso!")

# --- TABELA DE PRODUTOS ---
if len(st.session_state.lista_produtos) > 0:
    st.markdown("### 📝 Lista de Produtos Precificados")
    
    df_produtos = pd.DataFrame(st.session_state.lista_produtos)
    
    # Mostra a tabela interativa
    st.dataframe(df_produtos, use_container_width=True)
    
    # Botão para baixar CSV (Estilo Planilha)
    csv = df_produtos.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Baixar Lista em Excel (CSV)",
        data=csv,
        file_name='precificacao_ml.csv',
        mime='text/csv',
    )
    
    # Botão para limpar lista
    if st.button("Limpar Lista"):
        st.session_state.lista_produtos = []
        st.experimental_rerun()
else:
    st.info("Sua lista está vazia. Adicione produtos acima.")

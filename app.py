import streamlit as st
import pandas as pd

# Configuração da Página
st.set_page_config(page_title="Calculadora ML - Estratégia ERP", layout="wide")

# --- CSS para visual ---
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #ffc107;
    }
    .stRadio > label {
        font-weight: bold;
        font-size: 18px;
    }
</style>
""", unsafe_allow_html=True)

# --- BARRA LATERAL (Configurações Fixas) ---
st.sidebar.header("⚙️ Taxas Globais")
st.sidebar.info("Configure as taxas que valem para todos os produtos.")

imposto_padrao = st.sidebar.number_input("Impostos Médios (%)", value=27.0, step=0.5, format="%.2f")
frete_limite = st.sidebar.number_input("Limite Frete Grátis (R$)", value=79.0, step=1.0, format="%.2f")
custo_fixo_transacao = st.sidebar.number_input("Custo Fixo por Venda (R$)", value=0.0, step=0.01, format="%.2f")

st.sidebar.markdown("---")
st.sidebar.caption("Versão 1.2 - Correção de Formato")

# --- ÁREA PRINCIPAL ---
st.title("💰 Precificador Mercado Livre (Modo ERP)")
st.markdown("Defina se quer ganhar uma **porcentagem** ou garantir o **lucro em reais do ERP**.")

col1, col2 = st.columns([1, 1.3])

with col1:
    st.subheader("📦 Custos do Produto")
    
    nome_produto = st.text_input("Nome do Produto", "Tela Sombreamento Toldo")
    
    # CORREÇÃO AQUI: Adicionado step=0.01
    cmv = st.number_input("Custo do Produto (CMV) R$", value=36.59, min_value=0.0, step=0.01, format="%.2f")
    
    st.markdown("---")
    st.write("**Taxas do Anúncio**")
    taxa_ml = st.number_input("Comissão ML (%)", value=16.5, step=0.5, format="%.1f")
    
    # CORREÇÃO AQUI: Adicionado step=0.01
    frete_anuncio = st.number_input("Frete do Anúncio (R$)", value=18.86, min_value=0.0, step=0.01, format="%.2f")
    
    tem_embalagem = st.checkbox("Custos Extras (Embalagem)?")
    custo_extra = 0.0
    if tem_embalagem:
        # CORREÇÃO AQUI: Adicionado step=0.01
        custo_extra = st.number_input("Valor Extra (R$)", value=2.0, step=0.01, format="%.2f")

with col2:
    st.subheader("🎯 Definição de Lucro")
    
    # --- SELETOR DE ESTRATÉGIA ---
    estrategia = st.radio(
        "Como você quer precificar?",
        ("Margem % sobre Venda", "Manter Lucro em Reais (ERP)"),
        horizontal=True
    )
    
    st.markdown("---")

    lucro_alvo_reais = 0.0
    margem_alvo_percentual = 0.0

    # LÓGICA CONDICIONAL
    if estrategia == "Margem % sobre Venda":
        margem_alvo_percentual = st.number_input("Margem Líquida Desejada (%)", value=20.0, step=1.0, format="%.1f")
        st.caption(f"O sistema buscará um preço onde sobrem {margem_alvo_percentual}% limpos.")
        
    else: # Estratégia ERP
        c_erp1, c_erp2 = st.columns(2)
        with c_erp1:
            # CORREÇÃO AQUI: Adicionado step=0.01
            preco_erp = st.number_input("Preço de Venda no ERP (R$)", value=85.44, step=0.01, format="%.2f")
        with c_erp2:
            margem_erp = st.number_input("Margem no ERP (%)", value=20.0, step=1.0, format="%.1f")
        
        # Cálculo do Lucro em Reais que você quer "proteger"
        lucro_alvo_reais = preco_erp * (margem_erp / 100)
        
        st.success(f"💰 Lucro Alvo a Garantir: **R$ {lucro_alvo_reais:.2f}**")
        st.caption("O preço sugerido cobrirá custos + taxas + este valor exato em reais.")

    # --- CÁLCULO DO PREÇO SUGERIDO (ENGENHARIA REVERSA) ---
    custos_totais_absolutos = cmv + frete_anuncio + custo_fixo_transacao + custo_extra
    
    if estrategia == "Margem % sobre Venda":
        # Fórmula: Preço = Custos / (1 - (Taxas + Margem))
        divisor = 1 - ((taxa_ml + imposto_padrao + margem_alvo_percentual) / 100)
        if divisor > 0.0001: # Evitar divisão por zero
            preco_sugerido = custos_totais_absolutos / divisor
        else:
            preco_sugerido = 0.0
            st.error("Margem + Taxas ultrapassam 100%.")
            
    else: # Estratégia ERP
        # Fórmula: Preço = (Custos + Lucro em Reais) / (1 - Taxas)
        numerador = custos_totais_absolutos + lucro_alvo_reais
        divisor = 1 - ((taxa_ml + imposto_padrao) / 100)
        
        if divisor > 0.0001: # Evitar divisão por zero
            preco_sugerido = numerador / divisor
        else:
            preco_sugerido = 0.0
            st.error("Taxas ultrapassam 100%.")

    # --- SIMULADOR MANUAL PARA COMPARAÇÃO ---
    st.markdown("---")
    st.write("#### 🔎 Simulador de Resultado")
    
    # CORREÇÃO AQUI: Adicionado step=0.01
    valor_inicial_simulador = float(preco_sugerido) if preco_sugerido > 0 else 100.00
    preco_venda_manual = st.number_input("Preço de Venda Final (R$)", value=valor_inicial_simulador, step=0.01, format="%.2f")

    # DRE DO SIMULADOR
    v_comissao = preco_venda_manual * (taxa_ml / 100)
    v_imposto = preco_venda_manual * (imposto_padrao / 100)
    custo_total_venda = cmv + frete_anuncio + custo_extra + v_comissao + v_imposto + custo_fixo_transacao
    lucro_liquido_final = preco_venda_manual - custo_total_venda
    margem_final = (lucro_liquido_final / preco_venda_manual * 100) if preco_venda_manual > 0 else 0.0

    # EXIBIÇÃO RESULTADOS
    c1, c2, c3 = st.columns(3)
    c1.metric("Preço Sugerido", f"R$ {preco_sugerido:.2f}")
    c2.metric("Lucro Líquido Real", f"R$ {lucro_liquido_final:.2f}")
    
    # Feedback visual se bateu a meta
    if estrategia == "Manter Lucro em Reais (ERP)":
        if lucro_liquido_final >= (lucro_alvo_reais - 0.05): # Tolerância de centavos
            c3.metric("Status", "Meta Atingida ✅", f"Dif: R$ {lucro_liquido_final - lucro_alvo_reais:.2f}")
        else:
            c3.metric("Status", "Abaixo da Meta 🔻", f"Falta: R$ {lucro_alvo_reais - lucro_liquido_final:.2f}", delta_color="inverse")
    else:
        c3.metric("Margem Real", f"{margem_final:.1f}%")

    # DRE VISUAL
    with st.expander("Ver Detalhes dos Cálculos (DRE)", expanded=True):
        st.write(f"""
        | Descrição | Valor |
        | :--- | ---: |
        | **(+) Preço de Venda** | **R$ {preco_venda_manual:.2f}** |
        | (-) Impostos ({imposto_padrao}%) | R$ {v_imposto:.2f} |
        | (-) Comissão ML ({taxa_ml}%) | R$ {v_comissao:.2f} |
        | (-) Frete | R$ {frete_anuncio:.2f} |
        | (-) Custo Produto | R$ {cmv:.2f} |
        | **(=) Lucro Líquido** | **R$ {lucro_liquido_final:.2f}** |
        """)

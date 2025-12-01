import streamlit as st
import pandas as pd

# Configuração da Página
st.set_page_config(page_title="Calculadora de Precificação ML", layout="wide")

# --- CSS para deixar bonito ---
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #ffc107;
    }
    .big-font {
        font-size: 24px !important;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- BARRA LATERAL (Configurações Globais) ---
st.sidebar.header("⚙️ Configurações Globais")
st.sidebar.info("Baseado na aba 'Indicadores para MKP'")

# Valores padrão retirados da sua planilha (Source 1)
imposto_padrao = st.sidebar.number_input("Impostos Médios (%)", value=27.0, step=0.5)
margem_alvo = st.sidebar.number_input("Margem de Lucro Alvo (%)", value=20.0, step=1.0)
frete_limite = st.sidebar.number_input("Limite Frete Grátis (R$)", value=79.0)
custo_fixo_transacao = st.sidebar.number_input("Custo Fixo por Venda (R$)", value=0.0) # Caso tenha taxa fixa

st.sidebar.markdown("---")
st.sidebar.write("Desenvolvido por Gemini")

# --- ÁREA PRINCIPAL ---
st.title("💰 Precificador Mercado Livre Pro")
st.markdown("Simule custos, taxas e encontre o preço de venda ideal.")

col1, col2 = st.columns([1, 1.5])

with col1:
    st.subheader("📝 Dados do Produto")
    
    nome_produto = st.text_input("Nome do Produto", "Ex: Lona Plástica 4x10")
    cmv = st.number_input("Custo do Produto (CMV) R$", value=50.00, min_value=0.0)
    
    st.markdown("---")
    st.write("**Taxas do Anúncio**")
    taxa_ml = st.number_input("Comissão ML (%)", value=16.5, step=0.5, help="Clássico ou Premium")
    frete_anuncio = st.number_input("Frete do Anúncio (R$)", value=18.90, min_value=0.0)
    
    # Checkbox para outros custos
    tem_embalagem = st.checkbox("Incluir Custo de Embalagem?")
    custo_extra = 0.0
    if tem_embalagem:
        custo_extra = st.number_input("Custo Embalagem/Outros (R$)", value=2.0)

with col2:
    st.subheader("📊 Resultados e Análise")
    
    # --- CÁLCULOS MATEMÁTICOS ---
    
    # 1. Definição do Preço de Venda para Análise
    preco_venda_analise = st.number_input("Preço de Venda Atual (Para Teste) R$", value=100.00)
    
    # Cálculo de Custos Totais sobre a Venda
    valor_comissao = preco_venda_analise * (taxa_ml / 100)
    valor_imposto = preco_venda_analise * (imposto_padrao / 100)
    
    custo_total = cmv + frete_anuncio + valor_comissao + valor_imposto + custo_fixo_transacao + custo_extra
    lucro_liquido = preco_venda_analise - custo_total
    margem_real = (lucro_liquido / preco_venda_analise) * 100 if preco_venda_analise > 0 else 0
    
    # 2. Cálculo do Preço Sugerido (Engenharia Reversa)
    # Fórmula: Preço = (Custos Fixos) / (1 - (Taxas% + Impostos% + Margem%))
    # Nota: Frete do anúncio e CMV são valores absolutos, entram no numerador.
    
    divisor = 1 - ((taxa_ml + imposto_padrao + margem_alvo) / 100)
    if divisor <= 0:
        preco_sugerido = 0 # Evitar divisão por zero ou negativo impossível
        st.error("A soma das taxas e margem ultrapassa 100%. Impossível calcular preço sugerido.")
    else:
        preco_sugerido = (cmv + frete_anuncio + custo_fixo_transacao + custo_extra) / divisor

    # --- EXIBIÇÃO DOS CARDS ---
    
    c1, c2, c3 = st.columns(3)
    
    c1.metric("Lucro Líquido (R$)", f"R$ {lucro_liquido:.2f}", delta_color="normal")
    
    # Cor da margem (Verde se acima da meta, Vermelho se abaixo)
    cor_margem = "normal"
    if margem_real < margem_alvo:
        c2.metric("Margem Atual", f"{margem_real:.1f}%", f"{margem_real - margem_alvo:.1f}% (Abaixo)", delta_color="inverse")
    else:
        c2.metric("Margem Atual", f"{margem_real:.1f}%", f"Meta: {margem_alvo}%", delta_color="normal")

    c3.metric("Preço Sugerido", f"R$ {preco_sugerido:.2f}", help=f"Para atingir {margem_alvo}% de margem")

    st.markdown("---")
    
    # Detalhamento Visual (DRE Simples)
    st.write("#### ✂️ Para onde vai o dinheiro?")
    
    dados_dre = {
        "Descrição": ["Preço de Venda", "(-) Impostos", "(-) Comissão ML", "(-) Frete", "(-) Custo Produto", "(=) Lucro Líquido"],
        "Valor (R$)": [
            preco_venda_analise, 
            -valor_imposto, 
            -valor_comissao, 
            -frete_anuncio, 
            -cmv, 
            lucro_liquido
        ]
    }
    df_dre = pd.DataFrame(dados_dre)
    
    # Mostra tabela colorida
    st.dataframe(
        df_dre.style.format({"Valor (R$)": "R$ {:.2f}"}).applymap(
            lambda x: 'color: red' if isinstance(x, (int, float)) and x < 0 else 'color: green', 
            subset=['Valor (R$)']
        ),
        use_container_width=True,
        hide_index=True
    )

# Seção de Aviso de Frete
if preco_venda_analise < frete_limite and frete_anuncio > 0:
    st.warning(f"⚠️ Atenção: Seu preço está abaixo de R$ {frete_limite}. Verifique se o frete é pago pelo comprador ou se há taxa fixa adicional do ML.")
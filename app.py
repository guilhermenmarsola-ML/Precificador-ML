import streamlit as st
import pandas as pd

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Gerenciador ML - V4 (Simulador Inteligente)", layout="wide")

if 'lista_produtos' not in st.session_state:
    st.session_state.lista_produtos = []

# --- CSS (ESTILO) ---
st.markdown("""
<style>
    .metric-card { background-color: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #dee2e6; }
    .status-ok { color: #28a745; font-weight: bold; }
    .status-warn { color: #ffc107; font-weight: bold; }
    .status-bad { color: #dc3545; font-weight: bold; }
    .frete-info { font-size: 0.9em; color: #6c757d; }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR: REGRAS DE NEGÓCIO ---
st.sidebar.header("⚙️ Regras e Taxas")
imposto_padrao = st.sidebar.number_input("Impostos (%)", value=27.0, step=0.5, format="%.2f")

st.sidebar.markdown("### 🚚 Tabela de Frete ML (< R$ 79)")
taxa_12_29 = st.sidebar.number_input("R$ 12,50 a 29,00", value=6.25)
taxa_29_50 = st.sidebar.number_input("R$ 29,00 a 50,00", value=6.50)
taxa_50_79 = st.sidebar.number_input("R$ 50,00 a 79,00", value=6.75)
taxa_minima = st.sidebar.number_input("Abaixo de R$ 12,50", value=3.25)

st.sidebar.markdown("---")
st.sidebar.info("O App selecionará o frete automaticamente baseado no preço que você escolher.")

# --- FUNÇÃO INTELIGENTE DE FRETE ---
def calcular_frete_real(preco_alvo, frete_manual_input):
    """Retorna (Custo do Frete, Nome da Regra) baseado no preço escolhido"""
    if preco_alvo >= 79.00:
        return frete_manual_input, "Frete Manual (>79)"
    elif 50.00 <= preco_alvo < 79.00:
        return taxa_50_79, "Tabela (50-79)"
    elif 29.00 <= preco_alvo < 50.00:
        return taxa_29_50, "Tabela (29-50)"
    elif 12.50 <= preco_alvo < 29.00:
        return taxa_12_29, "Tabela (12-29)"
    else:
        return taxa_minima, "Tabela Mínima (<12)"

# --- TÍTULO ---
st.title("🛒 Precificação Inteligente ML")

# --- 1. DADOS DO PRODUTO ---
with st.container():
    c1, c2, c3, c4 = st.columns([1, 2, 1, 1])
    with c1: codigo_mlb = st.text_input("Código MLB", "MLB-")
    with c2: nome_produto = st.text_input("Produto", "Ex: Tela Sombreamento 80%")
    with c3: cmv = st.number_input("Custo (CMV) R$", value=36.59, step=0.01, format="%.2f")
    with c4: frete_anuncio = st.number_input("Frete no Anúncio (>79)", value=18.86, step=0.01, format="%.2f", help="Valor cobrado se o preço for maior que 79")

    col_taxas, col_meta = st.columns(2)
    with col_taxas:
        cc1, cc2 = st.columns(2)
        taxa_ml = cc1.number_input("Comissão ML (%)", value=16.5, step=0.5, format="%.1f")
        custo_extra = cc2.number_input("Embalagem (R$)", value=2.00, step=0.01, format="%.2f")
        
    with col_meta:
        # Focado na estratégia de Lucro Fixo ERP
        c_erp1, c_erp2 = st.columns(2)
        preco_erp = c_erp1.number_input("Preço ERP (R$)", value=85.44, step=0.01, format="%.2f")
        margem_erp = c_erp2.number_input("Margem ERP (%)", value=20.0, step=1.0, format="%.1f")
        lucro_alvo = preco_erp * (margem_erp / 100)
        st.caption(f"🎯 Lucro Alvo: **R$ {lucro_alvo:.2f}**")

# --- 2. MOTOR DE SUGESTÃO (Cálculo Reverso) ---
# Tenta calcular considerando o frete cheio
custos_base_cheio = cmv + custo_extra + frete_anuncio
divisor = 1 - ((taxa_ml + imposto_padrao) / 100)
preco_sugerido_inicial = (custos_base_cheio + lucro_alvo) / divisor

# Verifica se o preço sugerido caiu abaixo de 79. Se sim, recalcula com frete barato.
frete_sug, nome_frete_sug = calcular_frete_real(preco_sugerido_inicial, frete_anuncio)

if frete_sug != frete_anuncio:
    # Recalcula com o frete mais barato
    custos_base_reduzido = cmv + custo_extra + frete_sug
    preco_sugerido_final = (custos_base_reduzido + lucro_alvo) / divisor
else:
    preco_sugerido_final = preco_sugerido_inicial

# --- 3. SIMULADOR DE DECISÃO (Onde você edita) ---
st.markdown("---")
st.subheader("⚖️ Simulador e Decisão")

col_sim1, col_sim2 = st.columns([1, 2])

with col_sim1:
    st.info(f"O sistema sugere: **R$ {preco_sugerido_final:.2f}**")
    
    # CAMPO DE DECISÃO
    preco_praticado = st.number_input(
        "Preço Que Vou Praticar (R$)", 
        value=float(round(preco_sugerido_final, 2)), 
        step=0.01, 
        format="%.2f",
        help="Altere este valor para ver como o frete e a margem mudam."
    )

with col_sim2:
    # --- CÁLCULO FINAL BASEADO NA DECISÃO DO USUÁRIO ---
    
    # 1. Identifica qual frete vale para o preço que O USUÁRIO digitou
    frete_real_usado, nome_regra_frete = calcular_frete_real(preco_praticado, frete_anuncio)
    
    # 2. Calcula DRE
    imposto_reais = preco_praticado * (imposto_padrao / 100)
    comissao_reais = preco_praticado * (taxa_ml / 100)
    custos_totais = cmv + custo_extra + frete_real_usado + imposto_reais + comissao_reais
    
    lucro_final = preco_praticado - custos_totais
    margem_final = (lucro_final / preco_praticado * 100) if preco_praticado > 0 else 0
    diferenca_meta = lucro_final - lucro_alvo
    
    # Exibe Cards
    k1, k2, k3 = st.columns(3)
    
    k1.metric("Frete Aplicado", f"R$ {frete_real_usado:.2f}", nome_regra_frete)
    
    cor_lucro = "normal"
    if diferenca_meta < -0.50: cor_lucro = "inverse" # Vermelho se perder mais que 50 centavos da meta
    elif diferenca_meta > 0.50: cor_lucro = "normal" # Verde se ganhar a mais
    
    k2.metric("Lucro Líquido", f"R$ {lucro_final:.2f}", f"Meta: R$ {lucro_alvo:.2f}", delta_color=cor_lucro)
    k3.metric("Margem Final", f"{margem_final:.1f}%", f"Dif: R$ {diferenca_meta:.2f}")

    # DRE Visual Compacta
    st.markdown(f"""
    <div style='background-color: #eee; padding: 10px; border-radius: 5px; font-size: 0.9em;'>
        <b>Detalhamento:</b> 
        Venda ({preco_praticado:.2f}) - Imposto ({imposto_reais:.2f}) - ML ({comissao_reais:.2f}) 
        - <span style='color:blue'><b>Frete ({frete_real_usado:.2f})</b></span> - Custo ({cmv:.2f}) - Extra ({custo_extra:.2f}) 
        = <b>Lucro R$ {lucro_final:.2f}</b>
    </div>
    """, unsafe_allow_html=True)

# --- 4. LISTA ---
st.markdown("---")
btn_col, _ = st.columns([1, 3])
if btn_col.button("➕ Adicionar à Lista"):
    novo_item = {
        "MLB": codigo_mlb,
        "Produto": nome_produto,
        "Preço ERP": preco_erp,
        "Preço Final": preco_praticado,
        "Frete Pago": frete_real_usado,
        "Tipo Frete": nome_regra_frete,
        "Lucro Real": round(lucro_final, 2),
        "Meta Lucro": round(lucro_alvo, 2),
        "Diferença": round(diferenca_meta, 2),
        "Margem %": round(margem_final, 1)
    }
    st.session_state.lista_produtos.append(novo_item)
    st.success("Adicionado!")

if st.session_state.lista_produtos:
    st.write("### 📋 Seus Produtos")
    df = pd.DataFrame(st.session_state.lista_produtos)
    st.dataframe(df, use_container_width=True)
    
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Baixar CSV", csv, "precificacao_final.csv", "text/csv")
    if st.button("Limpar"):
        st.session_state.lista_produtos = []
        st.experimental_rerun()
        st.experimental_rerun()


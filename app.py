import streamlit as st
import pandas as pd
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Precificador Pro | Mercado Livre", layout="wide", page_icon="⚡")

# Função de Reinício Universal
def reiniciar_app():
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()

if 'lista_produtos' not in st.session_state:
    st.session_state.lista_produtos = []

# --- DESIGN SYSTEM (CSS PROFISSIONAL) ---
st.markdown("""
<style>
    /* Fundo e Fontes */
    .main { background-color: #f8f9fa; }
    h1, h2, h3 { font-family: 'Segoe UI', sans-serif; color: #2c3e50; }
    
    /* Cards Principais */
    .custom-card {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e9ecef;
        margin-bottom: 20px;
    }
    
    /* Destaques de Texto */
    .highlight-blue { color: #00a6ed; font-weight: bold; }
    .highlight-green { color: #28a745; font-weight: bold; }
    
    /* Métricas */
    div[data-testid="stMetricValue"] { font-size: 24px; color: #333; }
    
    /* Separadores */
    hr { margin: 10px 0; border-top: 1px solid #eee; }
    
    /* Botão Principal */
    div.stButton > button:first-child {
        background-color: #ffe600;
        color: #2d3236;
        font-weight: bold;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-size: 16px;
        width: 100%;
    }
    div.stButton > button:hover {
        background-color: #fdd835;
        color: black;
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR: CONFIGURAÇÕES ---
with st.sidebar:
    st.header("⚙️ Configurações")
    with st.expander("📊 Taxas Globais", expanded=True):
        imposto_padrao = st.number_input("Impostos (%)", value=27.0, step=0.5, format="%.2f")
    
    with st.expander("🚚 Tabela Frete ML (<79)", expanded=True):
        taxa_12_29 = st.number_input("R$ 12,50 - 29,00", value=6.25)
        taxa_29_50 = st.number_input("R$ 29,00 - 50,00", value=6.50)
        taxa_50_79 = st.number_input("R$ 50,00 - 79,00", value=6.75)
        taxa_minima = st.number_input("Abaixo de R$ 12,50", value=3.25)

# --- FUNÇÕES DE LÓGICA ---
def identificar_faixa_frete(preco):
    if preco >= 79.00: return "manual", 0.0 # Valor placeholder, usa o input manual
    elif 50.00 <= preco < 79.00: return "Tab. 50-79", taxa_50_79
    elif 29.00 <= preco < 50.00: return "Tab. 29-50", taxa_29_50
    elif 12.50 <= preco < 29.00: return "Tab. 12-29", taxa_12_29
    else: return "Tab. Mínima", taxa_minima

def calcular_preco_sugerido_reverso(custo_base, lucro_alvo_reais, taxa_ml_pct, imposto_pct, frete_manual):
    # 1. Tenta calcular assumindo que vai dar acima de 79 (Frete Manual)
    custos_fixos_1 = custo_base + frete_manual
    divisor = 1 - ((taxa_ml_pct + imposto_pct) / 100)
    
    if divisor <= 0: return 0.0, "Erro Taxas"
    
    preco_est_1 = (custos_fixos_1 + lucro_alvo_reais) / divisor
    
    # Se o preço estimado for >= 79, a premissa estava certa
    if preco_est_1 >= 79.00:
        return preco_est_1, "Frete Manual (>79)"
    
    # 2. Se deu menos de 79, precisamos recalcular usando a tabela
    # Como a tabela depende do preço, fazemos uma verificação em cascata
    
    # Tenta faixa 50-79
    custos_fixos_2 = custo_base + taxa_50_79
    preco_est_2 = (custos_fixos_2 + lucro_alvo_reais) / divisor
    if 50.00 <= preco_est_2 < 79.00:
        return preco_est_2, "Tab. 50-79"
        
    # Tenta faixa 29-50
    custos_fixos_3 = custo_base + taxa_29_50
    preco_est_3 = (custos_fixos_3 + lucro_alvo_reais) / divisor
    if 29.00 <= preco_est_3 < 50.00:
        return preco_est_3, "Tab. 29-50"
        
    # Tenta faixa 12-29
    custos_fixos_4 = custo_base + taxa_12_29
    preco_est_4 = (custos_fixos_4 + lucro_alvo_reais) / divisor
    if 12.50 <= preco_est_4 < 29.00:
        return preco_est_4, "Tab. 12-29"
        
    # Se nada bateu, retorna o cálculo base (fallback)
    return preco_est_1, "Frete Manual (Fallback)"

# --- CABEÇALHO ---
st.title("⚡ Precificador Mercado Livre Pro")
st.markdown("---")

# --- BLOCO 1: DADOS E CUSTOS (Card Branco) ---
st.markdown('<div class="custom-card">', unsafe_allow_html=True)
st.subheader("1. Dados do Produto e Custos")
c1, c2, c3, c4 = st.columns([1, 2, 1, 1])
with c1: codigo_mlb = st.text_input("SKU / MLB", "MLB-")
with c2: nome_produto = st.text_input("Nome do Produto", "")
with c3: cmv = st.number_input("Custo (CMV)", value=32.57, step=0.01, format="%.2f")
with c4: frete_anuncio = st.number_input("Frete Cheio (>79)", value=17.23, step=0.01, format="%.2f", help="Valor cobrado se o preço for maior que 79")

c_taxa, c_extra = st.columns(2)
with c_taxa: taxa_ml = st.number_input("Comissão ML (%)", value=16.5, step=0.5, format="%.1f")
with c_extra: custo_extra = st.number_input("Embalagem / Extra (R$)", value=0.00, step=0.01, format="%.2f")
st.markdown('</div>', unsafe_allow_html=True)

# --- BLOCO 2: ESTRATÉGIA E SUGESTÃO (Card Branco) ---
st.markdown('<div class="custom-card">', unsafe_allow_html=True)
st.subheader("2. Definição de Meta (ERP)")

col_meta, col_sugestao = st.columns([1, 1])

with col_meta:
    # Cálculo do Alvo
    mc1, mc2 = st.columns(2)
    preco_erp = mc1.number_input("Preço ERP (R$)", value=85.44, step=0.01, format="%.2f")
    margem_erp = mc2.number_input("Margem ERP (%)", value=20.0, step=1.0, format="%.1f")
    lucro_alvo = preco_erp * (margem_erp / 100)
    st.markdown(f"🎯 Meta de Lucro: :green[**R$ {lucro_alvo:.2f}**]")

with col_sugestao:
    # --- CÉREBRO DA SUGESTÃO ---
    preco_ideal, nome_frete_ideal = calcular_preco_sugerido_reverso(
        custo_base=(cmv + custo_extra),
        lucro_alvo_reais=lucro_alvo,
        taxa_ml_pct=taxa_ml,
        imposto_pct=imposto_padrao,
        frete_manual=frete_anuncio
    )
    
    st.info(f"💡 **Preço Sugerido para a Meta:**\n# **R$ {preco_ideal:.2f}**\n*(Considerando {nome_frete_ideal})*")

st.markdown('</div>', unsafe_allow_html=True)

# --- BLOCO 3: AJUSTE FINO E PROMOÇÃO (Card Azulado) ---
st.markdown('<div class="custom-card" style="background-color: #f0f8ff; border: 1px solid #b3d7ff;">', unsafe_allow_html=True)
st.subheader("3. Decisão Final e Promoções")

col_decisao, col_promo = st.columns([1, 1.5])

with col_decisao:
    preco_base_decisao = st.number_input(
        "Preço de Tabela (DE:)", 
        value=float(round(preco_ideal, 2)), 
        step=0.01, 
        format="%.2f",
        help="Edite este valor para o preço que você vai cadastrar"
    )

with col_promo:
    pc1, pc2 = st.columns(2)
    desconto_pct = pc1.number_input("Desconto (%)", value=0.0, step=0.5, format="%.1f")
    bonus_ml = pc2.number_input("Rebate / Bônus (R$)", value=0.00, step=0.01, format="%.2f")
    
    preco_final = preco_base_decisao * (1 - (desconto_pct / 100))
    st.markdown(f"🛒 Preço Final de Venda (POR): **R$ {preco_final:.2f}**")

st.markdown('</div>', unsafe_allow_html=True)

# --- BLOCO 4: RESULTADO (CÁLCULO FINAL) ---
# Lógica Final
nome_frete_real, valor_frete_real = identificar_faixa_frete(preco_final)
if nome_frete_real == "manual":
    valor_frete_real = frete_anuncio

imposto_val = preco_final * (imposto_padrao / 100)
comissao_val = preco_final * (taxa_ml / 100)
custos_totais = cmv + custo_extra + valor_frete_real + imposto_val + comissao_val
lucro_final = preco_final - custos_totais + bonus_ml
margem_final = (lucro_final / preco_final * 100) if preco_final > 0 else 0

st.subheader("📊 Resultado da Simulação")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Frete Aplicado", f"R$ {valor_frete_real:.2f}", nome_frete_real)
k2.metric("Comissão + Imposto", f"R$ {(comissao_val + imposto_val):.2f}")
k3.metric("Bônus (Entrada)", f"R$ {bonus_ml:.2f}")

diff_meta = lucro_final - lucro_alvo
cor_delta = "normal" if diff_meta >= -0.10 else "inverse"
k4.metric("Lucro Líquido", f"R$ {lucro_final:.2f}", f"Dif: R$ {diff_meta:.2f}", delta_color=cor_delta)

# --- BOTÃO ADICIONAR ---
st.markdown("---")
col_add, _ = st.columns([1, 2])
if col_add.button("➕ ADICIONAR PRODUTO À LISTA"):
    if nome_produto:
        novo_id = int(time.time() * 1000)
        novo_item = {
            "id": novo_id,
            "MLB": codigo_mlb,
            "Produto": nome_produto,
            "PrecoBase": preco_base_decisao,
            "DescontoPct": desconto_pct,
            "PrecoFinal": preco_final,
            "ImpostoVal": imposto_val,
            "ImpostoPct": imposto_padrao,
            "ComissaoVal": comissao_val,
            "ComissaoPct": taxa_ml,
            "FreteVal": valor_frete_real,
            "FreteNome": nome_frete_real,
            "CMV": cmv,
            "Extra": custo_extra,
            "Bonus": bonus_ml,
            "Lucro": lucro_final,
            "Margem": margem_final
        }
        st.session_state.lista_produtos.append(novo_item)
        st.success("Produto Salvo!")
    else:
        st.error("Digite o nome do produto.")

# --- LISTA DE PRODUTOS ---
if st.session_state.lista_produtos:
    st.markdown("### 📋 Itens Precificados")
    
    # Cabeçalho Fixo
    with st.container():
        h1, h2, h3, h4 = st.columns([1, 3, 2, 2])
        h1.caption("CÓDIGO")
        h2.caption("PRODUTO")
        h3.caption("PREÇO FINAL")
        h4.caption("LUCRO / MARGEM")
        st.divider()

    for item in reversed(st.session_state.lista_produtos):
        # Linha do Produto
        c1, c2, c3, c4 = st.columns([1, 3, 2, 2])
        c1.write(f"**{item['MLB']}**")
        c2.write(item['Produto'])
        c3.write(f"R$ {item['PrecoFinal']:.2f}")
        
        if item['Lucro'] > 0:
            c4.markdown(f":green[**R$ {item['Lucro']:.2f}**] ({item['Margem']:.1f}%)")
        else:
            c4.markdown(f":red[**R$ {item['Lucro']:.2f}**] ({item['Margem']:.1f}%)")

        # Expander Nativo para DRE
        with st.expander("📄 Ver Detalhes (DRE)"):
            # Linhas da DRE usando colunas nativas para alinhamento perfeito
            
            # Receita
            d1, d2 = st.columns([3, 1])
            d1.markdown("Preço Tabela")
            d2.markdown(f"R$ {item['PrecoBase']:.2f}")
            
            if item['DescontoPct'] > 0:
                d1, d2 = st.columns([3, 1])
                d1.markdown(f":red[(-) Desconto ({item['DescontoPct']}%) ]")
                d2.markdown(f":red[- R$ {item['PrecoBase'] - item['PrecoFinal']:.2f}]")
            
            st.markdown("---")
            d1, d2 = st.columns([3, 1])
            d1.markdown("**(=) RECEITA BRUTA**")
            d2.markdown(f"**R$ {item['PrecoFinal']:.2f}**")
            st.markdown("---")
            
            # Custos
            custos_list = [
                (f"Impostos ({item['ImpostoPct']}%)", item['ImpostoVal']),
                (f"Comissão ML ({item['ComissaoPct']}%)", item['ComissaoVal']),
                (f"Frete ({item['FreteNome']})", item['FreteVal']),
                ("Custo (CMV)", item['CMV']),
                ("Extras", item['Extra'])
            ]
            
            for nome, valor in custos_list:
                d1, d2 = st.columns([3, 1])
                d1.write(f"(-) {nome}")
                d2.markdown(f":red[- R$ {valor:.2f}]")

            # Bônus
            if item['Bonus'] > 0:
                st.write("")
                d1, d2 = st.columns([3, 1])
                d1.markdown(f":blue[(+) Bônus / Rebate]")
                d2.markdown(f":blue[+ R$ {item['Bonus']:.2f}]")

            # Final
            st.divider()
            d1, d2 = st.columns([3, 1])
            d1.markdown("#### RESULTADO FINAL")
            cor_final = ":green" if item['Lucro'] > 0 else ":red"
            d2.markdown(f"#### {cor_final}[R$ {item['Lucro']:.2f}]")
            
        st.divider()

    # Exportação
    col_dw, col_clr = st.columns([1, 1])
    df_exp = pd.DataFrame(st.session_state.lista_produtos)
    csv = df_exp.to_csv(index=False).encode('utf-8')
    col_dw.download_button("📥 Baixar Planilha Excel", csv, "precificacao.csv", "text/csv")
    
    if col_clr.button("🗑️ Limpar Lista"):
        st.session_state.lista_produtos = []
        reiniciar_app()

else:
    st.info("Sua lista está vazia. Adicione o primeiro produto acima.")

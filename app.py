import streamlit as st
import pandas as pd
import time

# --- CONFIGURAÇÃO INICIAL ---
st.set_page_config(page_title="Gerenciador ML - V9 Nativa", layout="wide")

# Função Universal de Reinício
def reiniciar_app():
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()

if 'lista_produtos' not in st.session_state:
    st.session_state.lista_produtos = []

# --- CSS (Apenas para ajustes finos globais) ---
st.markdown("""
<style>
    .stExpander { border: 1px solid #ddd; border-radius: 8px; }
    .stMetric { background-color: #f8f9fa; padding: 10px; border-radius: 5px; }
    /* Estilo do Card de Promoção */
    .promo-container {
        padding: 15px;
        background-color: #e8f4f8;
        border-radius: 8px;
        border-left: 5px solid #00a6ed;
        margin-bottom: 20px;
    }
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

# --- FUNÇÃO AUXILIAR VISUAL ---
def linha_dre_nativa(texto, valor, cor="padrao", negrito=False):
    c1, c2 = st.columns([3, 1])
    
    # Formatação do Label
    label = f"**{texto}**" if negrito else texto
    c1.markdown(label)
    
    # Formatação do Valor
    val_fmt = f"R$ {abs(valor):.2f}"
    if cor == "vermelho":
        c2.markdown(f":red[- {val_fmt}]")
    elif cor == "verde":
        c2.markdown(f":green[+ {val_fmt}]")
    elif cor == "azul":
        c2.markdown(f":blue[{val_fmt}]")
    else:
        c2.markdown(f"{val_fmt}")

st.title("🛒 Precificador ML (Versão Nativa)")

# --- 1. DADOS DE ENTRADA ---
with st.container():
    c1, c2, c3, c4 = st.columns([1, 2, 1, 1])
    with c1: codigo_mlb = st.text_input("Código MLB", "MLB-")
    with c2: nome_produto = st.text_input("Produto", "Ex: Lona 4x10")
    with c3: cmv = st.number_input("Custo (CMV)", value=32.57, step=0.01, format="%.2f")
    with c4: frete_anuncio = st.number_input("Frete Cheio (>79)", value=17.23, step=0.01, format="%.2f")

    col_taxas, col_meta = st.columns(2)
    with col_taxas:
        cc1, cc2 = st.columns(2)
        taxa_ml = cc1.number_input("Comissão ML (%)", value=16.5, step=0.5, format="%.1f")
        custo_extra = cc2.number_input("Embalagem (R$)", value=0.00, step=0.01, format="%.2f")
        
    with col_meta:
        c_erp1, c_erp2 = st.columns(2)
        preco_erp = c_erp1.number_input("Preço ERP (R$)", value=0.00, step=0.01, format="%.2f")
        margem_erp = c_erp2.number_input("Margem ERP (%)", value=20.0, step=1.0, format="%.1f")
        lucro_alvo = preco_erp * (margem_erp / 100) if preco_erp > 0 else 0

st.markdown("---")

# --- 2. PREÇO E PROMO ---
col_input, col_promo = st.columns([1, 1.5])
with col_input:
    preco_base = st.number_input("Preço Base (DE:)", value=32.57, step=0.01, format="%.2f")

with col_promo:
    # Card visual nativo usando container
    with st.container():
        st.markdown("""<div class="promo-container"><b>⚡ Configurar Promoção</b></div>""", unsafe_allow_html=True)
        cp1, cp2, cp3 = st.columns([1, 1, 1])
        desconto_pct = cp1.number_input("% Desconto", value=13.0, step=0.5, format="%.1f")
        bonus_ml = cp2.number_input("Bônus ML (R$)", value=0.52, step=0.01, format="%.2f")
        
        preco_final_venda = preco_base * (1 - (desconto_pct / 100))
        cp3.metric("Preço Final (POR)", f"R$ {preco_final_venda:.2f}")

# --- 3. CÁLCULO ---
frete_aplicado, nome_frete = calcular_frete_real(preco_final_venda, frete_anuncio)
imposto_reais = preco_final_venda * (imposto_padrao / 100)
comissao_reais = preco_final_venda * (taxa_ml / 100)
custos_totais = cmv + custo_extra + frete_aplicado + imposto_reais + comissao_reais
lucro_liquido = preco_final_venda - custos_totais + bonus_ml
margem_final = (lucro_liquido / preco_final_venda * 100) if preco_final_venda > 0 else 0

# --- 4. BOTÃO ADICIONAR ---
st.markdown("### 👁️ Prévia do Item")
k1, k2, k3 = st.columns(3)
k1.metric("Frete Aplicado", f"R$ {frete_aplicado:.2f}", nome_frete)
k2.metric("Lucro Líquido", f"R$ {lucro_liquido:.2f}", f"{margem_final:.1f}%")

if k3.button("➕ ADICIONAR À LISTA", type="primary", use_container_width=True):
    if nome_produto:
        novo_id = int(time.time() * 1000)
        novo_item = {
            "id": novo_id,
            "MLB": codigo_mlb,
            "Produto": nome_produto,
            "PrecoBase": preco_base,
            "DescontoPct": desconto_pct,
            "PrecoFinal": preco_final_venda,
            "ImpostoVal": imposto_reais,
            "ImpostoPct": imposto_padrao,
            "ComissaoVal": comissao_reais,
            "ComissaoPct": taxa_ml,
            "FreteVal": frete_aplicado,
            "FreteNome": nome_frete,
            "CMV": cmv,
            "Extra": custo_extra,
            "Bonus": bonus_ml,
            "Lucro": lucro_liquido,
            "Margem": margem_final
        }
        st.session_state.lista_produtos.append(novo_item)
        st.success(f"{nome_produto} Adicionado!")
    else:
        st.error("Nome obrigatório")

# --- 5. LISTA DE PRODUTOS ---
st.markdown("---")
st.subheader(f"📋 Produtos na Lista ({len(st.session_state.lista_produtos)})")

if len(st.session_state.lista_produtos) > 0:
    
    # Cabeçalho
    cols = st.columns([1, 3, 2, 2])
    cols[0].markdown("**MLB**")
    cols[1].markdown("**Produto**")
    cols[2].markdown("**Preço Final**")
    cols[3].markdown("**Lucro**")
    st.divider()

    for item in reversed(st.session_state.lista_produtos):
        
        c1, c2, c3, c4 = st.columns([1, 3, 2, 2])
        c1.write(f"#{item['MLB']}")
        c2.write(f"**{item['Produto']}**")
        c3.write(f"R$ {item['PrecoFinal']:.2f}")
        
        if item['Lucro'] > 0:
            c4.markdown(f":green[**R$ {item['Lucro']:.2f}**] ({item['Margem']:.1f}%)")
        else:
            c4.markdown(f":red[**R$ {item['Lucro']:.2f}**] ({item['Margem']:.1f}%)")
        
        # --- DRE NATIVA (SEM HTML/CSS COMPLEXO) ---
        with st.expander(f"📊 Ver DRE Detalhada - {item['MLB']}"):
            
            # Aqui usamos colunas nativas, impossível dar erro de código HTML
            linha_dre_nativa("Preço Tabela", item['PrecoBase'])
            linha_dre_nativa(f"Desconto ({item['DescontoPct']}%)", -1*(item['PrecoBase']-item['PrecoFinal']), "vermelho")
            st.divider()
            
            linha_dre_nativa("(=) RECEITA BRUTA", item['PrecoFinal'], "azul", True)
            st.write("") # Espaço
            
            linha_dre_nativa(f"(-) Impostos ({item['ImpostoPct']}%)", -item['ImpostoVal'], "vermelho")
            linha_dre_nativa(f"(-) Comissão ML ({item['ComissaoPct']}%)", -item['ComissaoVal'], "vermelho")
            linha_dre_nativa(f"(-) Frete ({item['FreteNome']})", -item['FreteVal'], "vermelho")
            linha_dre_nativa("(-) Custo (CMV)", -item['CMV'], "vermelho")
            linha_dre_nativa("(-) Extras", -item['Extra'], "vermelho")
            st.write("")
            
            linha_dre_nativa("(+) Bônus / Rebate", item['Bonus'], "verde")
            st.divider()
            
            # Linha final de resultado
            cf, cr = st.columns([3, 1])
            cf.markdown("### RESULTADO FINAL")
            if item['Lucro'] > 0:
                cr.metric("Lucro", f"R$ {item['Lucro']:.2f}", f"{item['Margem']:.1f}%")
            else:
                cr.metric("Prejuízo", f"R$ {item['Lucro']:.2f}", f"{item['Margem']:.1f}%", delta_color="inverse")
            
        st.divider()

    cb1, cb2 = st.columns([1, 1])
    df_export = pd.DataFrame(st.session_state.lista_produtos)
    csv = df_export.to_csv(index=False).encode('utf-8')
    cb1.download_button("📥 Baixar Excel", csv, "lista_ml.csv", "text/csv")
    
    if cb2.button("🗑️ Limpar Lista"):
        st.session_state.lista_produtos = []
        reiniciar_app()

else:
    st.info("Lista vazia.")


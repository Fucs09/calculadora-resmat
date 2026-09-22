import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# 1. Configuração da Página
st.set_page_config(page_title="Calculadora ResMat Naval", layout="wide", initial_sidebar_state="expanded")
st.title(" Calculadora Estrutural - Resistência dos Materiais I")
st.markdown("Análise Estática e Diagramas de Esforços Internos Contínuos - FCEE / UERJ")

# 2. Layout Principal
col_input, col_plot = st.columns([1.2, 2])

with col_input:
    st.subheader("1. Configuração da Viga e Apoios")
    vao = st.number_input("Comprimento Total da Viga L (m)", min_value=1.0, value=26.0, step=1.0)
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Apoio A (2ª Classe - Pino)**")
        pos_a = st.number_input("Posição X do Apoio A", value=0.0, step=1.0)
    with col_b:
        st.markdown("**Apoio B (1ª Classe - Rolete)**")
        pos_b = st.number_input("Posição X do Apoio B", value=float(vao), step=1.0)

    st.subheader("2. Matriz de Cargas Aplicadas")
    st.markdown("Preencha a tabela. (+) Cima / (-) Baixo. Para Momentos, digite o valor e escolha o sentido.")
    
    dados_iniciais = pd.DataFrame({
        "Tipo": ["Pontual", "Distribuída", "Inclinada", "Momento"],
        "Força (kN/kNm)": [6.0, -2.0, -4.0, 3.0], # Valores de exemplo ajustados
        "Posição X (m)": [10.0, 12.0, 5.0, 2.0],
        "Parâmetro (m ou °)": [0.0, 4.0, 60.0, 0.0],
        "Opções (Dir/Sentido)": ["N/A", "N/A", "Esquerda", "Horário"]
    })

    df_cargas = st.data_editor(
        dados_iniciais,
        num_rows="dynamic",
        column_config={
            "Tipo": st.column_config.SelectboxColumn("Tipo de Carga", options=["Pontual", "Distribuída", "Inclinada", "Momento"], required=True),
            "Força (kN/kNm)": st.column_config.NumberColumn("Intensidade (+ Cima / - Baixo)", format="%.2f"),
            "Posição X (m)": st.column_config.NumberColumn("Pos. X (m)", min_value=0.0),
            "Parâmetro (m ou °)": st.column_config.NumberColumn("Extensão(m) / Ângulo(°)", format="%.2f"),
            "Opções (Dir/Sentido)": st.column_config.SelectboxColumn("Direção / Sentido", options=["N/A", "Direita", "Esquerda", "Horário", "Anti-horário"], default="N/A")
        },
        use_container_width=True,
        hide_index=True
    )

# 2.5 PRÉ-PROCESSAMENTO DAS CARGAS (Garante a Regra de Sinais Padrão)
cargas = []
for index, row in df_cargas.iterrows():
    tipo = row.get("Tipo", "")
    try:
        forca_raw = float(row.get("Força (kN/kNm)", 0))
    except (ValueError, TypeError): continue
    
    if forca_raw == 0 and tipo != "Momento": continue
    
    pos = float(row.get("Posição X (m)", 0))
    param = float(row.get("Parâmetro (m ou °)", 0))
    opcoes = row.get("Opções (Dir/Sentido)", "N/A")

    # Tratamento especial para o sinal do Momento Fletor baseado na seleção do usuário
    if tipo == "Momento":
        if opcoes == "Horário":
            forca = -abs(forca_raw)
        elif opcoes == "Anti-horário":
            forca = abs(forca_raw)
        else:
            forca = forca_raw
    else:
        forca = forca_raw # Para as demais, respeita rigorosamente o + ou - digitado

    cargas.append({"tipo": tipo, "forca": forca, "pos": pos, "param": param, "opcoes": opcoes})

# 3. MOTOR MATEMÁTICO ALGÉBRICO (Reações)
soma_fy, soma_fx, soma_ma_cargas = 0.0, 0.0, 0.0
str_fx, str_fy, str_ma = "", "", ""

for c in cargas:
    if c["tipo"] == "Pontual":
        soma_fy += c["forca"]
        momento = c["forca"] * (c["pos"] - pos_a)
        soma_ma_cargas += momento
        str_fy += f" {'+' if c['forca'] > 0 else '-'} {abs(c['forca']):.2f}"
        str_ma += f" {'+' if momento > 0 else '-'} {abs(c['forca']):.2f} \\cdot ({c['pos'] - pos_a:.2f})"
        
    elif c["tipo"] == "Distribuída":
        forca_resultante = c["forca"] * c["param"]
        cg_distribuida = c["pos"] + (c["param"] / 2.0)
        soma_fy += forca_resultante
        momento = forca_resultante * (cg_distribuida - pos_a)
        soma_ma_cargas += momento
        str_fy += f" {'+' if forca_resultante > 0 else '-'} ({abs(c['forca']):.2f} \\cdot {c['param']:.2f})"
        str_ma += f" {'+' if momento > 0 else '-'} ({abs(c['forca']):.2f} \\cdot {c['param']:.2f}) \\cdot ({cg_distribuida - pos_a:.2f})"
        
    elif c["tipo"] == "Inclinada":
        rad = np.radians(c["param"])
        fy = c["forca"] * np.sin(rad)
        fx_mag = abs(c["forca"]) * np.cos(rad)
        fx = fx_mag if c["opcoes"] == "Direita" else -fx_mag
        
        soma_fy += fy
        soma_fx += fx
        momento = fy * (c["pos"] - pos_a)
        soma_ma_cargas += momento
        str_fx += f" {'+' if fx > 0 else '-'} {abs(fx):.2f}"
        str_fy += f" {'+' if fy > 0 else '-'} {abs(fy):.2f}"
        str_ma += f" {'+' if momento > 0 else '-'} {abs(fy):.2f} \\cdot ({c['pos'] - pos_a:.2f})"
        
    elif c["tipo"] == "Momento":
        soma_ma_cargas += c["forca"]
        str_ma += f" {'+' if c['forca'] > 0 else '-'} {abs(c['forca']):.2f}"

dist_ab = pos_b - pos_a
rb = -soma_ma_cargas / dist_ab if dist_ab != 0 else 0
ray = -soma_fy - rb
rax = -soma_fx

# 3.5. DISCRETIZAÇÃO DE MACAULAY (Diagramas)
X = np.linspace(0, float(vao), 1000)
N, V, M = np.zeros_like(X), np.zeros_like(X), np.zeros_like(X)

V += np.where(X >= pos_a, ray, 0)
M += np.where(X >= pos_a, ray * (X - pos_a), 0)
N += np.where(X >= pos_a, -rax, 0) 
V += np.where(X >= pos_b, rb, 0)
M += np.where(X >= pos_b, rb * (X - pos_b), 0)

for c in cargas:
    if c["tipo"] == "Pontual":
        V += np.where(X >= c["pos"], c["forca"], 0)
        M += np.where(X >= c["pos"], c["forca"] * (X - c["pos"]), 0)
    elif c["tipo"] == "Distribuída":
        V += np.where(X >= c["pos"], c["forca"] * (X - c["pos"]), 0)
        M += np.where(X >= c["pos"], c["forca"] * ((X - c["pos"])**2) / 2, 0)
        fim_carga = c["pos"] + c["param"]
        V -= np.where(X >= fim_carga, c["forca"] * (X - fim_carga), 0)
        M -= np.where(X >= fim_carga, c["forca"] * ((X - fim_carga)**2) / 2, 0)
    elif c["tipo"] == "Inclinada":
        rad = np.radians(c["param"])
        fy = c["forca"] * np.sin(rad)
        fx_mag = abs(c["forca"]) * np.cos(rad)
        fx = fx_mag if c["opcoes"] == "Direita" else -fx_mag
        V += np.where(X >= c["pos"], fy, 0)
        M += np.where(X >= c["pos"], fy * (X - c["pos"]), 0)
        N += np.where(X >= c["pos"], -fx, 0)
    elif c["tipo"] == "Momento":
        M -= np.where(X >= c["pos"], c["forca"], 0)

# 4. MOTOR GRÁFICO 
with col_plot:
    st.subheader("Análise Gráfica Estrutural")

    fig, (ax_dcl, ax_n, ax_v, ax_m) = plt.subplots(4, 1, figsize=(10, 14), gridspec_kw={'height_ratios': [2, 1, 1, 1.5]}, sharex=True)
    fig.subplots_adjust(hspace=0.3)
    
    # --- DCL ---
    ax_dcl.plot([0, vao], [0, 0], color='#2c3e50', linewidth=6, zorder=2)
    ax_dcl.set_title("Diagrama de Corpo Livre (DCL)", fontweight='bold')
    
    def draw_support(x, type_class, label):
        tri = plt.Polygon([[x, 0], [x-vao*0.02, -1.0], [x+vao*0.02, -1.0]], color='#7f8c8d', zorder=3)
        ax_dcl.add_patch(tri)
        if type_class == 2:
            ax_dcl.plot([x-vao*0.03, x+vao*0.03], [-1.0, -1.0], color='black', linewidth=3)
            return -1.0
        elif type_class == 1:
            ax_dcl.plot(x-vao*0.01, -1.15, marker='o', color='black', markersize=5)
            ax_dcl.plot(x+vao*0.01, -1.15, marker='o', color='black', markersize=5)
            ax_dcl.plot([x-vao*0.03, x+vao*0.03], [-1.3, -1.3], color='black', linewidth=2)
            return -1.3

    base_a = draw_support(pos_a, 2, 'A')
    base_b = draw_support(pos_b, 1, 'B')

    for c in cargas:
        c_color = '#e74c3c'
        pos = c["pos"]
        forca = c["forca"]
        
        if c["tipo"] == "Pontual":
            # Força < 0 aponta para BAIXO (seta vem de cima, y=2)
            # Força > 0 aponta para CIMA (seta vem de baixo, y=-2)
            dy = 2 if forca < 0 else -2
            va_align = 'bottom' if forca < 0 else 'top'
            ax_dcl.annotate(f"{abs(forca)}", xy=(pos, 0), xytext=(pos, dy),
                        arrowprops=dict(facecolor=c_color, edgecolor=c_color, width=2, headwidth=7, shrink=0.0),
                        ha='center', va=va_align, color=c_color, fontweight='bold')
            
        elif c["tipo"] == "Distribuída":
            altura = 1.5 if forca < 0 else -1.5
            y_base = 0 if forca < 0 else -1.5
            rect = patches.Rectangle((pos, y_base), c["param"], 1.5, linewidth=1, edgecolor=c_color, facecolor=c_color, alpha=0.2)
            ax_dcl.add_patch(rect)
            for xs in np.linspace(pos, pos + c["param"], int(c["param"]) + 2):
                ax_dcl.annotate("", xy=(xs, 0), xytext=(xs, altura),
                            arrowprops=dict(facecolor=c_color, edgecolor=c_color, width=1, headwidth=5, shrink=0.0))
            ax_dcl.text(pos + c["param"]/2, altura + (0.3 if forca < 0 else -0.3), f"{abs(forca)}", ha='center', va='center', color=c_color, fontweight='bold')

        elif c["tipo"] == "Inclinada":
            rad = np.radians(c["param"])
            dy_mag = 2 * np.sin(rad)
            dx_mag = 2 * np.cos(rad)
            
            dy = dy_mag if forca < 0 else -dy_mag
            dx = -dx_mag if c["opcoes"] == "Direita" else dx_mag
            va_align = 'bottom' if forca < 0 else 'top'
            ha_align = 'right' if c["opcoes"] == "Direita" else 'left'
            
            ax_dcl.annotate(f"{abs(forca)}", xy=(pos, 0), xytext=(pos + dx, dy),
                        arrowprops=dict(facecolor=c_color, edgecolor=c_color, width=2, headwidth=7, shrink=0.0),
                        ha=ha_align, va=va_align, color=c_color, fontweight='bold')
            
        elif c["tipo"] == "Momento":
            sentido = "↺" if forca > 0 else "↻"
            ax_dcl.text(pos, 0.0, f"{sentido}", ha='center', va='center', color=c_color, fontweight='bold', fontsize=26)
            ax_dcl.text(pos, 0.8, f"{abs(forca)}", ha='center', va='bottom', color=c_color, fontweight='bold', fontsize=11)

    r_color = '#27ae60'
    if abs(ray) > 0.01:
        start_y = base_a - 2.5 if ray > 0 else base_a + 2.5
        ax_dcl.annotate(f"{abs(ray):.2f}", xy=(pos_a, base_a), xytext=(pos_a, start_y),
                    arrowprops=dict(facecolor=r_color, edgecolor=r_color, width=2, headwidth=7, shrink=0.0),
                    ha='center', va='top' if ray > 0 else 'bottom', color=r_color, fontweight='bold')
    if abs(rax) > 0.01:
        start_x = pos_a - vao*0.12 if rax > 0 else pos_a + vao*0.12
        ha_align = 'right' if rax > 0 else 'left'
        ax_dcl.annotate(f"{abs(rax):.2f}", xy=(pos_a, base_a/2), xytext=(start_x, base_a/2),
                    arrowprops=dict(facecolor=r_color, edgecolor=r_color, width=2, headwidth=7, shrink=0.0),
                    ha=ha_align, va='center', color=r_color, fontweight='bold')
    if abs(rb) > 0.01:
        start_y = base_b - 2.5 if rb > 0 else base_b + 2.5
        ax_dcl.annotate(f"{abs(rb):.2f}", xy=(pos_b, base_b), xytext=(pos_b, start_y),
                    arrowprops=dict(facecolor=r_color, edgecolor=r_color, width=2, headwidth=7, shrink=0.0),
                    ha='center', va='top' if rb > 0 else 'bottom', color=r_color, fontweight='bold')

    y_ruler = -4.5
    ax_dcl.annotate('', xy=(pos_a, y_ruler), xytext=(pos_b, y_ruler), arrowprops=dict(arrowstyle='<|-|>', color='#95a5a6', lw=1.5))
    ax_dcl.text((pos_a + pos_b)/2, y_ruler - 0.2, f"{dist_ab:.2f} m", ha='center', va='top', color='#95a5a6', fontweight='bold')
    ax_dcl.plot([pos_a, pos_a], [-1.5, y_ruler], color='#95a5a6', linestyle=':', lw=1.5)
    ax_dcl.plot([pos_b, pos_b], [-1.5, y_ruler], color='#95a5a6', linestyle=':', lw=1.5)

    ax_dcl.set_xlim(-vao*0.1, vao + vao*0.1)
    ax_dcl.set_ylim(-6.5, 4.5)
    ax_dcl.axis('off')

    # --- ESFORÇO NORMAL (N) ---
    ax_n.plot(X, N, color='#e67e22', linewidth=2)
    ax_n.fill_between(X, 0, N, where=(N >= 0), color='#e67e22', alpha=0.3)
    ax_n.fill_between(X, 0, N, where=(N < 0), color='#d35400', alpha=0.3)
    ax_n.axhline(0, color='black', linewidth=1)
    ax_n.set_ylabel("Normal (N)\n[kN]", fontweight='bold')
    ax_n.grid(True, linestyle='--', alpha=0.6)

    # --- CORTANTE (V) ---
    ax_v.plot(X, V, color='#2980b9', linewidth=2)
    ax_v.fill_between(X, 0, V, where=(V >= 0), color='#3498db', alpha=0.3)
    ax_v.fill_between(X, 0, V, where=(V < 0), color='#e74c3c', alpha=0.3)
    ax_v.axhline(0, color='black', linewidth=1)
    ax_v.set_ylabel("Cortante (V)\n[kN]", fontweight='bold')
    ax_v.grid(True, linestyle='--', alpha=0.6)

    # --- MOMENTO FLETOR (M) ---
    ax_m.plot(X, M, color='#8e44ad', linewidth=2)
    ax_m.fill_between(X, 0, M, where=(M >= 0), color='#9b59b6', alpha=0.3)
    ax_m.fill_between(X, 0, M, where=(M < 0), color='#e74c3c', alpha=0.3)
    ax_m.axhline(0, color='black', linewidth=1)
    ax_m.set_ylabel("Momento (M)\n[kNm]", fontweight='bold')
    ax_m.invert_yaxis()
    ax_m.grid(True, linestyle='--', alpha=0.6)
    ax_m.set_xlabel("Posição da Viga X (m)", fontweight='bold')
    
    for ax in [ax_n, ax_v, ax_m]:
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    st.pyplot(fig)

  # 5. MEMÓRIA DE CÁLCULO
    st.subheader(" Memória de Cálculo (Rastreabilidade)")
    
    with st.expander("Ver Equações e Explicação Passo a Passo", expanded=True):
        st.markdown("""
        **O Princípio do Equilíbrio Estático:** 
        Para que a estrutura permaneça estática, ela não pode transladar e nem rotacionar. Aplicamos as três equações fundamentais da estática de corpo rígido para descobrir as reações nos apoios:
        """)
        
        st.markdown("---")
        st.markdown("""
         **Passo 1: Impedir a Rotação (A Escolha do Eixo)**  
        Na estática, o somatório de momentos pode ser feito em qualquer ponto. Escolhemos o Apoio A por conveniência matemática: como a reação $R_{Ay}$ passa exatamente por este eixo, seu "braço de alavanca" (distância) é zero, eliminando-a da equação. Assim, formamos uma equação de 1º grau apenas com a incógnita do lado oposto ($R_B$). *(Nota: Se fizéssemos $\sum M_B = 0$, isolaríamos $R_{Ay}$ primeiro com o mesmo sucesso!)*
        """)
        st.latex(r"\textbf{1. Equilíbrio de Momentos em A } (\sum M_A = 0)")
        st.latex(f"R_B \\cdot ({dist_ab:.2f}) {str_ma} = 0")
        st.latex(f"R_B = \\frac{{{-soma_ma_cargas:.2f}}}{{{dist_ab:.2f}}} \\Rightarrow \\mathbf{{R_B = {rb:.2f} \\, kN}}")
        
        st.markdown("---")
        st.markdown("""
         **Passo 2: Impedir a Translação Vertical**  
        Conhecendo $R_B$, somamos todas as forças ativas verticais (pontuais, distribuídas e componentes verticais de inclinadas) e igualamos a zero para descobrir a reação vertical remanescente ($R_{Ay}$).
        """)
        st.latex(r"\textbf{2. Equilíbrio de Forças Verticais } (\sum F_y = 0)")
        st.latex(f"R_A + R_B {str_fy} = 0")
        st.latex(f"R_A + ({rb:.2f}) + ({soma_fy:.2f}) = 0 \\Rightarrow \\mathbf{{R_A = {ray:.2f} \\, kN}}")

        st.markdown("---")
        st.markdown("""
         **Passo 3: Impedir a Translação Horizontal**  
        O apoio de 1ª classe (rolete) é livre para transladar lateralmente, não absorvendo esforços no eixo X. Portanto, por princípio de rigidez, toda força horizontal aplicada na estrutura é integralmente resistida pelo apoio de 2ª classe (pino fixo), que neste sistema está configurado na posição A ($H_A$).
        """)
        st.latex(r"\textbf{3. Equilíbrio de Forças Horizontais } (\sum F_x = 0)")
        st.latex(f"H_A {str_fx} = 0 \\Rightarrow \\mathbf{{H_A = {rax:.2f} \\, kN}}")

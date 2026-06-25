from fpdf import FPDF
import os
import datetime
import pandas as pd


def _limpar_label(nome):
    """Remove o prefixo 'Prova' (redundante e repetido) para economizar espaço."""
    name = str(nome).strip()
    if name.upper().startswith("PROVA "):
        name = name[6:].strip()
    elif " PROVA " in f" {name.upper()} ":
        name = name.upper().replace("PROVA", "").strip()
    return name.upper()


def _quebrar_em_linhas(pdf, texto, largura_max, tamanho, max_linhas=2):
    """Quebra o texto em até `max_linhas` linhas que caibam em `largura_max` (mm)."""
    pdf.set_font('helvetica', '', tamanho)
    linhas, atual = [], ""
    for palavra in str(texto).split(" "):
        teste = (atual + " " + palavra).strip()
        if not atual or pdf.get_string_width(teste) <= largura_max:
            atual = teste
        else:
            linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas[:max_linhas]


def _ajustar_a_largura(pdf, texto, largura_max, tamanho):
    """Garante que uma única linha caiba em `largura_max`, cortando como último recurso."""
    pdf.set_font('helvetica', '', tamanho)
    if pdf.get_string_width(texto) <= largura_max:
        return texto
    while texto and pdf.get_string_width(texto + ".") > largura_max:
        texto = texto[:-1]
    return texto + "."

class BoletimPDF(FPDF):
    def __init__(self, logo_path=None, curso="", turma="", aluno_nome="", matricula=""):
        super().__init__()
        self.logo_path = logo_path
        self.curso = curso
        self.turma = turma
        self.aluno_nome = aluno_nome
        self.matricula = matricula
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        # Top Header line: ALL NET / Período / Turma
        self.set_font('helvetica', 'B', 12)
        self.set_text_color(0, 0, 0)
        
        x_offset = 15
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                self.image(self.logo_path, 15, 8, 20)
                x_offset = 40
            except:
                pass
                
        self.set_xy(x_offset, 10)
        self.cell(100, 5, "ALL NET", ln=0)
        
        self.set_font('helvetica', '', 9)
        self.set_text_color(100, 100, 100)
        self.set_xy(100, 10)
        self.cell(95, 5, "Período", align='R', ln=1)

        self.set_xy(x_offset, 15)
        self.set_font('helvetica', '', 9)
        self.cell(100, 5, "Boletim Escolar", ln=0)
        
        self.set_xy(100, 15)
        self.cell(95, 5, f"Turma: {self.turma}", align='R', ln=1)
        
        # Solid Line
        self.ln(3)
        self.set_draw_color(0, 15, 60) # Dark blue line
        self.set_line_width(0.6)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(5)
        
        # Aluno section
        self.set_font('helvetica', '', 9)
        self.set_text_color(50, 50, 50)
        self.cell(150, 5, "ALUNO(A)", ln=0)
        self.cell(30, 5, "MATRÍCULA", align='R', ln=1)
        
        self.set_font('helvetica', 'B', 14)
        self.set_text_color(0, 15, 60)
        self.cell(150, 7, str(self.aluno_nome).upper()[:50], ln=0)
        self.set_font('helvetica', '', 14)
        self.cell(30, 7, str(self.matricula), align='R', ln=1)
        
        # Dotted Line
        self.ln(2)
        y_line2 = self.get_y()
        self.set_draw_color(200, 200, 200)
        self.set_line_width(0.2)
        for x in range(15, 195, 3):
            self.line(x, y_line2, x+1.5, y_line2)
            
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def gerar_pdf(dados_aluno, total_presencas, total_faltas, freq_global, responsavel, feedback, chart_buffer, professor="Professor(a)", curso="", turma="", logo_path=None):
    pdf = BoletimPDF(logo_path=logo_path, curso=curso, turma=turma, aluno_nome=dados_aluno['nome'], matricula=dados_aluno['matricula'])
    pdf.add_page()
    
    df_materias = dados_aluno['materias'].copy()
    
    # Recalcula a nota se ela estiver zerada ou nula, buscando a média das notas dinâmicas
    import math
    import json
    for idx, row in df_materias.iterrows():
        val = float(row.get('Nota', 0.0))
        if val == 0.0 or math.isnan(val):
            detalhes = row.get('Detalhes_JSON', {})
            if isinstance(detalhes, str):
                try:
                    detalhes = json.loads(detalhes)
                except:
                    detalhes = {}
            if isinstance(detalhes, dict):
                notas_dinamicas = detalhes.get('notas', {})
                if notas_dinamicas:
                    valores = [float(v) for v in notas_dinamicas.values() if v is not None and not math.isnan(float(v))]
                    if valores:
                        df_materias.at[idx, 'Nota'] = sum(valores) / len(valores)

    qtd_modulos = len(df_materias)
    media_geral = df_materias['Nota'].mean() if qtd_modulos > 0 else 0
    
    # Box "Módulos", "Média Geral", "Frequência Geral"
    pdf.set_draw_color(220, 220, 220)
    pdf.set_line_width(0.3)
    pdf.rect(15, pdf.get_y(), 180, 18, style='D')
    
    pdf.set_xy(20, pdf.get_y() + 3)
    pdf.set_font('helvetica', '', 9)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(50, 5, "MÓDULOS", ln=0)
    pdf.cell(50, 5, "MÉDIA GERAL", ln=0)
    pdf.cell(50, 5, "FREQUÊNCIA GERAL", ln=1)
    
    pdf.set_xy(20, pdf.get_y())
    pdf.set_font('helvetica', 'B', 14)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(50, 7, str(qtd_modulos), ln=0)
    pdf.cell(50, 7, f"{media_geral:.1f}", ln=0)
    pdf.cell(50, 7, f"{freq_global:.0f}%", ln=1)
    
    pdf.ln(7)
    
    # Matérias / Cards
    for _, row in df_materias.iterrows():
        # Prevent page break inside a card if possible
        if pdf.get_y() > 220:
            pdf.add_page()
            
        materia_nome = str(row['Matéria'])
        nota_media = float(row['Nota'])
        p = int(row['Presenças'])
        f = int(row['Faltas'])
        freq = float(row['Frequência (%)'])
        aulas = p + f
        
        start_y = pdf.get_y()
        
        pdf.set_font('helvetica', 'B', 11)
        pdf.set_text_color(0, 15, 60)
        # Title of subject
        pdf.cell(90, 8, f"{materia_nome}", ln=0)
        
        # Right aligned stats
        pdf.set_font('helvetica', '', 10)
        pdf.set_text_color(50, 50, 50)
        stats = f"Média: {nota_media:.1f}   P: {p}   F: {f}   Aulas: {aulas}   Freq: {freq:.0f}%"
        pdf.cell(90, 8, stats, align='R', ln=1)
        
        # Dynamic Grades Table
        detalhes = row.get('Detalhes_JSON', {})
        if isinstance(detalhes, str):
            import json
            try: detalhes = json.loads(detalhes)
            except: detalhes = {}
            
        notas_dinamicas = detalhes.get('notas', {}) if isinstance(detalhes, dict) else {}
        freq_lista = detalhes.get('frequencia', []) if isinstance(detalhes, dict) else []
        
        # Prepare columns: Dynamic + Média
        cols_notas = list(notas_dinamicas.keys())
        cols_todas = cols_notas + ['Média']

        # Largura útil real da página (respeita as margens) — a tabela nunca
        # ultrapassa a margem direita.
        usable_w = pdf.w - pdf.l_margin - pdf.r_margin
        n_cols = len(cols_todas)
        w_col = (usable_w / n_cols) if n_cols else usable_w
        pad = 1.2  # respiro interno horizontal (mm)

        labels = [_limpar_label(c) for c in cols_todas]

        # Escolhe o MAIOR tamanho de fonte (<=8) em que todos os rótulos caibam
        # em no máximo 2 linhas dentro da coluna. Assim os nomes aparecem
        # inteiros (sem cortar) e colunas parecidas continuam distinguíveis.
        header_size = 5
        for size in (8, 7.5, 7, 6.5, 6, 5.5, 5):
            ok = True
            for lb in labels:
                ls = _quebrar_em_linhas(pdf, lb, w_col - pad, size)
                if any(pdf.get_string_width(x) > (w_col - pad) for x in ls):
                    ok = False
                    break
                # se a quebra em 2 linhas ainda não cobriu o texto, não serve
                if len(" ".join(ls)) < len(lb.replace("  ", " ")):
                    ok = False
                    break
            if ok:
                header_size = size
                break

        # ---- Cabeçalho (2 linhas de altura, com borda e fundo) ----
        header_h = 8.0
        x0 = pdf.l_margin
        y0 = pdf.get_y()
        line_h = header_size * 0.40 + 0.6  # altura aproximada de cada linha (mm)
        pdf.set_fill_color(245, 245, 245)
        pdf.set_text_color(50, 50, 50)
        pdf.set_draw_color(210, 210, 210)
        for i, lb in enumerate(labels):
            x = x0 + i * w_col
            pdf.rect(x, y0, w_col, header_h, style='DF')
            ls = _quebrar_em_linhas(pdf, lb, w_col - pad, header_size)
            ls = [_ajustar_a_largura(pdf, t, w_col - pad, header_size) for t in ls]
            pdf.set_font('helvetica', '', header_size)
            ty = y0 + (header_h - len(ls) * line_h) / 2
            for linha in ls:
                pdf.set_xy(x, ty)
                pdf.cell(w_col, line_h, linha, align='C')
                ty += line_h
        pdf.set_xy(x0, y0 + header_h)

        # ---- Linha de valores ----
        val_font_size = 10 if n_cols <= 6 else (9 if n_cols <= 8 else 8)
        pdf.set_font('helvetica', '', val_font_size)
        pdf.set_text_color(0, 0, 0)
        y_val = pdf.get_y()
        val_h = 8.0
        for i, c in enumerate(cols_todas):
            x = x0 + i * w_col
            if c == 'Média':
                txt = f"{nota_media:.1f}"
            else:
                val = notas_dinamicas[c]
                if val == 0.0 or pd.isna(val):
                    txt = "—"
                elif isinstance(val, float) and val.is_integer():
                    txt = f"{int(val)}"
                elif isinstance(val, float):
                    txt = f"{val:.1f}"
                else:
                    txt = _ajustar_a_largura(pdf, str(val), w_col - pad, val_font_size)
            pdf.rect(x, y_val, w_col, val_h, style='D')
            pdf.set_xy(x, y_val)
            pdf.cell(w_col, val_h, txt, align='C')
        pdf.set_y(y_val + val_h)
        
        # Frequencia boxes
        pdf.ln(3)
        # Assume minimum 20 boxes to match layout, or more if there are more classes
        qtd_boxes = max(len(freq_lista), 20)
        box_size = 7
        x_pos = 15
        y_pos = pdf.get_y()
        
        pdf.set_font('helvetica', '', 8)
        
        for i in range(qtd_boxes):
            val = freq_lista[i] if i < len(freq_lista) else ''
            
            # Determine color based on P/F
            if val == 'P':
                pdf.set_draw_color(34, 197, 94) # Green
                pdf.set_text_color(34, 197, 94)
            elif val == 'F':
                pdf.set_draw_color(239, 68, 68) # Red
                pdf.set_text_color(239, 68, 68)
            else:
                pdf.set_draw_color(200, 200, 200) # Gray
                pdf.set_text_color(100, 100, 100)
                
            pdf.set_xy(x_pos, y_pos)
            pdf.cell(box_size, box_size, str(i+1), border=1, align='C')
            x_pos += box_size + 1.5
            
            if x_pos + box_size > 195:
                x_pos = 15
                y_pos += box_size + 2
                
        # Move Y to below the boxes
        pdf.set_y(y_pos + box_size + 4)
        
        # Draw outer rectangle
        end_y = pdf.get_y()
        pdf.set_draw_color(220, 220, 220)
        pdf.rect(14, start_y - 2, 182, end_y - start_y + 2, style='D')
        pdf.ln(2)

    # Feedback Box
    if feedback:
        if pdf.get_y() > 240:
            pdf.add_page()
        pdf.ln(5)
        pdf.set_draw_color(220, 220, 220)
        start_y = pdf.get_y()
        
        pdf.set_font('helvetica', '', 11)
        
        pdf.set_xy(18, start_y + 3)
        pdf.set_font('helvetica', 'B', 9)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(100, 5, "FEEDBACK DO PROFESSOR", ln=1)
        
        pdf.set_xy(18, start_y + 9)
        pdf.set_font('helvetica', '', 11)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(174, 5, str(feedback))
        
        end_y = pdf.get_y()
        pdf.rect(15, start_y, 180, (end_y - start_y) + 5, style='D')
        pdf.set_y(end_y + 10)

    # ---- Assinaturas (para quem quiser a versão impressa) ----
    # Garante espaço; se não couber, joga para a próxima página.
    if pdf.get_y() > 245:
        pdf.add_page()
    pdf.ln(22)  # espaço em branco acima das linhas para assinar

    col_w = 75
    x_esq = 22
    x_dir = 113
    y_linha = pdf.get_y()

    pdf.set_draw_color(80, 80, 80)
    pdf.set_line_width(0.3)
    pdf.line(x_esq, y_linha, x_esq + col_w, y_linha)
    pdf.line(x_dir, y_linha, x_dir + col_w, y_linha)

    pdf.set_font('helvetica', '', 9)
    pdf.set_text_color(80, 80, 80)
    pdf.set_xy(x_esq, y_linha + 1)
    pdf.cell(col_w, 5, "Assinatura do Professor", align='C')
    pdf.set_xy(x_dir, y_linha + 1)
    pdf.cell(col_w, 5, "Assinatura do Aluno ou Responsável", align='C')

    # Nome impresso abaixo do rótulo
    pdf.set_font('helvetica', '', 8)
    pdf.set_text_color(120, 120, 120)
    if professor:
        pdf.set_xy(x_esq, y_linha + 6)
        pdf.cell(col_w, 4, str(professor).upper()[:45], align='C')
    pdf.set_xy(x_dir, y_linha + 6)
    pdf.cell(col_w, 4, str(dados_aluno.get('nome', '')).upper()[:45], align='C')

    # Output
    output_dir = "boletins_gerados"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    nome_limpo = str(dados_aluno['nome']).replace(' ', '_').replace('/', '_')
    nome_arquivo = f"Boletim_{dados_aluno['matricula']}_{nome_limpo}.pdf"
    output_path = os.path.join(output_dir, nome_arquivo)
    pdf.output(output_path)
    
    return output_path

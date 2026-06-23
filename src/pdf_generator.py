from fpdf import FPDF
import os
import datetime

class BoletimPDF(FPDF):
    def __init__(self, logo_path=None, curso="", turma="", aluno_nome="", matricula=""):
        super().__init__()
        self.logo_path = logo_path
        self.curso = curso
        self.turma = turma
        self.aluno_nome = aluno_nome
        self.matricula = matricula
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        # Logo da ALLNET (se existir)
        x_offset = 15
        if self.logo_path and os.path.exists(self.logo_path):
            try:
                self.image(self.logo_path, 15, 6, 35)
                x_offset = 55 # Desloca o texto pra direita do logo
            except:
                pass
        
        # ALL NET
        self.set_font('helvetica', 'B', 12)
        self.set_text_color(0, 0, 0)
        self.set_xy(x_offset, 10)
        self.cell(100, 5, "ALL NET", ln=0)
        
        # Ano
        self.set_font('helvetica', '', 10)
        self.set_text_color(100, 100, 100)
        ano_atual = datetime.datetime.now().year
        self.set_xy(100, 10)
        self.cell(95, 5, str(ano_atual), align='R', ln=1)
        
        # Curso e Turma
        self.set_xy(x_offset, 15)
        self.set_font('helvetica', '', 10)
        self.set_text_color(80, 80, 80)
        curso_str = self.curso.upper() if self.curso else "CURSO LIVRE"
        self.cell(100, 5, f"Boletim Escolar - {curso_str}", ln=0)
        
        self.set_xy(100, 15)
        self.cell(95, 5, f"Turma: {self.turma}", align='R', ln=1)
        
        self.ln(5)
        
        # Linha preta sólida
        y_line = self.get_y()
        self.set_draw_color(0, 0, 0)
        self.set_line_width(0.5)
        self.line(15, y_line, 195, y_line)
        self.ln(5)
        
        # ALUNO e MATRICULA
        self.set_font('helvetica', '', 9)
        self.set_text_color(80, 80, 80)
        self.cell(100, 5, "ALUNO(A)", ln=0)
        self.cell(80, 5, "MATR\u00cdCULA", align='R', ln=1)
        
        self.set_font('helvetica', 'B', 14)
        self.set_text_color(0, 15, 60) # Um azul muito escuro e elegante
        nome_limitado = str(self.aluno_nome).upper()[:50]
        self.cell(140, 7, nome_limitado, ln=0)
        self.cell(40, 7, str(self.matricula), align='R', ln=1)
        
        self.ln(2)
        
        # Linha pontilhada (simulada com retas curtas)
        y_line2 = self.get_y()
        self.set_draw_color(200, 200, 200)
        self.set_line_width(0.2)
        for x in range(15, 195, 3):
            self.line(x, y_line2, x+1.5, y_line2)
            
        self.ln(10)
        self.set_draw_color(0, 0, 0)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def gerar_pdf(dados_aluno, total_presencas, total_faltas, freq_global, responsavel, feedback, chart_buffer, professor="Professor(a)", curso="", turma="", logo_path=None):
    """
    Gera o PDF do boletim escolar para um aluno.
    dados_aluno: dict com 'nome', 'matricula', e 'materias' (DataFrame)
    """
    pdf = BoletimPDF(
        logo_path=logo_path, 
        curso=curso, 
        turma=turma, 
        aluno_nome=dados_aluno['nome'], 
        matricula=dados_aluno['matricula']
    )
    pdf.add_page()
    
    # As informações do cabeçalho agora são impressas automaticamente pela classe BoletimPDF
    
    # Tabela de Desempenho - Cabeçalho
    pdf.set_fill_color(240, 240, 240)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('helvetica', 'B', 10)
    
    larguras = [75, 20, 25, 25, 35]
    colunas = ['Matéria', 'Nota', 'Presenças', 'Faltas', 'Frequência (%)']
    
    for w, col in zip(larguras, colunas):
        pdf.cell(w, 10, col, border=1, align='C', fill=True)
    pdf.ln()
    
    # Tabela de Desempenho - Linhas
    pdf.set_font('helvetica', '', 10)
    df_materias = dados_aluno['materias']
    
    for _, row in df_materias.iterrows():
        # Aumenta o limite de corte do nome e adiciona reticências se passar
        materia_nome = str(row['Matéria']).strip()
        if len(materia_nome) > 40:
            materia_nome = materia_nome[:37] + "..."
            
        pdf.cell(larguras[0], 10, materia_nome, border=1, align='C')
        pdf.cell(larguras[1], 10, str(row['Nota']), border=1, align='C')
        pdf.cell(larguras[2], 10, str(row['Presenças']), border=1, align='C')
        pdf.cell(larguras[3], 10, str(row['Faltas']), border=1, align='C')
        pdf.cell(larguras[4], 10, f"{row['Frequência (%)']:.1f}%", border=1, align='C')
        pdf.ln()
        
    pdf.ln(10)
    
    # Resumo Global e Frequência Total
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(0, 10, f"Frequência Total: {freq_global:.1f}%", ln=1, align='C')
    pdf.ln(5)
    
    y_start = pdf.get_y()
    
    # Salva temporariamente a imagem do gráfico se existir
    if chart_buffer:
        chart_temp_path = f"temp_chart_{dados_aluno['matricula']}.png"
        with open(chart_temp_path, "wb") as f:
            f.write(chart_buffer.getbuffer())
    
    # Layout de Feedback e Gráfico Lado a Lado
    if feedback:
        pdf.set_font('helvetica', 'B', 12)
        pdf.cell(120, 8, "Observações e Feedback:", ln=0)
        
        if chart_buffer:
            # Título do gráfico à direita
            pdf.cell(70, 8, "Proporção de Presenças:", ln=1, align='C')
        else:
            pdf.ln(8)
            
        y_content = pdf.get_y()
        
        # Desenha a caixa de feedback na esquerda
        pdf.set_font('helvetica', '', 10)
        pdf.multi_cell(120, 6, feedback, border=1)
        y_after_feedback = pdf.get_y()
        
        # Insere o gráfico na direita
        if chart_buffer:
            pdf.image(chart_temp_path, x=145, y=y_content, w=45)
            y_after_chart = y_content + 48
            pdf.set_y(max(y_after_feedback, y_after_chart))
            os.remove(chart_temp_path)
        else:
            pdf.set_y(y_after_feedback)
            
    else:
        # Se não há feedback, apenas mostra o gráfico reduzido e centralizado
        if chart_buffer:
            x_pos = (210 - 45) / 2
            pdf.image(chart_temp_path, x=x_pos, y=y_start, w=45)
            pdf.set_y(y_start + 48)
            os.remove(chart_temp_path)
        
    # Campos de Assinatura (Fundo da página)
    pdf.ln(25) # Espaçamento para as assinaturas
    y_assinatura = pdf.get_y()
    
    # Se a página quebrar, pegamos o novo Y
    if y_assinatura > 260: 
        pdf.add_page()
        y_assinatura = pdf.get_y() + 20
        
    # Linha do Professor (Esquerda)
    pdf.line(20, y_assinatura, 90, y_assinatura)
    pdf.set_xy(20, y_assinatura + 2)
    pdf.set_font('helvetica', '', 9)
    # Limita o nome do professor para não estourar a linha
    prof_limitado = str(professor).upper()[:35]
    pdf.cell(70, 5, f"Professor(a): {prof_limitado}", align='C')
    
    # Linha do Responsável/Aluno (Direita)
    pdf.line(120, y_assinatura, 190, y_assinatura)
    pdf.set_xy(120, y_assinatura + 2)
    pdf.cell(70, 5, "Responsável / Aluno(a)", align='C')
        
    # Salvar
    # Criar pasta de saída se não existir
    output_dir = "boletins_gerados"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    nome_limpo = str(dados_aluno['nome']).replace(' ', '_').replace('/', '_')
    nome_arquivo = f"Boletim_{dados_aluno['matricula']}_{nome_limpo}.pdf"
    output_path = os.path.join(output_dir, nome_arquivo)
    pdf.output(output_path)
    
    return output_path

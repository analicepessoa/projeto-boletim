import matplotlib.pyplot as plt
import io

def gerar_grafico_frequencia(total_presencas, total_faltas):
    """Gera um gráfico de rosca (donut chart) com o total de presenças e faltas."""
    if total_presencas == 0 and total_faltas == 0:
        return None

    labels = ['Presenças', 'Faltas']
    sizes = [total_presencas, total_faltas]
    colors = ['#10B981', '#EF4444'] # Verde esmeralda e vermelho moderno
    
    fig, ax = plt.subplots(figsize=(4, 4), dpi=150)
    
    # Desenhar o gráfico de pizza
    wedges, texts, autotexts = ax.pie(
        sizes, 
        colors=colors, 
        labels=labels, 
        autopct='%1.1f%%',
        pctdistance=0.75,
        startangle=140, 
        wedgeprops=dict(width=0.4, edgecolor='white', linewidth=2),
        textprops={'color': '#333333', 'fontsize': 10, 'weight': 'bold'}
    )
    
    # Desenha o círculo branco no meio para o Donut Chart
    centre_circle = plt.Circle((0,0), 0.60, fc='white')
    ax.add_artist(centre_circle)
    
    # Estilizar o texto de porcentagem
    plt.setp(autotexts, size=11, weight="bold", color="white")
    
    # Remover bordas externas
    ax.axis('equal') 
    
    # Título centralizado
    ax.set_title('Proporção Global', fontsize=12, fontweight='bold', pad=15)
    
    # Salvar em buffer de memória
    img_buffer = io.BytesIO()
    plt.savefig(img_buffer, format='png', bbox_inches='tight', transparent=True)
    img_buffer.seek(0)
    plt.close()
    
    return img_buffer

import pandas as pd

def localizar_cabecalho(df):
    """Varre as primeiras linhas para encontrar onde a tabela realmente começa."""
    # Primeiro checa se o pandas já acertou o cabeçalho de cara (linha 1)
    cols = [str(c).lower() for c in df.columns]
    if any('matr' in c for c in cols) and any('nome' in c for c in cols):
        return df

    # Se não acertou, varre as 15 primeiras linhas procurando as palavras-chave
    for idx, row in df.head(15).iterrows():
        valores = [str(v).lower() for v in row.values]
        if any('matr' in v for v in valores) and any('nome' in v for v in valores):
            # Encontrou a linha do cabeçalho!
            df.columns = df.iloc[idx] # Define a linha atual como cabeçalho
            df = df.iloc[idx+1:].reset_index(drop=True) # Descarta o lixo acima
            return df
            
    return df # Retorna original se não achar

def processar_planilhas(arquivos_com_materias):
    """
    Processa múltiplas planilhas e unifica pelo número da matrícula.
    Retorna um DataFrame único contendo os dados de todas as matérias processadas.
    """
    if not arquivos_com_materias:
        return pd.DataFrame()

    dados_consolidados = []

    for item in arquivos_com_materias:
        arquivo = item['file']
        materia = item['materia']
        
        # Lê a planilha normalmente sem pular linhas de forma fixa
        try:
            if arquivo.name.endswith('.csv'):
                df = pd.read_csv(arquivo)
            else:
                df = pd.read_excel(arquivo)
        except Exception as e:
            raise ValueError(f"Erro ao ler a planilha {arquivo.name}: {e}")

        # Localiza dinamicamente onde a tabela começa
        df = localizar_cabecalho(df)

        colunas_originais = df.columns.tolist()
        
        # Encontra as colunas principais
        col_matricula = next((c for c in colunas_originais if any(x in str(c).lower() for x in ['matr', 'ra', 'id', 'cód', 'cod'])), None)
        col_nome = next((c for c in colunas_originais if any(x in str(c).lower() for x in ['nome', 'aluno', 'estudante'])), None)
        col_nota = next((c for c in colunas_originais if 'prova' in str(c).lower() or 'nota' in str(c).lower()), None)

        if not col_matricula or not col_nome:
            raise ValueError(f"A planilha '{arquivo.name}' não possui colunas de Matrícula ou Nome válidas. Colunas encontradas: {colunas_originais}")

        df.rename(columns={col_matricula: 'Matrícula', col_nome: 'Nome'}, inplace=True)
        if col_nota:
            df.rename(columns={col_nota: 'Nota'}, inplace=True)
        else:
            df['Nota'] = 0.0

        # Filtra as colunas de aulas (qualquer coluna que tenha 'aula' no nome ou comece com 'A' curto)
        colunas_aulas = [col for col in df.columns if 'aula' in str(col).lower() or (str(col).lower().startswith('a') and len(str(col)) <= 3)]
        
        # Converte valores para maiúsculo para garantir a contagem e remove espaços em branco
        for col in colunas_aulas:
            df[col] = df[col].astype(str).str.strip().str.upper()

        df['Presenças'] = (df[colunas_aulas] == 'P').sum(axis=1)
        df['Faltas'] = (df[colunas_aulas] == 'F').sum(axis=1)

        # Evita divisão por zero
        df['Frequência (%)'] = df.apply(
            lambda row: (row['Presenças'] / row_total * 100) if (row_total := row['Presenças'] + row['Faltas']) > 0 else 0, 
            axis=1
        )

        df['Matéria'] = materia

        # Seleciona apenas as colunas essenciais
        colunas_finais = ['Matrícula', 'Nome', 'Matéria', 'Nota', 'Presenças', 'Faltas', 'Frequência (%)']
        
        # Dropa linhas vazias
        df_resumo = df[colunas_finais].dropna(subset=['Matrícula', 'Nome'])
        dados_consolidados.append(df_resumo)

    if not dados_consolidados:
        return pd.DataFrame()

    # Concatena todos os DataFrames
    df_final = pd.concat(dados_consolidados, ignore_index=True)
    return df_final

def obter_resumo_aluno(df_consolidado, matricula):
    """Retorna os dados consolidados de um aluno específico e o total global de frequência."""
    df_aluno = df_consolidado[df_consolidado['Matrícula'] == matricula]
    if df_aluno.empty:
        return None, 0, 0, 0

    total_presencas = df_aluno['Presenças'].sum()
    total_faltas = df_aluno['Faltas'].sum()
    total_geral = total_presencas + total_faltas

    frequencia_global = (total_presencas / total_geral * 100) if total_geral > 0 else 0

    return df_aluno, total_presencas, total_faltas, frequencia_global

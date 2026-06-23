import os
import sys
import streamlit.web.cli as stcli
# Forçar o PyInstaller a empacotar essas bibliotecas:
import pandas
import fpdf
import matplotlib
import matplotlib.pyplot
import openpyxl

def resolve_path(path):
    # Quando o app está compilado pelo PyInstaller, as variáveis sys mudam.
    # __file__ não existe e o diretório de execução passa a ser onde o exe está.
    if getattr(sys, 'frozen', False):
        application_path = sys._MEIPASS
    else:
        application_path = os.path.dirname(os.path.abspath(__file__))
        
    return os.path.join(application_path, path)

if __name__ == "__main__":
    app_path = resolve_path("app.py")
    
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--global.developmentMode=false",
    ]
    sys.exit(stcli.main())

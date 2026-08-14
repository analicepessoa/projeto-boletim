"""Validação e conversão dos pacotes gerados pelo Importador ALLNET."""

from __future__ import annotations

import json
import math
import re
import unicodedata
from difflib import SequenceMatcher

import pandas as pd


FORMATO_PACOTE_ALLNET = "allnet-boletins/v1"


def normalizar_texto(valor: object) -> str:
    texto = unicodedata.normalize("NFKD", str(valor or ""))
    texto = "".join(ch for ch in texto if not unicodedata.combining(ch))
    texto = texto.replace("\xa0", " ").lower()
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    return " ".join(texto.split())


def _numero(valor: object, padrao: float = 0.0) -> float:
    if valor is None or isinstance(valor, bool):
        return padrao
    if isinstance(valor, str):
        valor = valor.strip().replace(",", ".")
        if not valor:
            return padrao
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return padrao
    return numero if math.isfinite(numero) else padrao


def carregar_pacote_allnet(conteudo: bytes | str) -> dict:
    """Lê um pacote sem confiar em campos fora do formato esperado."""
    if isinstance(conteudo, bytes):
        if len(conteudo) > 15 * 1024 * 1024:
            raise ValueError("O arquivo é maior que o limite de 15 MB.")
        conteudo = conteudo.decode("utf-8-sig")

    try:
        pacote = json.loads(conteudo)
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Este arquivo não é um pacote válido do Importador ALLNET.") from exc

    if not isinstance(pacote, dict) or pacote.get("formato") != FORMATO_PACOTE_ALLNET:
        raise ValueError("Formato não reconhecido. Gere o arquivo pelo Importador ALLNET.")

    turma = pacote.get("turma")
    modulos = pacote.get("modulos")
    if not isinstance(turma, dict) or not str(turma.get("nome", "")).strip():
        raise ValueError("O pacote não informa a turma de origem.")
    if not isinstance(modulos, list) or not modulos:
        raise ValueError("O pacote não contém módulos para importar.")
    if len(modulos) > 100:
        raise ValueError("O pacote contém módulos demais para uma única importação.")

    nomes = []
    total_alunos = 0
    for modulo in modulos:
        if not isinstance(modulo, dict):
            raise ValueError("Há um módulo inválido no pacote.")
        nome = str(modulo.get("nome", "")).strip()
        alunos = modulo.get("alunos")
        if not nome or not isinstance(alunos, list):
            raise ValueError("Há um módulo sem nome ou sem lista de alunos.")
        nomes.append(normalizar_texto(nome))
        total_alunos += len(alunos)

    if len(nomes) != len(set(nomes)):
        raise ValueError("O pacote repete o mesmo módulo mais de uma vez.")
    if total_alunos > 5000:
        raise ValueError("O pacote contém registros demais para uma única importação.")

    return pacote


def sugerir_materia(nome_modulo: str, materias: list[dict]) -> tuple[str | None, str]:
    """Encontra a matéria mais provável, preferindo correspondências inequívocas."""
    alvo = normalizar_texto(nome_modulo)
    candidatos = [
        (str(materia["id"]), normalizar_texto(materia.get("nome", "")))
        for materia in materias
        if materia.get("id") and normalizar_texto(materia.get("nome", ""))
    ]

    exatos = [materia_id for materia_id, nome in candidatos if nome == alvo]
    if len(exatos) == 1:
        return exatos[0], "nome idêntico"

    contidos = [
        materia_id
        for materia_id, nome in candidatos
        if min(len(nome), len(alvo)) >= 7 and (nome in alvo or alvo in nome)
    ]
    if len(contidos) == 1:
        return contidos[0], "nome equivalente"

    pontuados = sorted(
        ((SequenceMatcher(None, alvo, nome).ratio(), materia_id) for materia_id, nome in candidatos),
        reverse=True,
    )
    if pontuados:
        melhor, materia_id = pontuados[0]
        segundo = pontuados[1][0] if len(pontuados) > 1 else 0.0
        if melhor >= 0.78 and melhor - segundo >= 0.08:
            return materia_id, "nome semelhante"

    return None, "precisa de conferência"


def modulo_para_dataframe(modulo: dict, nome_materia: str) -> pd.DataFrame:
    """Transforma um módulo validado no mesmo formato usado pelas planilhas."""
    registros = []
    for aluno in modulo.get("alunos", []):
        if not isinstance(aluno, dict):
            continue

        matricula = str(aluno.get("ctr", aluno.get("matricula", ""))).strip()
        if matricula.endswith(".0") and matricula[:-2].isdigit():
            matricula = matricula[:-2]
        nome = str(aluno.get("nome", "")).strip()
        if not matricula or not nome:
            continue

        frequencia = aluno.get("frequencia_detalhada", [])
        if not isinstance(frequencia, list):
            frequencia = []
        frequencia = [str(item or "").strip().upper()[:1] for item in frequencia]

        notas_detalhadas = aluno.get("notas_detalhadas", {})
        if not isinstance(notas_detalhadas, dict):
            notas_detalhadas = {}
        notas_detalhadas = {
            str(chave): _numero(valor)
            for chave, valor in notas_detalhadas.items()
            if str(chave).strip()
        }

        nota = _numero(aluno.get("nota"))
        if nota == 0.0 and notas_detalhadas:
            nota = sum(notas_detalhadas.values()) / len(notas_detalhadas)

        presencas = int(_numero(aluno.get("presencas"), frequencia.count("P")))
        faltas = int(_numero(aluno.get("faltas"), frequencia.count("F")))
        total = presencas + faltas

        registros.append(
            {
                "Matrícula": matricula,
                "Nome": nome,
                "Matéria": nome_materia,
                "Nota": nota,
                "Presenças": max(presencas, 0),
                "Faltas": max(faltas, 0),
                "Frequência (%)": (presencas / total * 100) if total else 0.0,
                "Frequencia_Detalhada": frequencia,
                "Notas_Detalhadas": notas_detalhadas,
            }
        )

    return pd.DataFrame(
        registros,
        columns=[
            "Matrícula",
            "Nome",
            "Matéria",
            "Nota",
            "Presenças",
            "Faltas",
            "Frequência (%)",
            "Frequencia_Detalhada",
            "Notas_Detalhadas",
        ],
    )


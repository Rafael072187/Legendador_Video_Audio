"""Interface web do Legendador de Vídeo e Áudio (Streamlit).

Duas telas:

- **Extrair legenda** — transcreve o vídeo/áudio localmente com o Whisper.
- **Inserir legenda** — coloca essa legenda dentro do vídeo, na linha do
  tempo original (queimada ou como faixa).

Para abrir a interface:

    uv run streamlit run main.py

`python main.py` também funciona: o arquivo detecta que foi executado fora do
Streamlit e se reinicia pelo comando correto.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import streamlit as st

import tela_extrair
import tela_inserir

TELAS = {
    "Extrair legenda": tela_extrair.render,
    "Inserir legenda": tela_inserir.render,
}


def meu_app() -> None:
    """Cabeçalho, navegação entre as telas e a tela escolhida."""
    # Precisa ser o primeiro comando do Streamlit executado na página.
    st.set_page_config(
        page_title="Legendador de Vídeo e Áudio",
        page_icon="🎬",
        layout="centered",
    )

    st.title("Legendador de Vídeo e Áudio")
    st.caption(
        "🔒 **100% local e gratuito** — nada de API paga, nada sai do seu "
        "computador. Depois do primeiro download do modelo, funciona sem internet."
    )

    with st.sidebar:
        st.subheader("Tela")
        escolhida = st.radio(
            "Tela",
            list(TELAS),
            key="tela_atual",
            label_visibility="collapsed",
        )

    TELAS[escolhida]()


# --------------------------------------------------------------------------- #
# Execução
# --------------------------------------------------------------------------- #


def _fora_do_streamlit() -> bool:
    """True quando o arquivo foi rodado direto (`python main.py`).

    Nesse modo o Streamlit não cria o contexto da sessão, e nada funciona:
    a tela não sobe e o app só emite avisos de `missing ScriptRunContext`.
    """
    from streamlit.runtime.scriptrunner import get_script_run_ctx

    # suppress_warning: aqui a ausência de contexto é o comportamento
    # esperado, não um problema a ser logado.
    return get_script_run_ctx(suppress_warning=True) is None


def _iniciar_pelo_streamlit() -> int:
    """Reinicia este arquivo pelo comando `streamlit run` e espera terminar."""
    comando = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(Path(__file__).resolve()),
        *sys.argv[1:],
    ]

    print("Iniciando a interface do Legendador...", flush=True)
    print("  " + " ".join(comando), flush=True)
    print("Pressione Ctrl+C para encerrar.\n", flush=True)

    return subprocess.call(comando)


if __name__ == "__main__":
    if _fora_do_streamlit():
        raise SystemExit(_iniciar_pelo_streamlit())
    meu_app()

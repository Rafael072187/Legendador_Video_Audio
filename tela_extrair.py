"""Tela 1: extrai a legenda de um vídeo ou áudio."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from legendador import (
    EXTENSOES_SUPORTADAS,
    MODELO_PADRAO,
    ErroLegendagem,
    ResultadoLegenda,
    dispositivo_padrao,
    legendar,
)
from ui import (
    ORIGENS,
    campo_arquivo,
    campo_pasta,
    cartao,
    formatar_duracao,
)

IDIOMAS = {
    "Português": "pt",
    "Inglês": "en",
    "Espanhol": "es",
    "Francês": "fr",
    "Italiano": "it",
    "Alemão": "de",
    "Japonês": "ja",
    "Detecção automática": None,
}

MODELOS = {
    "tiny — mais rápido, menor qualidade (75 MB)": "tiny",
    "base — rápido, qualidade básica (145 MB)": "base",
    "small — equilibrado, recomendado (484 MB)": MODELO_PADRAO,
    "medium — lento, alta qualidade (1,5 GB)": "medium",
    "large-v3 — muito lento, máxima qualidade (3 GB)": "large-v3",
}

FORMATOS = {
    "SRT (SubRip)": "srt",
    "VTT (WebVTT)": "vtt",
}

CHAVE_RESULTADO = "resultado"
CHAVE_ARQUIVO = "resultado_arquivo"
CHAVE_OPCOES = "resultado_opcoes"

# Vídeo de onde a legenda saiu: a tela de inserção reaproveita esta referência.
CHAVE_MIDIA = "midia_extraida"


def _exibir_resultado(resultado: ResultadoLegenda, origem: object) -> None:
    """Mostra a legenda gerada, o download e a opção de salvar numa pasta."""
    st.success(f"Arquivo **{resultado.nome_base}** legendado com sucesso.")

    if resultado.idioma_detectado:
        st.caption(
            f"Idioma detectado: **{resultado.idioma_detectado}** "
            f"({resultado.probabilidade_idioma:.0%} de confiança)"
        )

    col_duracao, col_blocos, col_modelo, col_velocidade = st.columns(4)
    with col_duracao:
        st.metric("Duração", formatar_duracao(resultado.duracao_segundos))
    with col_blocos:
        st.metric("Blocos", str(len(resultado.legendas)))
    with col_modelo:
        st.metric("Modelo", f"{resultado.modelo} ({resultado.dispositivo})")
    with col_velocidade:
        if resultado.velocidade:
            st.metric("Velocidade", f"{resultado.velocidade:.1f}x tempo real")
        else:
            st.metric("Velocidade", "—")

    st.download_button(
        "⬇️ Baixar legenda",
        data=resultado.srt,
        file_name=resultado.nome_saida,
        mime="application/x-subrip" if resultado.srt.startswith("1\n") else "text/vtt",
        type="primary",
    )

    with st.expander("💾 Salvar a legenda numa pasta", expanded=False):
        pasta = campo_pasta(
            "Pasta de destino",
            chave="pasta_saida_legenda",
            origem=origem,
            ajuda=(
                "Pasta onde a legenda será gravada. O padrão é a pasta do arquivo "
                "original — troque à vontade."
            ),
        )
        nome = st.text_input(
            "Nome do arquivo",
            value=resultado.nome_saida,
            key="nome_saida_legenda",
            help="Se você não puser extensão, a do formato escolhido é usada.",
        ).strip()

        alvo = (Path(pasta) / nome) if pasta is not None and nome else None
        if st.button("Salvar legenda", disabled=alvo is None) and alvo is not None:
            if not alvo.suffix:
                alvo = alvo.with_suffix(Path(resultado.nome_saida).suffix)
            try:
                alvo.parent.mkdir(parents=True, exist_ok=True)
                alvo.write_text(resultado.srt, encoding="utf-8")
            except OSError as exc:
                st.error(f"Não foi possível salvar a legenda: {exc}")
            else:
                st.success(f"Legenda salva em **{alvo}**.")

    with st.expander("Pré-visualizar legenda", expanded=True):
        st.code(resultado.srt, language="srt")


def _opcoes_na_barra_lateral() -> tuple[str | None, str, str, str | None, bool]:
    """Desenha os seletores e devolve (idioma, modelo, formato, dispositivo, vad)."""
    with st.sidebar:
        st.subheader("Opções de extração")

        idioma = st.selectbox("Idioma do áudio", list(IDIOMAS), index=0)
        modelo = st.selectbox("Modelo Whisper", list(MODELOS), index=2)
        formato = st.selectbox("Formato de saída", list(FORMATOS), index=0)

        padrao = dispositivo_padrao()
        opcoes_dispositivo = ["Automático"] + (
            ["CPU", "GPU (CUDA)"] if padrao == "cuda" else ["CPU"]
        )
        escolha = st.selectbox("Dispositivo", opcoes_dispositivo, index=0)
        dispositivo = (
            None
            if escolha == "Automático"
            else ("cuda" if "CUDA" in escolha else "cpu")
        )

        vad = st.checkbox(
            "Ignorar trechos sem fala",
            value=True,
            help=(
                "Pula os silêncios: é mais rápido e evita texto inventado em áudio "
                "vazio. Desmarque em **música cantada** ou fala sobre música — "
                "o filtro descarta o canto."
            ),
        )

        st.caption(
            "O áudio é convertido para 16 kHz mono antes da transcrição, "
            "o que acelera o processo sem perda de qualidade."
        )

    return IDIOMAS[idioma], MODELOS[modelo], FORMATOS[formato], dispositivo, vad


def render() -> None:
    """Tela de extração da legenda."""
    st.header("Extrair legenda", divider=True)
    st.caption(
        "🔒 **100% local e gratuito** — a transcrição roda na sua máquina com o "
        "Whisper. Nenhum dado sai do seu computador e não há custo por minuto."
    )

    idioma, modelo, formato, dispositivo, vad = _opcoes_na_barra_lateral()

    with cartao("extracao_arquivo", "📂 Arquivo"):
        origem = st.radio(
            "Origem do arquivo",
            ORIGENS,
            horizontal=True,
            key="origem_extrair",
            help=(
                "O caminho no disco lê o arquivo direto do seu computador: não passa "
                "pelo navegador, não tem limite de tamanho e começa na hora."
            ),
        )

        escolha = campo_arquivo(
            origem,
            prefixo="extrair",
            rotulo="Selecione o vídeo ou áudio",
            tipos=EXTENSOES_SUPORTADAS,
        )
        if escolha is None:
            return

        opcoes = (idioma, modelo, formato, dispositivo, vad)

        # Se o usuário trocou de arquivo, o resultado anterior não vale mais.
        if st.session_state.get(CHAVE_ARQUIVO) != escolha.chave:
            st.session_state.pop(CHAVE_RESULTADO, None)
            st.session_state.pop(CHAVE_MIDIA, None)

        st.caption(escolha.rotulo)
        pedido = st.button("Gerar legenda", type="primary")

    if pedido:
        resultado_existente = st.session_state.get(CHAVE_RESULTADO)

        # Evita refazer o trabalho para o mesmo arquivo com as mesmas opções.
        if (
            resultado_existente is not None
            and st.session_state.get(CHAVE_ARQUIVO) == escolha.chave
            and st.session_state.get(CHAVE_OPCOES) == opcoes
        ):
            st.info(
                "Este arquivo já foi legendado com estas opções. Reutilizando o resultado."
            )
        else:
            with st.status("Processando...", expanded=True) as status:
                # st.status.update() só aceita argumentos nomeados.
                def atualizar(mensagem: str) -> None:
                    status.update(label=mensagem)

                try:
                    resultado = legendar(
                        escolha.entrada,
                        idioma=idioma,
                        modelo=modelo,
                        dispositivo=dispositivo,
                        formato=formato,
                        vad=vad,
                        progresso=atualizar,
                    )
                except ErroLegendagem as exc:
                    status.update(
                        label="Não foi possível gerar a legenda", state="error"
                    )
                    st.error(str(exc))
                except Exception as exc:  # noqa: BLE001 - rede de segurança na UI
                    status.update(label="Erro inesperado", state="error")
                    st.error(f"Erro inesperado: {exc}")
                else:
                    status.update(label="Legenda gerada com sucesso!", state="complete")
                    st.session_state[CHAVE_RESULTADO] = resultado
                    st.session_state[CHAVE_ARQUIVO] = escolha.chave
                    st.session_state[CHAVE_OPCOES] = opcoes
                    st.session_state[CHAVE_MIDIA] = {
                        "entrada": escolha.entrada,
                        "nome": escolha.nome,
                        "chave": escolha.chave,
                        "tamanho": escolha.tamanho,
                    }

    resultado = st.session_state.get(CHAVE_RESULTADO)
    if resultado is not None:
        with cartao("extracao_resultado", "✅ Resultado"):
            _exibir_resultado(resultado, escolha.entrada)

        if st.session_state.get(CHAVE_MIDIA):
            st.caption(
                "A legenda está pronta para ser colocada no vídeo — abra a tela "
                "**Inserir legenda** na barra lateral."
            )

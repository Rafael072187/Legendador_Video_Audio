"""Tela 2: coloca a legenda dentro do vídeo, na linha do tempo original."""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from insercao import (
    MODO_QUEIMAR,
    ROTULOS_MODOS,
    destino_padrao,
    extrair_quadro,
    inserir_legenda,
    momento_de_amostra,
)
from legendador import ErroLegendagem
from legendas import para_srt
from tela_extrair import CHAVE_MIDIA, CHAVE_RESULTADO
from ui import (
    CAMINHO,
    UPLOAD,
    campo_arquivo,
    campo_pasta,
    cartao,
    decodificar_texto,
    formatar_duracao,
    formatar_tamanho,
    formatar_tempo,
)

CHAVE_RESULTADO_INSERCAO = "resultado_insercao"
CHAVE_ENTRADA_INSERCAO = "insercao_entrada"

DA_EXTRACAO = "Vídeo da extração"
ENVIAR_ARQUIVO = "Enviar arquivo"

# Acima disso não vale a pena carregar o vídeo na memória só para o download:
# mostramos o caminho do arquivo.
LIMITE_DOWNLOAD = 50 * 1024 * 1024


def _texto_da_extracao(resultado) -> str:
    """SRT canônico da legenda extraída.

    Mesmo que o usuário tenha escolhido VTT na extração, a inserção usa SRT:
    são os mesmos tempos, no formato que o ffmpeg lê sem conversão.
    """
    if resultado.legendas:
        return para_srt(resultado.legendas)
    return resultado.srt


def _escolher_legenda(resultado) -> str | None:
    """Devolve o texto SRT da legenda a inserir."""
    opcoes = ([DA_EXTRACAO] if resultado is not None else []) + [ENVIAR_ARQUIVO]

    fonte = st.radio(
        "Legenda",
        opcoes,
        horizontal=True,
        key="fonte_legenda",
        help="A legenda gerada na tela de extração é reaproveitada aqui.",
    )

    if fonte == DA_EXTRACAO:
        blocos = len(resultado.legendas) if resultado.legendas else "?"
        st.caption(f"Usando a legenda extraída nesta sessão · **{blocos} blocos**")
        return _texto_da_extracao(resultado)

    arquivo = st.file_uploader(
        "Arquivo de legenda", type=["srt", "vtt"], key="upload_legenda"
    )
    if arquivo is None:
        st.info("Envie um arquivo .srt (ou .vtt).")
        return None

    dados = arquivo.getvalue()
    texto = decodificar_texto(dados)
    if "-->" not in texto:
        st.error(
            "Este arquivo não parece uma legenda SRT/VTT (não há marcação de tempo)."
        )
        return None

    st.caption(f"**{arquivo.name}** · {formatar_tamanho(len(dados))}")
    return texto


def _escolher_video(
    midia: dict | None,
) -> tuple[object, str, str, int] | tuple[None, str, None, int]:
    """Devolve (entrada, nome, chave, tamanho) do vídeo onde a legenda entra."""
    opcoes = ([DA_EXTRACAO] if midia is not None else []) + [CAMINHO, UPLOAD]

    fonte = st.radio(
        "Vídeo onde a legenda entra",
        opcoes,
        horizontal=True,
        key="fonte_video",
        help=(
            "Escolha o mesmo vídeo de onde a legenda saiu: os tempos batem por "
            "construção, sem sincronizar nada à mão."
        ),
    )

    if fonte == DA_EXTRACAO and midia is not None:
        st.caption(f"**{midia['nome']}** · mesmo arquivo de onde a legenda saiu")
        return (
            midia["entrada"],
            midia["nome"],
            midia["chave"],
            midia.get("tamanho", 0),
        )

    escolha = campo_arquivo(
        UPLOAD if fonte == UPLOAD else CAMINHO,
        prefixo="video_inserir",
        rotulo="Selecione o vídeo",
    )
    if escolha is None:
        return None, "", None, 0

    st.caption(escolha.rotulo)
    return escolha.entrada, escolha.nome, escolha.chave, escolha.tamanho


def _verificar_sincronia(resultado_ins, resultado_extracao) -> None:
    """Tira um quadro de dentro da legenda e mostra na tela.

    É a prova visual de que o texto caiu no tempo certo: o quadro vem do vídeo
    final, no meio do primeiro bloco de legenda.
    """
    instante = momento_de_amostra(resultado_ins.duracao_segundos)
    referencia = ""

    if resultado_extracao is not None and resultado_extracao.legendas:
        primeiro = resultado_extracao.legendas[0]
        instante = (primeiro.inicio + primeiro.fim) / 2
        referencia = (
            f", dentro do primeiro bloco "
            f"({formatar_tempo(primeiro.inicio)} → {formatar_tempo(primeiro.fim)})"
        )

    try:
        with tempfile.TemporaryDirectory(prefix="legendador_quadro_") as pasta:
            quadro = extrair_quadro(
                resultado_ins.caminho, instante, Path(pasta) / "quadro.jpg"
            )
            st.image(
                str(quadro),
                caption=f"Quadro do vídeo final em {instante:.1f}s{referencia}",
            )
    except ErroLegendagem:
        return


def _mostrar_resultado(resultado_ins, resultado_extracao) -> None:
    """Confirma o que foi gerado e prova a sincronia com um quadro do vídeo."""
    st.success(
        f"Legenda aplicada em **{resultado_ins.nome}** "
        f"({formatar_tamanho(resultado_ins.tamanho_bytes)})."
    )

    col_tempo, col_duracao, col_modo = st.columns(3)
    with col_tempo:
        st.metric("Tempo", f"{resultado_ins.tempo:.1f}s")
    with col_duracao:
        st.metric("Duração", formatar_duracao(resultado_ins.duracao_segundos))
    with col_modo:
        st.metric("Modo", "Queimada" if resultado_ins.modo == MODO_QUEIMAR else "Faixa")

    st.code(str(resultado_ins.caminho), language=None)

    if resultado_ins.modo == MODO_QUEIMAR:
        _verificar_sincronia(resultado_ins, resultado_extracao)
    elif resultado_ins.faixas_de_legenda:
        st.caption(
            "Faixa de legenda criada · idioma "
            f"**{', '.join(resultado_ins.faixas_de_legenda)}** · "
            "ative a legenda no player."
        )

    if resultado_ins.tamanho_bytes <= LIMITE_DOWNLOAD:
        st.download_button(
            "⬇️ Baixar vídeo legendado",
            data=resultado_ins.caminho.read_bytes(),
            file_name=resultado_ins.nome,
            mime="video/mp4",
            type="primary",
        )
    else:
        st.info(
            "O arquivo é grande demais para download pelo navegador — ele já está "
            "salvo no caminho acima."
        )


def render() -> None:
    """Tela de inserção da legenda."""
    st.header("Inserir legenda no vídeo", divider=True)
    st.caption(
        "A legenda entra na linha do tempo do próprio vídeo. Quando ela vem da "
        "extração, os tempos são os do arquivo original — nada é deslocado."
    )

    resultado = st.session_state.get(CHAVE_RESULTADO)
    midia = st.session_state.get(CHAVE_MIDIA)

    if resultado is None and midia is None:
        st.info(
            "Ainda não há legenda nesta sessão. Gere uma na tela **Extrair legenda** "
            "ou envie um arquivo .srt abaixo."
        )

    with cartao("inserir_legenda", "💬 1 · Legenda"):
        legenda = _escolher_legenda(resultado)

    if legenda is None:
        return

    with cartao("inserir_video", "🎬 2 · Vídeo"):
        video, nome_video, chave_video, tamanho_video = _escolher_video(midia)

        # Legenda de um vídeo aplicada em outro: os tempos podem não bater.
        # Mesmo arquivo escolhido por outro caminho (ex.: "Caminho no disco" em
        # vez de "Vídeo da extração") não é outro vídeo: confere nome e tamanho.
        origem = midia or {}
        chave_origem = origem.get("chave")
        mesmo_arquivo = chave_origem == chave_video or (
            origem.get("nome") == nome_video
            and origem.get("tamanho", -1) == tamanho_video
        )
        if chave_origem and chave_video and not mesmo_arquivo:
            st.warning(
                "A legenda foi extraída de outro vídeo. Se os tempos não baterem, "
                "gere a legenda a partir deste mesmo arquivo."
            )

    if video is None:
        return

    with cartao("inserir_modo", "⚙️ 3 · Como colocar"):
        modo = st.radio(
            "Modo",
            list(ROTULOS_MODOS),
            key="modo_insercao",
            format_func=lambda chave: ROTULOS_MODOS[chave],
            help=(
                "**Queimar** reencoda o vídeo e o texto passa a fazer parte da "
                "imagem. **Embutir** só adiciona uma faixa selecionável — é quase "
                "instantâneo."
            ),
        )

        if modo == MODO_QUEIMAR:
            st.caption(
                "Queimada: aparece em qualquer player, celular e rede social. "
                "O vídeo é reencodado (mais lento)."
            )
        else:
            st.caption(
                "Faixa: o vídeo é copiado sem reencodar (rápido) e a legenda pode "
                "ser ligada e desligada no player."
            )

        # A pasta e o nome são escolhidos; o padrão fica ao lado do vídeo, com
        # outro nome, e o vídeo original nunca é alterado.
        pasta = campo_pasta(
            "Pasta de destino",
            chave="pasta_saida_video",
            origem=video,
            ajuda=(
                "Pasta onde o vídeo legendado será salvo. O padrão é a pasta do "
                "vídeo original — troque à vontade."
            ),
        )
        nome_saida = st.text_input(
            "Nome do arquivo",
            value=destino_padrao(video, modo).name,
            key=f"nome_saida_{modo}",
            help="O original nunca é sobrescrito: mude o nome se quiser.",
        ).strip()

        destino = (
            (Path(pasta) / nome_saida) if pasta is not None and nome_saida else None
        )

        chave_entrada = f"{chave_video}::{modo}::{destino}"
        if st.session_state.get(CHAVE_ENTRADA_INSERCAO) != chave_entrada:
            st.session_state.pop(CHAVE_RESULTADO_INSERCAO, None)

        pedido = st.button("Inserir legenda", type="primary", disabled=destino is None)

    if pedido and destino is not None:
        with st.status("Colocando a legenda...", expanded=True) as status:

            def atualizar(mensagem: str) -> None:
                status.update(label=mensagem)

            try:
                # A pasta pode ter sido digitada agora: criá-la só aqui evita
                # deixar pastas vazias enquanto o usuário ainda está digitando.
                destino.parent.mkdir(parents=True, exist_ok=True)
                resultado_ins = inserir_legenda(
                    video,
                    legenda,
                    modo=modo,
                    destino=destino,
                    progresso=atualizar,
                )
            except OSError as exc:
                status.update(label="Não foi possível criar a pasta", state="error")
                st.error(f"Não foi possível criar a pasta {destino.parent}: {exc}")
            except ErroLegendagem as exc:
                status.update(label="Não foi possível inserir a legenda", state="error")
                st.error(str(exc))
            except Exception as exc:  # noqa: BLE001 - rede de segurança na UI
                status.update(label="Erro inesperado", state="error")
                st.error(f"Erro inesperado: {exc}")
            else:
                status.update(label="Legenda inserida!", state="complete")
                st.session_state[CHAVE_RESULTADO_INSERCAO] = resultado_ins
                st.session_state[CHAVE_ENTRADA_INSERCAO] = chave_entrada

    resultado_ins = st.session_state.get(CHAVE_RESULTADO_INSERCAO)
    if resultado_ins is not None:
        with cartao("inserir_resultado", "✅ Pronto"):
            _mostrar_resultado(resultado_ins, resultado)

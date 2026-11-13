"""Testes das duas telas e da passagem da legenda de uma para a outra."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from conftest import APP, SRT_FALSO

EXTRACAO = "Extrair legenda"
INSERCAO = "Inserir legenda"


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #


def _abrir() -> AppTest:
    at = AppTest.from_file(str(APP), default_timeout=90)
    at.run()
    assert not at.exception
    return at


def _trocar_de_tela(at: AppTest, tela: str) -> None:
    next(r for r in at.radio if r.label == "Tela").set_value(tela)
    at.run()
    assert not at.exception


def _radio(at: AppTest, rotulo: str):
    return next(r for r in at.radio if r.label == rotulo)


def _legendar_upload(at: AppTest, midia: Path, nome: str = "teste.mp4") -> None:
    """Fluxo da tela 1: envia o vídeo e clica em 'Gerar legenda'."""
    at.file_uploader[0].set_value((nome, midia.read_bytes(), "video/mp4"))
    at.run()
    next(b for b in at.button if b.label == "Gerar legenda").click()
    at.run()
    assert not at.exception


def _tem_faixa(video: Path, tipo: str) -> bool:
    saida = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "csv=p=0",
            str(video),
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return tipo in saida


# --------------------------------------------------------------------------- #
# Navegação
# --------------------------------------------------------------------------- #


def test_abre_na_tela_de_extracao():
    at = _abrir()
    assert at.header[0].value == "Extrair legenda"
    assert _radio(at, "Tela").value == EXTRACAO


def test_atinge_a_tela_de_insercao_sem_legenda():
    """Sem nada extraído, a tela 2 explica o que fazer em vez de quebrar."""
    at = _abrir()
    _trocar_de_tela(at, INSERCAO)

    assert at.header[0].value == "Inserir legenda no vídeo"
    assert any("Ainda não há legenda" in i.value for i in at.info)


def test_a_tela_de_insercao_oferece_enviar_um_srt():
    """Quem já tem uma legenda pronta pode usá-la sem passar pela extração."""
    at = _abrir()
    _trocar_de_tela(at, INSERCAO)

    # Só "Enviar arquivo" é oferecido quando não há extração na sessão.
    assert _radio(at, "Legenda").options == ["Enviar arquivo"]
    assert at.file_uploader


# --------------------------------------------------------------------------- #
# Extração -> inserção
# --------------------------------------------------------------------------- #


def test_insercao_reaproveita_o_video_da_extracao(midia_teste, transcricao_mockada):
    """O vídeo de onde a legenda saiu é oferecido na tela 2, sem novo upload."""
    at = _abrir()
    _legendar_upload(at, midia_teste)
    assert any("legendado com sucesso" in s.value for s in at.success)

    _trocar_de_tela(at, INSERCAO)

    assert _radio(at, "Legenda").options == ["Vídeo da extração", "Enviar arquivo"]
    assert _radio(at, "Vídeo onde a legenda entra").value == "Vídeo da extração"
    assert any("mesmo arquivo de onde a legenda saiu" in c.value for c in at.caption)

    # Reaproveitar o vídeo não pede upload de novo.
    assert not at.file_uploader


def test_insercao_avisa_quando_o_video_e_outro(
    midia_teste, transcricao_mockada, tmp_path
):
    """Legenda de um vídeo aplicada em outro: os tempos podem não bater."""
    at = _abrir()
    _legendar_upload(at, midia_teste)
    _trocar_de_tela(at, INSERCAO)

    _radio(at, "Vídeo onde a legenda entra").set_value("Caminho no disco")
    at.run()

    outro = tmp_path / "outro.mp4"
    outro.write_bytes(midia_teste.read_bytes())
    at.text_input[0].set_value(str(outro))
    at.run()

    assert not at.exception
    assert any("extraída de outro vídeo" in w.value for w in at.warning)


# --------------------------------------------------------------------------- #
# Inserção de verdade (ffmpeg)
# --------------------------------------------------------------------------- #


def test_insercao_queimada_pelo_app(midia_teste, transcricao_mockada, tmp_path):
    """Fluxo completo: extrair numa tela e queimar na outra."""
    destino = tmp_path / "final.mp4"

    at = _abrir()
    _legendar_upload(at, midia_teste)
    _trocar_de_tela(at, INSERCAO)

    _radio(at, "Modo").set_value("queimar")
    # O destino padrão de um upload iria para a pasta do usuário: aqui é o tmp.
    next(t for t in at.text_input if t.label == "Salvar como").set_value(str(destino))
    at.run()

    next(b for b in at.button if b.label == "Inserir legenda").click()
    at.run()

    assert not at.exception, at.exception
    assert destino.is_file(), "o ffmpeg deveria ter gerado o vídeo legendado"
    assert not _tem_faixa(destino, "subtitle"), "queimada não deixa faixa no arquivo"
    assert _tem_faixa(destino, "video")

    assert any("Legenda aplicada em" in s.value for s in at.success)
    assert any(m.label == "Modo" and m.value == "Queimada" for m in at.metric)

    # Prova de sincronia: o app mostra um quadro do próprio vídeo final.
    assert at.image, "a tela deveria mostrar um quadro do resultado"


def test_insercao_embutida_pelo_app(midia_teste, transcricao_mockada, tmp_path):
    """No modo faixa, o vídeo não é reencodado e a legenda fica selecionável."""
    destino = tmp_path / "final_faixa.mp4"

    at = _abrir()
    _legendar_upload(at, midia_teste)
    _trocar_de_tela(at, INSERCAO)

    _radio(at, "Modo").set_value("embutir")
    next(t for t in at.text_input if t.label == "Salvar como").set_value(str(destino))
    at.run()

    next(b for b in at.button if b.label == "Inserir legenda").click()
    at.run()

    assert not at.exception, at.exception
    assert destino.is_file()
    assert _tem_faixa(destino, "subtitle")
    assert any(m.label == "Modo" and m.value == "Faixa" for m in at.metric)


def test_modo_invalido_de_saida_mostra_erro(midia_teste, transcricao_mockada, tmp_path):
    """Erro do ffmpeg/validação vira mensagem, não traceback."""
    at = _abrir()
    _legendar_upload(at, midia_teste)
    _trocar_de_tela(at, INSERCAO)

    next(t for t in at.text_input if t.label == "Salvar como").set_value(
        str(tmp_path / "saida.txt")
    )
    at.run()

    next(b for b in at.button if b.label == "Inserir legenda").click()
    at.run()

    assert not at.exception
    assert any(".mp4" in e.value for e in at.error)


def test_resultado_da_insercao_e_limpo_ao_trocar_o_modo(
    midia_teste, transcricao_mockada, tmp_path
):
    """Trocar o modo invalida o resultado mostrado: ele não vale mais."""
    destino = tmp_path / "final.mp4"

    at = _abrir()
    _legendar_upload(at, midia_teste)
    _trocar_de_tela(at, INSERCAO)

    next(t for t in at.text_input if t.label == "Salvar como").set_value(str(destino))
    at.run()
    next(b for b in at.button if b.label == "Inserir legenda").click()
    at.run()
    assert any("Legenda aplicada em" in s.value for s in at.success)

    _radio(at, "Modo").set_value("embutir")
    at.run()

    assert not any("Legenda aplicada em" in s.value for s in at.success)


# --------------------------------------------------------------------------- #
# Legenda enviada manualmente
# --------------------------------------------------------------------------- #


def test_srt_enviado_na_mao_e_usado(midia_teste, tmp_path):
    """Sem extração, a legenda pode vir de um .srt do disco do usuário."""
    destino = tmp_path / "manual.mp4"

    at = _abrir()
    _trocar_de_tela(at, INSERCAO)

    at.file_uploader[0].set_value(
        ("minha.srt", SRT_FALSO.encode("utf-8"), "text/plain")
    )
    at.run()
    assert not at.exception

    _radio(at, "Vídeo onde a legenda entra").set_value("Caminho no disco")
    at.run()
    # text_input[0] é o caminho do vídeo; o "Salvar como" vem depois.
    next(
        t for t in at.text_input if "Vídeo" in t.label or t.label == "Selecione o vídeo"
    ).set_value(str(midia_teste))
    at.run()

    next(t for t in at.text_input if t.label == "Salvar como").set_value(str(destino))
    at.run()
    next(b for b in at.button if b.label == "Inserir legenda").click()
    at.run()

    assert not at.exception, at.exception
    assert destino.is_file()


def test_arquivo_que_nao_e_legenda_mostra_erro(midia_teste):
    at = _abrir()
    _trocar_de_tela(at, INSERCAO)

    at.file_uploader[0].set_value(
        ("qualquer.srt", b"isto nao e uma legenda", "text/plain")
    )
    at.run()

    assert not at.exception
    assert any("marcação de tempo" in e.value for e in at.error)


@pytest.mark.parametrize("nome", ["legenda.srt", "legenda.vtt"])
def test_aceita_srt_e_vtt(midia_teste, nome):
    at = _abrir()
    _trocar_de_tela(at, INSERCAO)

    conteudo = (
        "WEBVTT\n\n00:00:00.500 --> 00:00:01.800\nOlá\n"
        if nome.endswith(".vtt")
        else SRT_FALSO
    )
    at.file_uploader[0].set_value((nome, conteudo.encode("utf-8"), "text/plain"))
    at.run()

    assert not at.exception
    assert not any("marcação de tempo" in e.value for e in at.error)

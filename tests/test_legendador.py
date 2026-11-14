"""Testes do núcleo do Legendador (extração de áudio, fluxo e interface)."""

from __future__ import annotations

import io
import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import APP, RAIZ, SRT_FALSO
from streamlit.testing.v1 import AppTest

import legendador
from legendador import ErroLegendagem, extrair_audio, legendar

# --------------------------------------------------------------------------- #
# Extração de áudio
# --------------------------------------------------------------------------- #


def test_extrair_audio_normaliza_16k_mono(midia_teste, tmp_path):
    """O áudio entregue ao modelo deve ser 16 kHz e mono (taxa nativa do Whisper)."""
    destino = tmp_path / "audio.mp3"
    extrair_audio(midia_teste, destino)

    assert destino.exists()
    assert destino.stat().st_size > 0

    saida = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=sample_rate,channels",
            "-of",
            "csv=p=0",
            str(destino),
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    taxa, canais = (saida.split(",") + ["", ""])[:2]
    assert taxa == "16000"
    assert canais == "1"


def test_extrair_audio_ignora_a_trilha_de_video(midia_teste, tmp_path):
    """O arquivo extraído não pode conter vídeo (só serve para a transcrição)."""
    destino = tmp_path / "audio.mp3"
    extrair_audio(midia_teste, destino)

    saida = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "csv=p=0",
            str(destino),
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    assert "video" not in saida


# --------------------------------------------------------------------------- #
# Fluxo completo
# --------------------------------------------------------------------------- #


def test_legendar_retorna_resultado(midia_teste, transcricao_mockada):
    resultado = legendar(midia_teste, idioma="pt", modelo="small")

    assert resultado.srt == SRT_FALSO
    assert resultado.nome_base == "teste"
    assert resultado.nome_saida == "teste.srt"
    assert resultado.modelo == "small"
    assert resultado.idioma == "pt"
    assert resultado.duracao_segundos is not None
    assert resultado.duracao_segundos == pytest.approx(3.0, abs=1.0)
    assert len(transcricao_mockada) == 1


def test_legendar_preserva_nome_com_pontos(midia_teste, transcricao_mockada, tmp_path):
    """'Meu.Video.2024.mp4' não pode ser interpretado como formato 'Video'."""
    destino = tmp_path / "Meu.Video.2024.mp4"
    shutil.copyfile(midia_teste, destino)

    resultado = legendar(destino, idioma="pt")
    assert resultado.nome_saida == "Meu.Video.2024.srt"


def test_legendar_nao_escreve_no_diretorio_de_trabalho(
    midia_teste, transcricao_mockada, tmp_path, monkeypatch
):
    """Os artefatos devem ficar em uma pasta temporária, e não no projeto."""
    monkeypatch.chdir(tmp_path)

    legendar(midia_teste, idioma="pt")

    assert list(tmp_path.iterdir()) == []


def test_extensao_nao_suportada(midia_teste):
    arquivo = midia_teste.with_suffix(".pdf")
    shutil.copyfile(midia_teste, arquivo)

    with pytest.raises(ErroLegendagem, match="não suportado"):
        legendar(arquivo, idioma="pt")


def test_arquivo_vazio():
    class FalsoUpload:
        name = "vazio.mp3"

        def read(self, size=-1):
            return b""

        def seek(self, *args):
            return 0

    with pytest.raises(ErroLegendagem, match="vazio"):
        legendar(FalsoUpload(), idioma="pt")


def test_arquivo_inexistente(tmp_path):
    with pytest.raises(ErroLegendagem, match="não encontrado"):
        legendar(tmp_path / "nao_existe.mp4", idioma="pt")


def test_modelo_desconhecido(midia_teste):
    with pytest.raises(ErroLegendagem):
        legendar(midia_teste, idioma="pt", modelo="nao-existe")


# --------------------------------------------------------------------------- #
# Arquivos grandes
# --------------------------------------------------------------------------- #


def test_caminho_do_disco_nao_e_copiado(midia_teste, transcricao_mockada, monkeypatch):
    """Arquivo local é lido no lugar: copiar um vídeo grande seria desperdício."""
    recebidos: list[Path] = []
    original = legendador.extrair_audio

    def espiao(arquivo, destino):
        recebidos.append(Path(arquivo))
        return original(arquivo, destino)

    monkeypatch.setattr(legendador, "extrair_audio", espiao)
    legendar(midia_teste, idioma="pt")

    assert recebidos == [midia_teste]


def test_upload_e_gravado_em_pedacos(tmp_path):
    """O upload não pode ser carregado inteiro na memória uma segunda vez."""
    pedidos: list[int] = []

    class FalsoUpload:
        name = "teste.mp4"

        def __init__(self, dados: bytes) -> None:
            self._buffer = io.BytesIO(dados)

        def seek(self, posicao: int, *args) -> int:
            return self._buffer.seek(posicao, *args)

        def read(self, size: int = -1) -> bytes:
            pedidos.append(size)
            return self._buffer.read(size)

    destino = legendador.entrada_local(FalsoUpload(b"x" * 5000), tmp_path, ".mp4")

    assert destino == tmp_path / "entrada.mp4"
    assert destino.stat().st_size == 5000
    assert pedidos, "o upload deveria ser lido em pedaços"
    assert all(pedaco > 0 for pedaco in pedidos)


def test_limite_de_upload_do_streamlit_aceita_video_grande():
    """O padrão do Streamlit (200 MB) recusa vídeos comuns."""
    import tomllib

    config = tomllib.loads(
        (RAIZ / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    )
    assert config["server"]["maxUploadSize"] >= 2048


# --------------------------------------------------------------------------- #
# Modelo local
# --------------------------------------------------------------------------- #


def test_dispositivo_padrao_e_valido():
    assert legendador.dispositivo_padrao() in ("cpu", "cuda")


def test_compute_type_por_dispositivo():
    assert legendador._compute_type("cpu") == "int8"
    assert legendador._compute_type("cuda") == "float16"


def test_modelo_fica_em_cache():
    """Recarregar o modelo a cada chamada custaria ~15 s."""
    legendador._modelos.clear()
    try:
        primeiro = legendador._obter_modelo("tiny", "cpu", "int8")
        segundo = legendador._obter_modelo("tiny", "cpu", "int8")
        assert primeiro is segundo
    finally:
        legendador._modelos.clear()


# --------------------------------------------------------------------------- #
# Interface (Streamlit AppTest)
# --------------------------------------------------------------------------- #


def test_ui_gerar_legenda_e_reaproveitar_resultado(midia_teste, transcricao_mockada):
    """Clicar em 'Gerar legenda' transcreve uma vez; reruns não refazem o trabalho."""
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    assert not at.exception
    assert at.info  # "Envie um arquivo para começar."

    at.file_uploader[0].set_value(("teste.mp4", midia_teste.read_bytes(), "video/mp4"))
    at.run()
    assert not at.exception

    botao = next(b for b in at.button if b.label == "Gerar legenda")
    botao.click()
    at.run()

    assert not at.exception
    assert len(transcricao_mockada) == 1, (
        "a transcrição deveria ter sido chamada uma única vez"
    )

    # Resultado visível na tela
    assert any("legendado com sucesso" in s.value for s in at.success)
    assert at.code and SRT_FALSO.strip() in at.code[0].value
    assert len(at.metric) == 4

    # Um rerun qualquer (trocar de opção, redimensionar a janela) não pode
    # disparar uma nova transcrição.
    at.run()
    assert len(transcricao_mockada) == 1, "rerun não deveria transcrever novamente"

    # Clicar de novo com o mesmo arquivo e as mesmas opções reaproveita o cache
    next(b for b in at.button if b.label == "Gerar legenda").click()
    at.run()
    assert len(transcricao_mockada) == 1, (
        "o resultado cacheado deveria ser reaproveitado"
    )


def test_ui_trocar_de_arquivo_invalida_resultado_anterior(
    midia_teste, transcricao_mockada
):
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()

    at.file_uploader[0].set_value(("teste.mp4", midia_teste.read_bytes(), "video/mp4"))
    at.run()
    next(b for b in at.button if b.label == "Gerar legenda").click()
    at.run()
    assert len(transcricao_mockada) == 1

    # Outro arquivo -> a legenda anterior não deve mais ser exibida
    at.file_uploader[0].set_value(("outro.mp4", midia_teste.read_bytes(), "video/mp4"))
    at.run()

    assert not any("legendado com sucesso" in s.value for s in at.success)


def test_ui_nao_exige_nenhuma_chave_de_api(
    midia_teste, transcricao_mockada, monkeypatch
):
    """O app funciona sem OPENAI_API_KEY — a transcrição é local."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    at.file_uploader[0].set_value(("teste.mp4", midia_teste.read_bytes(), "video/mp4"))
    at.run()
    next(b for b in at.button if b.label == "Gerar legenda").click()
    at.run()

    assert not at.exception
    assert len(transcricao_mockada) == 1


def test_ui_legenda_por_caminho_no_disco(midia_teste, transcricao_mockada):
    """O modo 'Caminho no disco' legenda sem upload e sem limite de tamanho."""
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    assert not at.exception

    next(r for r in at.radio if r.label == "Origem do arquivo").set_value(
        "Caminho no disco"
    )
    at.run()
    assert not at.file_uploader, "o upload não deve aparecer neste modo"

    at.text_input[0].set_value(str(midia_teste))
    at.run()
    assert not at.exception

    next(b for b in at.button if b.label == "Gerar legenda").click()
    at.run()

    assert not at.exception
    assert len(transcricao_mockada) == 1
    assert any("legendado com sucesso" in s.value for s in at.success)


def test_ui_caminho_inexistente_mostra_erro():
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()

    next(r for r in at.radio if r.label == "Origem do arquivo").set_value(
        "Caminho no disco"
    )
    at.run()
    at.text_input[0].set_value(r"C:\pasta\que\nao\existe\video.mp4")
    at.run()

    assert not at.exception
    assert any("não encontrado" in e.value for e in at.error)


def test_ui_vad_ligado_por_padrao(midia_teste, transcricao_mockada):
    """O filtro de silêncio vem ligado: é o comportamento certo para fala."""
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()
    assert next(c for c in at.checkbox if c.label == "Ignorar trechos sem fala").value

    at.file_uploader[0].set_value(("teste.mp4", midia_teste.read_bytes(), "video/mp4"))
    at.run()
    next(b for b in at.button if b.label == "Gerar legenda").click()
    at.run()

    assert not at.exception
    assert transcricao_mockada[0]["vad"] is True


def test_ui_desligar_vad_repassa_para_a_transcricao(midia_teste, transcricao_mockada):
    """Música cantada precisa rodar sem o filtro: o canto é descartado por ele."""
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()

    at.file_uploader[0].set_value(("teste.mp4", midia_teste.read_bytes(), "video/mp4"))
    at.run()
    next(c for c in at.checkbox if c.label == "Ignorar trechos sem fala").uncheck()
    at.run()
    next(b for b in at.button if b.label == "Gerar legenda").click()
    at.run()

    assert not at.exception
    assert transcricao_mockada[0]["vad"] is False


def test_ui_trocar_o_vad_invalida_o_resultado(midia_teste, transcricao_mockada):
    """O VAD muda o resultado: reaproveitar o anterior seria mentira."""
    at = AppTest.from_file(str(APP), default_timeout=60)
    at.run()

    at.file_uploader[0].set_value(("teste.mp4", midia_teste.read_bytes(), "video/mp4"))
    at.run()
    next(b for b in at.button if b.label == "Gerar legenda").click()
    at.run()
    assert len(transcricao_mockada) == 1

    next(c for c in at.checkbox if c.label == "Ignorar trechos sem fala").uncheck()
    at.run()
    next(b for b in at.button if b.label == "Gerar legenda").click()
    at.run()

    assert len(transcricao_mockada) == 2, "deveria transcrever de novo sem o filtro"

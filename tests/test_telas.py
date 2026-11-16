"""Testes das duas telas e da passagem da legenda de uma para a outra."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from conftest import APP, SRT_FALSO
from streamlit.testing.v1 import AppTest

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


def _campo(at: AppTest, rotulo: str):
    return next(t for t in at.text_input if t.label == rotulo)


def _definir_saida(at: AppTest, pasta: Path, nome: str) -> None:
    """Escolhe a pasta e o nome do vídeo legendado (tela 2)."""
    _campo(at, "Pasta de destino").set_value(str(pasta))
    at.run()
    _campo(at, "Nome do arquivo").set_value(nome)
    at.run()


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
    next(t for t in at.text_input if t.label == "Selecione o vídeo").set_value(
        str(outro)
    )
    at.run()

    assert not at.exception
    assert any("extraída de outro vídeo" in w.value for w in at.warning)


def test_insercao_nao_avisa_se_for_o_mesmo_video_por_outro_caminho(
    midia_teste, transcricao_mockada
):
    """Escolher o mesmo arquivo em 'Caminho no disco' não é usar outro vídeo."""
    at = _abrir()
    _legendar_upload(at, midia_teste)
    _trocar_de_tela(at, INSERCAO)

    _radio(at, "Vídeo onde a legenda entra").set_value("Caminho no disco")
    at.run()
    next(t for t in at.text_input if t.label == "Selecione o vídeo").set_value(
        str(midia_teste)
    )
    at.run()

    assert not at.exception
    assert not any("extraída de outro vídeo" in w.value for w in at.warning)


# --------------------------------------------------------------------------- #
# Inserção de verdade (ffmpeg)
# --------------------------------------------------------------------------- #


def test_insercao_queimada_pelo_app(
    midia_teste, transcricao_mockada, tmp_path, monkeypatch
):
    """Fluxo completo: extrair numa tela e queimar na outra."""
    import tela_inserir

    # O app prova a sincronia tirando um quadro do vídeo final. Aqui a gente
    # espiona o pedido para saber de onde e de que instante o quadro saiu.
    pedidos: list[tuple[Path, float]] = []
    original = tela_inserir.extrair_quadro

    def espiao(video, segundos, destino_quadro, largura=720):
        pedidos.append((Path(video), segundos))
        return original(video, segundos, destino_quadro, largura=largura)

    monkeypatch.setattr(tela_inserir, "extrair_quadro", espiao)

    destino = tmp_path / "final.mp4"

    at = _abrir()
    _legendar_upload(at, midia_teste)
    _trocar_de_tela(at, INSERCAO)

    _radio(at, "Modo").set_value("queimar")
    # O destino padrão de um upload iria para a pasta do usuário: aqui é o tmp.
    _definir_saida(at, tmp_path, destino.name)

    next(b for b in at.button if b.label == "Inserir legenda").click()
    at.run()

    assert not at.exception, at.exception
    assert destino.is_file(), "o ffmpeg deveria ter gerado o vídeo legendado"
    assert not _tem_faixa(destino, "subtitle"), "queimada não deixa faixa no arquivo"
    assert _tem_faixa(destino, "video")

    assert any("Legenda aplicada em" in s.value for s in at.success)
    assert any(m.label == "Modo" and m.value == "Queimada" for m in at.metric)

    # O quadro de conferência vem do arquivo final, num instante que está
    # dentro do bloco de legenda — é isso que mostra a sincronia na tela.
    assert pedidos, "a tela deveria extrair um quadro do vídeo final"
    video_do_quadro, instante = pedidos[0]
    assert video_do_quadro == destino
    assert 0.5 <= instante <= 1.8, (
        f"o quadro deveria sair de dentro do bloco (0,5–1,8 s), veio de {instante:.2f}s"
    )


def test_insercao_embutida_pelo_app(midia_teste, transcricao_mockada, tmp_path):
    """No modo faixa, o vídeo não é reencodado e a legenda fica selecionável."""
    destino = tmp_path / "final_faixa.mp4"

    at = _abrir()
    _legendar_upload(at, midia_teste)
    _trocar_de_tela(at, INSERCAO)

    # Trocar o modo troca o campo de destino (cada modo tem seu nome padrão),
    # então o rerun vem antes de preencher o caminho.
    _radio(at, "Modo").set_value("embutir")
    at.run()
    assert not at.exception

    _definir_saida(at, tmp_path, destino.name)

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

    _definir_saida(at, tmp_path, "saida.txt")

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

    _definir_saida(at, tmp_path, destino.name)
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
    # O caminho do vídeo vem antes dos campos de saída.
    next(t for t in at.text_input if t.label == "Selecione o vídeo").set_value(
        str(midia_teste)
    )
    at.run()

    _definir_saida(at, tmp_path, destino.name)
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


# --------------------------------------------------------------------------- #
# Onde salvar: pasta e nome escolhidos pelo usuário
# --------------------------------------------------------------------------- #


def test_pasta_padrao_segue_o_arquivo_escolhido(midia_teste):
    """O padrão é a pasta do próprio arquivo — não um caminho fixo."""
    from ui import pasta_padrao

    assert pasta_padrao(midia_teste) == midia_teste.parent


def test_pasta_padrao_sem_arquivo_usa_uma_pasta_do_usuario():
    """Sem caminho local (upload), a sugestão vem do sistema, não do código."""
    from ui import pasta_padrao

    pasta = pasta_padrao()
    assert pasta.is_dir()
    assert pasta == Path.home() or Path.home() in pasta.parents


def test_tela_2_nome_padrao_depende_do_modo(midia_teste, transcricao_mockada):
    at = _abrir()
    _legendar_upload(at, midia_teste)
    _trocar_de_tela(at, INSERCAO)

    assert _campo(at, "Nome do arquivo").value == "teste_legendado.mp4"

    _radio(at, "Modo").set_value("embutir")
    at.run()
    assert _campo(at, "Nome do arquivo").value == "teste_comlegenda.mp4"


def test_tela_2_salva_o_video_na_pasta_escolhida(
    midia_teste, transcricao_mockada, tmp_path
):
    """A pasta escolhida na tela é a pasta onde o arquivo aparece."""
    pasta = tmp_path / "meus videos"

    at = _abrir()
    _legendar_upload(at, midia_teste)
    _trocar_de_tela(at, INSERCAO)

    _definir_saida(at, pasta, "resultado.mp4")
    assert not pasta.exists(), "digitar o caminho não deveria criar pasta nenhuma"

    next(b for b in at.button if b.label == "Inserir legenda").click()
    at.run()

    assert not at.exception, at.exception
    assert (pasta / "resultado.mp4").is_file()


def test_tela_1_salva_a_legenda_na_pasta_escolhida(
    midia_teste, transcricao_mockada, tmp_path
):
    """Além do download, a legenda pode ser gravada numa pasta escolhida."""
    pasta = tmp_path / "legendas"

    at = _abrir()
    _legendar_upload(at, midia_teste)

    _campo(at, "Pasta de destino").set_value(str(pasta))
    at.run()
    _campo(at, "Nome do arquivo").set_value("legenda.srt")
    at.run()

    next(b for b in at.button if b.label == "Salvar legenda").click()
    at.run()

    alvo = pasta / "legenda.srt"
    assert not at.exception, at.exception
    assert alvo.is_file()
    assert "00:00:00,500 --> 00:00:01,800" in alvo.read_text(encoding="utf-8")

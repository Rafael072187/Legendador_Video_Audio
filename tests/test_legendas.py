"""Testes da montagem de legendas (formatação SRT/VTT e agrupamento)."""

from __future__ import annotations

from legendas import (
    Legenda,
    Palavra,
    agrupar_palavras,
    formatar_timestamp,
    legendas_de_segmentos,
    montar_legendas,
    para_srt,
    para_vtt,
    quebrar_linhas,
)

# --------------------------------------------------------------------------- #
# Timestamps
# --------------------------------------------------------------------------- #


def test_formatar_timestamp():
    assert formatar_timestamp(0) == "00:00:00,000"
    assert formatar_timestamp(7.4) == "00:00:07,400"
    assert formatar_timestamp(61.5) == "00:01:01,500"
    assert formatar_timestamp(3661.25) == "01:01:01,250"
    assert formatar_timestamp(-1) == "00:00:00,000"


def test_formatar_timestamp_arredonda():
    assert formatar_timestamp(1.0004) == "00:00:01,000"
    assert formatar_timestamp(1.9996) == "00:00:02,000"


# --------------------------------------------------------------------------- #
# Quebra de linhas
# --------------------------------------------------------------------------- #


def test_quebrar_linhas_respeita_o_limite():
    texto = "palavra " * 20
    linhas = quebrar_linhas(texto, 42)
    assert all(len(linha) <= 42 for linha in linhas)
    assert " ".join(linhas) == " ".join(texto.split())


def test_quebrar_linhas_texto_curto_fica_em_uma_linha():
    assert quebrar_linhas("Olá mundo", 42) == ["Olá mundo"]


def test_quebrar_linhas_palavra_sozinha_nao_e_quebrada():
    linhas = quebrar_linhas("palavragemuitocomprida", 10)
    assert linhas == ["palavragemuitocomprida"]


# --------------------------------------------------------------------------- #
# Agrupamento
# --------------------------------------------------------------------------- #


def _palavras(*pares: tuple[str, float, float]) -> list[Palavra]:
    return [
        Palavra(texto=texto, inicio=inicio, fim=fim) for texto, inicio, fim in pares
    ]


def test_agrupar_palavras_respeita_o_padrao_de_42_caracteres():
    palavras = _palavras(
        ("Uma", 0.0, 0.4),
        ("frase", 0.4, 0.9),
        ("com", 0.9, 1.1),
        ("muitas", 1.1, 1.6),
        ("palavras", 1.6, 2.2),
        ("para", 2.2, 2.5),
        ("caber", 2.5, 2.9),
        ("em", 2.9, 3.0),
        ("varias", 3.0, 3.5),
        ("linhas", 3.5, 3.9),
        ("e", 3.9, 4.0),
        ("mais", 4.0, 4.4),
        ("texto", 4.4, 4.9),
        ("que", 4.9, 5.1),
        ("precisa", 5.1, 5.6),
        ("ser", 5.6, 5.9),
        ("dividido", 5.9, 6.4),
        ("em", 6.4, 6.5),
        ("varios", 6.5, 7.0),
        ("blocos", 7.0, 7.5),
    )
    legendas = montar_legendas(palavras)

    assert len(legendas) > 1, "o texto deveria ter sido dividido em vários blocos"
    for legenda in legendas:
        assert len(legenda.linhas) <= 2
        assert all(len(linha) <= 42 for linha in legenda.linhas)

    # Nenhuma palavra pode ser perdida na divisão
    strung = " ".join(linha for legenda in legendas for linha in legenda.linhas)
    assert strung.split() == [p.texto for p in palavras]


def test_agrupar_palavras_quebra_em_pausas():
    palavras = _palavras(
        ("Primeira", 0.0, 0.5),
        ("frase", 0.5, 1.0),
        ("Segunda", 5.0, 5.5),
        ("frase", 5.5, 6.0),
    )
    blocos = agrupar_palavras(palavras, limiar_pausa=0.6)

    assert len(blocos) == 2
    assert [p.texto for p in blocos[0]] == ["Primeira", "frase"]
    assert [p.texto for p in blocos[1]] == ["Segunda", "frase"]


def test_agrupar_palavras_respeita_duracao_maxima():
    palavras = _palavras(
        ("uma", 0.0, 1.0),
        ("duas", 1.0, 2.0),
        ("tres", 2.0, 3.0),
        ("quatro", 3.0, 4.0),
        ("cinco", 4.0, 5.0),
    )
    blocos = agrupar_palavras(palavras, max_duracao=2.5, limiar_pausa=99)

    assert len(blocos) >= 2
    for bloco in blocos:
        assert bloco[-1].fim - bloco[0].inicio <= 2.5


def test_agrupar_palavras_sem_palavras():
    assert agrupar_palavras([]) == []


def test_corte_prefere_o_fim_de_uma_oracao():
    """O bloco deve ser fechado depois de uma vírgula, não no meio da frase."""
    palavras = _palavras(
        ("Deixa", 0.0, 0.3),
        ("eu", 0.3, 0.5),
        ("te", 0.5, 0.6),
        ("falar", 0.6, 1.0),
        ("uma", 1.0, 1.2),
        ("coisa", 1.2, 1.6),
        ("que", 1.6, 1.7),
        ("eu", 1.7, 1.9),
        ("até", 1.9, 2.1),
        ("esqueci", 2.1, 2.6),
        ("de", 2.6, 2.7),
        ("te", 2.7, 2.8),
        ("falar,", 2.8, 3.2),
        ("e", 3.2, 3.3),
        ("isso", 3.3, 3.6),
        ("aqui", 3.6, 4.0),
        ("foi", 4.0, 4.2),
        ("bom", 4.2, 4.6),
        ("mesmo", 4.6, 5.0),
        ("obrigado.", 5.0, 5.5),
    )
    legendas = montar_legendas(palavras)

    assert len(legendas) > 1
    # Nenhum bloco deve terminar numa palavra que não encerra uma oração,
    # a menos que não haja pontuação disponível antes.
    textos = [" ".join(legenda.linhas) for legenda in legendas]
    assert any(texto.endswith(",") or texto.endswith(".") for texto in textos)


def test_corte_prefere_antes_de_conjuncao():
    palavras = _palavras(
        ("um", 0.0, 0.2),
        ("dois", 0.2, 0.5),
        ("tres", 0.5, 0.8),
        ("quatro", 0.8, 1.2),
        ("cinco", 1.2, 1.6),
        ("seis", 1.6, 2.0),
        ("sete", 2.0, 2.4),
        ("oito", 2.4, 2.8),
        ("nove", 2.8, 3.2),
        ("dez", 3.2, 3.6),
        ("e", 3.6, 3.7),
        ("onze", 3.7, 4.1),
        ("doze", 4.1, 4.5),
        ("treze", 4.5, 4.9),
    )
    legendas = montar_legendas(palavras)

    # "e" inicia uma ideia nova: o corte deve ficar antes dela, se couber.
    textos = [" ".join(legenda.linhas) for legenda in legendas]
    assert any(not texto.startswith("e") for texto in textos)


def test_agrupar_palavras_nao_perde_palavras():
    palavras = _palavras(*[(f"palavra{i}", i * 0.3, i * 0.3 + 0.25) for i in range(60)])
    legendas = montar_legendas(palavras)

    juntado = " ".join(linha for legenda in legendas for linha in legenda.linhas)
    assert juntado.split() == [p.texto for p in palavras]


# --------------------------------------------------------------------------- #
# Montagem e saída
# --------------------------------------------------------------------------- #


def test_montar_legendas_marca_inicio_e_fim():
    palavras = _palavras(("Oi", 1.0, 1.5), ("tchau", 1.5, 2.0))
    legendas = montar_legendas(palavras)

    assert len(legendas) == 1
    assert legendas[0].inicio == 1.0
    assert legendas[0].fim == 2.0
    assert legendas[0].linhas == ("Oi tchau",)
    assert legendas[0].texto == "Oi tchau"


def test_para_srt_formato_correto():
    legendas = [
        Legenda(0.0, 2.5, ("Primeira linha",)),
        Legenda(2.5, 4.0, ("Segunda", "linha")),
    ]
    srt = para_srt(legendas)

    assert srt.startswith("1\n00:00:00,000 --> 00:00:02,500\nPrimeira linha\n")
    assert "2\n00:00:02,500 --> 00:00:04,000\nSegunda\nlinha" in srt
    assert srt.count("-->") == 2


def test_para_srt_numera_os_blocos_em_sequencia():
    legendas = [Legenda(i * 1.0, (i + 1) * 1.0, (f"bloco {i}",)) for i in range(5)]
    srt = para_srt(legendas)

    for indice in range(1, 6):
        assert f"\n{indice}\n" in srt or srt.startswith(f"{indice}\n")


def test_para_vtt_formato_correto():
    legendas = [Legenda(0.0, 2.5, ("Primeira linha",))]
    vtt = para_vtt(legendas)

    assert vtt.startswith("WEBVTT")
    assert "00:00:00.000 --> 00:00:02.500" in vtt
    assert "," not in vtt.split("-->")[1].split("\n")[0]


def test_legendas_de_segmentos_divide_blocos_longos():
    segmentos = [(0.0, 10.0, "palavra " * 30)]
    legendas = legendas_de_segmentos(segmentos)

    assert len(legendas) > 1
    for legenda in legendas:
        assert len(legenda.linhas) <= 2
        assert all(len(linha) <= 42 for linha in legenda.linhas)
    # O tempo é distribuído de forma contígua e cobre o segmento inteiro.
    assert legendas[0].inicio == 0.0
    assert abs(legendas[-1].fim - 10.0) < 0.001


def test_legendas_de_segmentos_ignora_vazios():
    assert legendas_de_segmentos([(0.0, 1.0, "   ")]) == []

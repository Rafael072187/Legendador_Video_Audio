"""
Construção de legendas no formato SRT.

A transcrição local entrega marcação de tempo por palavra, o que permite
reformatar os blocos de legenda seguindo o padrão usado porplayers e
legendas profissional: no máximo 42 caracteres por linha e 2 linhas por bloco.
"""

from __future__ import annotations

from dataclasses import dataclass

MAX_CARACTERES = 42
MAX_LINHAS = 2
MAX_DURACAO_SEGUNDOS = 7.0
LIMIAR_PAUSA_SEGUNDOS = 0.6

# Pontuação que indica fim de oração: bons lugares para cortar a legenda.
PONTUACOES_DE_FIM = ",.;:!?…—"
# Conjunções que costumam iniciar uma nova ideia: bons lugares para cortar.
CONJUNCOES = {
    "e",
    "mas",
    "ou",
    "que",
    "porque",
    "porém",
    "portanto",
    "então",
    "aí",
    "já",
    "como",
    "quando",
    "se",
    "nem",
}
# Quantas palavras para trás o algoritmo pode procurar um corte melhor.
JANELA_DE_BUSCA = 8


@dataclass(frozen=True)
class Palavra:
    """Uma palavra com marcação de tempo."""

    texto: str
    inicio: float
    fim: float


@dataclass(frozen=True)
class Legenda:
    """Um bloco de legenda pronto para o formato SRT."""

    inicio: float
    fim: float
    linhas: tuple[str, ...]

    @property
    def texto(self) -> str:
        return "\n".join(self.linhas)


# --------------------------------------------------------------------------- #
# Formatação
# --------------------------------------------------------------------------- #


def formatar_timestamp(segundos: float) -> str:
    """Converte segundos em 'HH:MM:SS,mmm', o formato de tempo do SRT."""
    milissegundos = max(0, int(round(segundos * 1000)))
    horas, resto = divmod(milissegundos, 3_600_000)
    minutos, resto = divmod(resto, 60_000)
    segundos_restantes, milissegundos = divmod(resto, 1000)
    return f"{horas:02d}:{minutos:02d}:{segundos_restantes:02d},{milissegundos:03d}"


def quebrar_linhas(texto: str, max_caracteres: int = MAX_CARACTERES) -> list[str]:
    """Quebra o texto em linhas de no máximo `max_caracteres` caracteres."""
    linhas: list[str] = []
    atual = ""

    for palavra in texto.split():
        candidata = f"{atual} {palavra}".strip()
        if not atual or len(candidata) <= max_caracteres:
            atual = candidata
        else:
            linhas.append(atual)
            atual = palavra

    if atual:
        linhas.append(atual)
    return linhas


def _texto_do_bloco(bloco: list[Palavra]) -> str:
    return " ".join(palavra.texto for palavra in bloco)


def _melhor_corte(
    bloco: list[Palavra],
    *,
    max_caracteres: int = MAX_CARACTERES,
    max_linhas: int = MAX_LINHAS,
) -> int:
    """Escolhe onde cortar um bloco que estourou o limite de tamanho.

    Em vez de partir a frase no meio, procura (a) o fim de uma oração e
    (b) uma conjunção que inicie uma ideia nova. Devolve quantas palavras
    ficam no bloco fechado (nunca zero, para garantir progresso).
    """
    inicio = max(0, len(bloco) - JANELA_DE_BUSCA)

    # (a) Depois de uma pontuação de fim de oração.
    for indice in range(len(bloco) - 1, inicio - 1, -1):
        texto = bloco[indice].texto
        if texto and texto[-1] in PONTUACOES_DE_FIM:
            corte = indice + 1
            if (
                len(quebrar_linhas(_texto_do_bloco(bloco[:corte]), max_caracteres))
                <= max_linhas
            ):
                return corte

    # (b) Antes de uma conjunção que começa outra ideia.
    for indice in range(len(bloco) - 1, inicio, -1):
        if bloco[indice].texto.lower() in CONJUNCOES:
            corte = indice
            if (
                corte >= 1
                and len(quebrar_linhas(_texto_do_bloco(bloco[:corte]), max_caracteres))
                <= max_linhas
            ):
                return corte

    return len(bloco)


# --------------------------------------------------------------------------- #
# Agrupamento
# --------------------------------------------------------------------------- #


def agrupar_palavras(
    palavras: list[Palavra],
    *,
    max_caracteres: int = MAX_CARACTERES,
    max_linhas: int = MAX_LINHAS,
    max_duracao: float = MAX_DURACAO_SEGUNDOS,
    limiar_pausa: float = LIMIAR_PAUSA_SEGUNDOS,
) -> list[list[Palavra]]:
    """Agrupa palavras em blocos de legenda.

    Um bloco é fechado quando chega uma pausa na fala, quando a duração máxima
    é atingida, ou quando o texto não cabe em `max_linhas` linhas.
    """
    blocos: list[list[Palavra]] = []
    atual: list[Palavra] = []

    for palavra in palavras:
        # Fecha blocos anteriores até que a palavra caiba no bloco atual.
        while atual:
            pausa = palavra.inicio - atual[-1].fim
            duracao = palavra.fim - atual[0].inicio
            cabe_linhas = (
                len(quebrar_linhas(_texto_do_bloco(atual + [palavra]), max_caracteres))
                <= max_linhas
            )

            if pausa <= limiar_pausa and duracao <= max_duracao and cabe_linhas:
                break

            if cabe_linhas:
                # A quebra veio de uma pausa ou da duração: o próprio fim do
                # bloco é o corte natural.
                corte = len(atual)
            else:
                # O texto estourou o limite: procura um corte mais legível.
                corte = _melhor_corte(
                    atual, max_caracteres=max_caracteres, max_linhas=max_linhas
                )

            blocos.append(atual[:corte])
            atual = atual[corte:]

        atual.append(palavra)

    if atual:
        blocos.append(atual)
    return blocos


def montar_legendas(
    palavras: list[Palavra],
    *,
    max_caracteres: int = MAX_CARACTERES,
    max_linhas: int = MAX_LINHAS,
    max_duracao: float = MAX_DURACAO_SEGUNDOS,
    limiar_pausa: float = LIMIAR_PAUSA_SEGUNDOS,
) -> list[Legenda]:
    """Transforma palavras com marcação de tempo em blocos de legenda."""
    legendas: list[Legenda] = []

    for bloco in agrupar_palavras(
        palavras,
        max_caracteres=max_caracteres,
        max_linhas=max_linhas,
        max_duracao=max_duracao,
        limiar_pausa=limiar_pausa,
    ):
        linhas = quebrar_linhas(_texto_do_bloco(bloco), max_caracteres)
        legendas.append(
            Legenda(inicio=bloco[0].inicio, fim=bloco[-1].fim, linhas=tuple(linhas))
        )

    return legendas


def legendas_de_segmentos(
    segmentos: list[tuple[float, float, str]],
    *,
    max_caracteres: int = MAX_CARACTERES,
    max_linhas: int = MAX_LINHAS,
) -> list[Legenda]:
    """Constrói legendas a partir de segmentos (usado quando não há marcação por palavra).

    Blocos longos demais são divididos em vários, com o tempo distribuído
    proporcionalmente ao tamanho de cada parte.
    """
    legendas: list[Legenda] = []

    for inicio, fim, texto in segmentos:
        texto = (texto or "").strip()
        if not texto:
            continue

        linhas = quebrar_linhas(texto, max_caracteres)
        grupos = [linhas[i : i + max_linhas] for i in range(0, len(linhas), max_linhas)]

        duracao = max(0.0, fim - inicio)
        pesos = [sum(len(linha) for linha in grupo) for grupo in grupos]
        total = sum(pesos) or 1

        cursor = inicio
        for grupo, peso in zip(grupos, pesos, strict=True):
            fim_grupo = cursor + duracao * peso / total
            legendas.append(Legenda(inicio=cursor, fim=fim_grupo, linhas=tuple(grupo)))
            cursor = fim_grupo

    return legendas


# --------------------------------------------------------------------------- #
# Saída
# --------------------------------------------------------------------------- #


def para_srt(legendas: list[Legenda]) -> str:
    """Serializa os blocos de legenda no formato SRT."""
    blocos = []

    for indice, legenda in enumerate(legendas, start=1):
        blocos.append(
            f"{indice}\n"
            f"{formatar_timestamp(legenda.inicio)} --> {formatar_timestamp(legenda.fim)}\n"
            f"{legenda.texto}\n"
        )

    return "\n".join(blocos)


def para_vtt(legendas: list[Legenda]) -> str:
    """Serializa os blocos de legenda no formato WebVTT."""
    blocos = ["WEBVTT", ""]

    for legenda in legendas:
        inicio = formatar_timestamp(legenda.inicio).replace(",", ".")
        fim = formatar_timestamp(legenda.fim).replace(",", ".")
        blocos.append(f"{inicio} --> {fim}")
        blocos.append(legenda.texto)
        blocos.append("")

    return "\n".join(blocos)

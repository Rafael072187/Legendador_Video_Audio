<center>
  <h1 style="font-size:2.4em; margin-bottom:0.1em;">🎬 Legendador de Vídeo e Áudio</h1>
  <p style="margin-top:0.2em; font-size:1.05em; color:#555;">
    Aplicação em <b>Python + Streamlit</b> que gera legendas com o <b>Whisper local</b>
    e coloca essa legenda de volta no vídeo — <b>queimada na imagem</b> ou como
    <b>faixa selecionável</b>, com os tempos do próprio arquivo.
  </p>
  <p style="margin-top:0.1em; font-size:0.95em; color:#777;">
    Repositório <b>Legendador_Video_Audio</b> · versão <b>2.0</b>
  </p>
  <p>
    <a href="https://github.com/Rafael072187/Legendador_Video_Audio" style="background:#24292F;color:#fff;padding:8px 14px;border-radius:8px;text-decoration:none;font-weight:600;">
      🔗 Repositório no GitHub
    </a>
  </p>
</center>

<hr>

## 🧭 Tabela de Conteúdos

- [Descrição](#-descrição)
- [Funcionalidades](#-funcionalidades)
- [Requisitos](#-requisitos)
- [Instalação](#-instalação)
- [Como usar](#-como-usar)
- [Sincronia](#-sincronia)
- [Linha de comando](#-linha-de-comando)
- [Modelos Whisper](#-modelos-whisper)
- [Arquivos grandes](#-arquivos-grandes)
- [Estrutura do projeto](#-estrutura-do-projeto)
- [Tecnologias](#-tecnologias)
- [Solução de problemas](#-solução-de-problemas)
- [Como contribuir](#-como-contribuir)
- [Autor](#-autor)
- [Observações](#-observações)

---

## 📘 Descrição

<details>
<summary><b>Resumo</b></summary>

O **Legendador de Vídeo e Áudio** transcreve vídeos e áudios **na sua própria
máquina** com o **Whisper** (via `faster-whisper`) e devolve a legenda pronta em
**SRT** ou **VTT**, no padrão profissional de leitura: no máximo **42 caracteres
por linha** e **2 linhas por bloco**.

A versão 2.0 acrescentou a segunda metade do trabalho: **colocar a legenda de
volta no vídeo**. A interface tem duas telas independentes, ligadas pela sessão:

| Tela | O que resolve |
| --- | --- |
| 🎬 **Extrair legenda** | Transcreve o arquivo e entrega o `.srt` / `.vtt` para download. |
| 🎞️ **Inserir legenda** | Aplica a legenda no vídeo — o mesmo de onde ela saiu, outro arquivo ou um novo upload. |

Nada disso usa API paga, chave de acesso ou envio de dados para fora. Depois do
primeiro download do modelo, o projeto funciona **sem internet**.

</details>

---

## ✨ Funcionalidades

<details open>
<summary><b>O que o programa faz</b></summary>

| Recurso | Descrição |
| --- | --- |
| 🔒 **100% local** | Transcrição com `faster-whisper` (CTranslate2). Nenhuma API, nenhuma chave, nenhum custo por minuto. |
| 🎬 **Duas telas** | Extrair a legenda e inseri-la no vídeo, com a legenda passando de uma tela para a outra. |
| 📝 **SRT e VTT** | Saída nos dois formatos, com o padrão de 42 caracteres por linha e 2 linhas por bloco. |
| ⏱️ **Tempos por palavra** | O Whisper marca cada palavra; os blocos são montados em fronteiras naturais de frase. |
| 🔥 **Queimar (hardsub)** | O texto vira pixel. Reencoda em H.264 + AAC e aparece em qualquer player, celular ou rede social. |
| 💬 **Embutir (softsub)** | Adiciona uma faixa selecionável **sem reencodar o vídeo** — leva menos de 2 segundos. |
| 🎯 **Sincronia por construção** | A legenda é aplicada na linha do tempo original do vídeo, sem deslocamento manual. |
| 🖼️ **Quadro de conferência** | Depois de queimar, a tela mostra um quadro do vídeo final tirado de dentro do primeiro bloco. |
| 📂 **Caminho no disco** | Lê o arquivo direto do computador: sem upload, sem limite de tamanho, sem cópia em memória. |
| 🗂️ **Pasta de destino** | Você escolhe onde salvar a legenda e o vídeo. O padrão vem do sistema (pasta do arquivo, `Downloads` ou a home). |
| ☁️ **Upload até 2 GB** | Limite elevado no `.streamlit/config.toml` para quem prefere arrastar o arquivo. |
| 🎼 **Áudio cantado** | O filtro de silêncio pode ser desligado (tela ou `--sem-vad`): em música, ele descarta o canto. |
| 🧠 **Modelos selecionáveis** | `tiny`, `base`, `small`, `medium` e `large-v3`, com detecção automática de GPU CUDA. |
| 🖥️ **Interface escura** | Tema próprio, cartões por etapa e navegação na barra lateral. |

</details>

<details>
<summary><b>O que mudou em relação à versão anterior</b></summary>

| Antes (v1) | Agora (v2.0) |
| --- | --- |
| Só gerava o `.srt` / `.vtt` | Gera **e aplica** a legenda no vídeo |
| Uma tela única | Duas telas: extrair e inserir |
| Transcrição com o filtro de silêncio fixo | Filtro **opcional**, com aviso para música cantada |
| Nenhuma verificação visual | Quadro do vídeo final provando a sincronia |
| Só upload de arquivo | Upload **ou** caminho no disco (sem limite) |
| Nenhum arquivo salvo (só download) | **Pasta e nome escolhidos** para a legenda e para o vídeo |
| `pydub` para o áudio | `ffmpeg` direto, em MP3 mono 16 kHz |
| Sem confirmação do resultado | Métricas de duração, blocos, modelo e velocidade |

</details>

---

## 📦 Requisitos

| Requisito | Versão / Observação |
| --- | --- |
| **Python** | 3.11 ou superior |
| **uv** | Gerencia o ambiente e os comandos (`uv sync`, `uv run`) |
| **ffmpeg** | No `PATH` — extrai o áudio e aplica a legenda |
| **libass** | Compilada na build do ffmpeg; necessária para **queimar** o texto |

> As builds do [Gyan](https://www.gyan.dev/ffmpeg/builds/) já vêm com `libass` e
> `libx264`. No Linux, o pacote `ffmpeg` da distribuição serve.

---

## ⚙️ Instalação

<details>
<summary><b>Passo a passo (Windows / Linux / macOS)</b></summary>

### 1. Clone o repositório

```bash
git clone https://github.com/Rafael072187/Legendador_Video_Audio.git
cd Legendador_Video_Audio
```

### 2. Instale as dependências

```bash
uv sync
```

### 3. Instale o ffmpeg

**Windows**

```powershell
winget install Gyan.FFmpeg
```

Ou baixe em <https://www.gyan.dev/ffmpeg/builds/> e adicione a pasta `bin` ao `PATH`.

**macOS**

```bash
brew install ffmpeg
```

**Linux (Debian/Ubuntu)**

```bash
sudo apt install ffmpeg
```

Confirme a instalação:

```bash
ffmpeg -version
```

Reinicie o terminal depois de instalar, para que o comando passe a ser reconhecido.

> Não é preciso criar `.env` nem configurar chave de API: **não existe dependência
> de serviço pago neste projeto**. Todos os comandos abaixo usam `uv run`, que
> executa dentro do ambiente do projeto sem precisar ativar o `.venv`.

</details>

---

## 🖥️ Como usar

<details open>
<summary><b>Usando a interface (duas telas)</b></summary>

### 1. Abra a aplicação

```bash
uv run streamlit run main.py
```

A interface fica em <http://localhost:8501>, com a navegação das duas telas na
barra lateral. `uv run main.py` e `python main.py` também funcionam: o `main.py`
detecta que foi executado fora do Streamlit e se reinicia pelo comando correto.

> Rode o comando a partir da raiz do projeto para que a `.streamlit/config.toml`
> (limite de upload e tema) seja lida.

### 2. Tela 🎬 Extrair legenda

1. Escolha a origem do arquivo: **Upload** ou **Caminho no disco**.
2. Ajuste na barra lateral o **idioma**, o **modelo Whisper**, o **formato de
   saída** e o **dispositivo** (automático por padrão).
3. Clique em **Gerar legenda**.
4. Ao terminar, a tela mostra duração, número de blocos, modelo usado e a
   velocidade em relação ao tempo real.
5. Baixe o `.srt` / `.vtt`, pré-visualize na própria tela ou use
   **💾 Salvar a legenda numa pasta** para gravá-la onde quiser.

| Opção da barra lateral | Para que serve |
| --- | --- |
| **Idioma do áudio** | Fixa o idioma ou deixa o Whisper detectar automaticamente. |
| **Modelo Whisper** | Troca precisão por velocidade (veja a tabela de modelos). |
| **Formato de saída** | `SRT (SubRip)` ou `VTT (WebVTT)`. |
| **Dispositivo** | `Automático`, `CPU` ou `GPU (CUDA)` quando há NVIDIA. |
| **Ignorar trechos sem fala** | Pula os silêncios (mais rápido). **Desmarque em música cantada.** |

### 3. Tela 🎞️ Inserir legenda

1. **Legenda** — use a extraída nesta sessão (reaproveitada automaticamente) ou
   envie um `.srt` / `.vtt` seu.
2. **Vídeo** — escolha **Vídeo da extração** (o mesmo arquivo de onde a legenda
   saiu), outro **Caminho no disco** ou um novo **Upload**.
3. **Como colocar** — escolha o modo, a **Pasta de destino** e o **Nome do
   arquivo**, e clique em **Inserir legenda**.

| Modo | O que faz | Quando usar |
| --- | --- | --- |
| 🔥 **Queimar no vídeo** | O texto vira pixel. Reencoda em H.264 + AAC. | Redes sociais, celular, qualquer player. |
| 💬 **Embutir como faixa** | Adiciona uma faixa selecionável. **Não reencoda.** | Arquivo de trabalho, player que liga/desliga legenda. |

### 4. Onde salvar

Os dois arquivos gerados — a legenda e o vídeo legendado — têm **pasta e nome
escolhidos na tela**:

| Campo | Padrão | Observação |
| --- | --- | --- |
| **Pasta de destino** | A pasta do arquivo escolhido; sem arquivo local, `Downloads`, `Vídeos` ou a pasta do usuário | Qualquer caminho serve; a pasta é criada se não existir |
| **Nome do arquivo** | `nome_legendado.mp4` (queimar) ou `nome_comlegenda.mp4` (faixa) | A extensão é validada (`.mp4`, `.mkv`, `.mov`) |

O padrão é sempre **derivado do sistema onde o app roda** — não existe pasta
fixa no código. O **vídeo original nunca é alterado**.

### 5. Resultado

- **Queimar** grava `_legendado` no nome e mostra um **quadro do vídeo final**
  para conferir a sincronia.
- **Embutir** grava `_comlegenda` e informa o idioma da faixa criada.

Arquivos abaixo de 50 MB também podem ser baixados pelo navegador; acima disso,
o app informa o caminho no disco (carregar gigabytes na memória só para o
download não valeria a pena).

</details>

---

## 🎯 Sincronia

<details open>
<summary><b>Por que a legenda cai no tempo certo</b></summary>

Não existe "sincronizar no olho". Quando a legenda vem da tela de extração, os
tempos são **os do próprio arquivo**: o mesmo vídeo, a mesma linha do tempo,
nenhum deslocamento. O alinhamento é consequência de os dois arquivos
descreverem o mesmo tempo.

O que a tela faz para você conferir:

1. Depois de queimar, extrai um **quadro do vídeo final** de dentro do primeiro
   bloco de legenda e mostra na tela.
2. Se a legenda veio de **outro vídeo**, avisa que os tempos podem não bater —
   e reconhece o mesmo arquivo escolhido por outro caminho (compara nome e
   tamanho), sem alarme falso.

No modo **faixa**, o vídeo é copiado byte a byte (`-c copy`) e só a legenda é
acrescentada: a sincronia é a do contêiner original, e o player liga e desliga o
texto quando quiser.

</details>

---

## 💻 Linha de comando

<details>
<summary><b>Extração sem abrir a interface</b></summary>

A CLI cobre a extração (a inserção no vídeo fica na interface):

```bash
# Legendar um vídeo ou áudio
uv run legendador Churrasco.mp4

# Escolher modelo, idioma e formato de saída
uv run legendador audio.mp3 --modelo medium --idioma en --formato vtt

# Música cantada: sem o filtro de silêncio
uv run legendador clipe.mp4 --sem-vad

# Baixar um modelo antecipadamente (deixa tudo pronto para uso offline)
uv run legendador --baixar-modelo small
uv run legendador --baixar-modelo todos
```

| Opção | Efeito |
| --- | --- |
| `--modelo` | `tiny`, `base`, `small`, `medium` ou `large-v3` |
| `--idioma` | Código do idioma (`pt`, `en`…) ou `auto` para detectar |
| `--formato` | `srt` ou `vtt` |
| `--dispositivo` | Força `cpu` ou `cuda`; por padrão detecta sozinho |
| `--saida` | Caminho do arquivo gerado |
| `--sem-vad` | Não ignora silêncios (música cantada, fala sobre música) |
| `--baixar-modelo` | Baixa um modelo (ou `todos`) e sai |

</details>

---

## 🧠 Modelos Whisper

<details>
<summary><b>Tamanho, velocidade e quando usar</b></summary>

O modelo é baixado do Hugging Face na primeira vez e fica em cache
(`~/.cache/huggingface`). Medições em CPU (AMD Ryzen 5 5600G, 6 núcleos, **sem
GPU**, `int8`):

| Modelo | Download | Velocidade | Quando usar |
| --- | --- | --- | --- |
| `tiny` | 75 MB | ~30x tempo real | Testes, áudio limpo e fácil |
| `base` | 145 MB | ~11x tempo real | Qualidade básica |
| `small` | 484 MB | ~4x a 6x tempo real | **Recomendado** — equilíbrio ideal |
| `medium` | 1,5 GB | ~1,2x tempo real | Qualidade alta, áudio difícil |
| `large-v3` | 3 GB | ~0,5x tempo real | Qualidade máxima, bem mais lento |

Com GPU NVIDIA (CUDA) o projeto detecta automaticamente e usa `float16`, o que
multiplica a velocidade. Em CPU ele usa `int8`.

> **Vídeo cantado:** em música, o filtro de silêncio do Whisper descarta o canto
> junto com a música. Desmarque **Ignorar trechos sem fala** (ou use `--sem-vad`).
> Num teste com lyric video, isso passou de **7 para 143 blocos** — a letra
> inteira. Em compensação fica mais lento e pode inventar texto em trechos
> realmente vazios.

</details>

---

## 📂 Arquivos grandes

<details>
<summary><b>Upload x caminho no disco</b></summary>

| Origem | Limite | Como funciona |
| --- | --- | --- |
| **Upload** | 2 GB | O arquivo passa pelo navegador e fica na memória do servidor. |
| **Caminho no disco** | **nenhum** | O ffmpeg lê o arquivo direto do disco; nada é enviado, nada é copiado. |

O limite de upload não é escolha do projeto: **200 MB** é o padrão do Streamlit.
Ele está elevado para 2 GB em [`.streamlit/config.toml`](.streamlit/config.toml).
Para arquivos maiores — ou simplesmente para não esperar o upload de um vídeo
que já está no computador — use **Caminho no disco**: é instantâneo e não duplica
o arquivo em memória nem em disco.

Só o áudio extraído (MP3 mono 16 kHz) é gravado, e ele é descartado no final.

</details>

---

## 🗂️ Estrutura do projeto

<details open>
<summary><b>Arquivos e responsabilidades</b></summary>

| Arquivo | Responsabilidade |
| --- | --- |
| `legendador.py` | Núcleo: extração de áudio, transcrição local e resultado. |
| `legendas.py` | Montagem das legendas: agrupamento por palavra, quebra de linhas e saída SRT/VTT. |
| `insercao.py` | Colocar a legenda no vídeo (queimar/embutir), progresso e inspeção do resultado. |
| `ui.py` | Peças de interface compartilhadas: campos de arquivo, cartões, formatação. |
| `tela_extrair.py` | Tela 1: transcrição e download da legenda. |
| `tela_inserir.py` | Tela 2: aplicação da legenda no vídeo e conferência de sincronia. |
| `main.py` | Roteador das telas e ponto de entrada do Streamlit. |
| `cli.py` | Linha de comando (console script `legendador`), só para extração. |
| `.streamlit/config.toml` | Limite de upload (2 GB), tema e telemetria desligada. |
| `tests/` | Testes do núcleo, das legendas, da inserção e das duas telas. |

O núcleo também pode ser usado como biblioteca:

```python
from insercao import MODO_EMBUTIR, MODO_QUEIMAR, inserir_legenda
from legendador import legendar

resultado = legendar("Churrasco.mp4", idioma="pt", modelo="small")
print(resultado.srt)          # conteúdo da legenda
print(resultado.nome_saida)   # "Churrasco.srt"
print(resultado.velocidade)   # quantas vezes mais rápido que o tempo real

video = inserir_legenda("Churrasco.mp4", resultado.srt, modo=MODO_QUEIMAR)
print(video.caminho)          # Churrasco_legendado.mp4
print(video.tempo)            # segundos gastos
```

### Exemplos de saída

Pasta escolhida na tela (o exemplo usa a pasta do próprio vídeo):

```
<qualquer pasta que você escolher>\
├── Churrasco.mp4                    # original, nunca é alterado
├── Churrasco_legendado.mp4          # modo queimar
├── Churrasco_comlegenda.mp4         # modo faixa
└── Churrasco.srt                    # legenda salva pela tela 1
```

### Testes

```bash
uv run pytest
```

</details>

---

## 🛠️ Tecnologias

<details>
<summary><b>Stack principal</b></summary>

| Tecnologia | Uso no projeto |
| --- | --- |
| **Python** | Linguagem principal |
| **Streamlit** | Interface web, navegação entre telas e tema escuro |
| **faster-whisper / CTranslate2** | Transcrição local com timestamps por palavra |
| **FFmpeg** | Extração do áudio, queima (`libass`) e faixa (`mov_text`) |
| **H.264 + AAC** | Saída do modo queimar, compatível com qualquer player |
| **pytest + AppTest** | Testes do núcleo e das telas |
| **uv / hatchling** | Ambiente, comandos e empacotamento |

</details>

---

## 🧯 Solução de problemas

<details>
<summary><b>Erros comuns</b></summary>

**"O ffmpeg não foi encontrado no PATH"**
Instale o ffmpeg (`winget install Gyan.FFmpeg`) e reabra o terminal. Confirme
com `ffmpeg -version`.

**A queima falha com erro de filtro `subtitles`**
A build do ffmpeg não tem `libass`. Use uma build com `libass` (as do Gyan têm)
ou escolha o modo **Embutir como faixa**, que não precisa do filtro.

**A legenda saiu com poucos blocos num vídeo cantado**
O filtro de silêncio descartou o canto. Desmarque **Ignorar trechos sem fala**
na barra lateral ou use `--sem-vad` na linha de comando.

**A legenda ficou duplicada na imagem**
O vídeo já tinha legenda queimada de fábrica (comum em lyric videos e clipes
legendados). Queimar por cima acrescenta a segunda linha. Nesse caso, use
**Embutir como faixa** ou trabalhe a partir de um arquivo sem legenda embutida.

**O download do vídeo final não aparece**
Acima de 50 MB o app mostra o caminho em vez do botão: carregar gigabytes na
memória do navegador não compensa. O arquivo já está salvo no caminho indicado.

**"Arquivo não encontrado" no caminho digitado**
Cole o caminho completo, com a extensão. Aspas de "Copiar como caminho" são
aceitas e removidas automaticamente.

**A transcrição está muito lenta**
Troque para um modelo menor (`tiny` ou `base`) ou verifique se há GPU CUDA
disponível na barra lateral.

</details>

---

## 🤝 Como contribuir

<details>
<summary><b>Guia rápido</b></summary>

1. Faça um fork do repositório.
2. Crie uma branch:

   ```bash
   git checkout -b feature/nova-funcionalidade
   ```

3. Implemente a melhoria. Algumas ideias que ainda faltam:
   - tradução da legenda para outro idioma;
   - editor de tempos e textos antes de aplicar no vídeo;
   - estilos de legenda (fonte, cor, posição) no modo queimar;
   - fila de processamento para vários arquivos;
   - empacotamento como executável para quem não usa Python.

4. Rode os testes e o lint antes de enviar:

   ```bash
   uv run pytest
   uvx ruff check .
   ```

5. Commit e push:

   ```bash
   git commit -m "feat: adiciona editor de tempos"
   git push origin feature/nova-funcionalidade
   ```

6. Abra um Pull Request detalhando a mudança.

</details>

---

## 👤 Autor

<details>
<summary><b>Contato</b></summary>

**Rafael Bittencourt de Araújo** — desenvolvedor do projeto.

- GitHub: [github.com/Rafael072187](https://github.com/Rafael072187)
- Repositório: [Legendador_Video_Audio](https://github.com/Rafael072187/Legendador_Video_Audio)

</details>

---

## 📝 Observações

- ✅ Projeto prático de transcrição e edição de vídeo com Python, Whisper local,
  Streamlit e FFmpeg.
- ✅ A legenda e o vídeo compartilham a mesma linha do tempo: a sincronia é
  consequência do processo, não de ajuste manual.
- ⚠️ **Aviso legal:** respeite os direitos autorais do conteúdo que você legenda.
  Utilize o programa apenas para material de domínio público, com licença aberta
  ou com autorização do autor.

<p align="center" style="margin-top:18px;">
  <a href="https://github.com/Rafael072187/Legendador_Video_Audio" style="background:#0b5fff;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:600;">
    Ver repositório
  </a>
</p>

<p align="center" style="margin-top:14px;color:#666;">
  README atualizado com base no comportamento real da versão <b>2.0</b> do aplicativo.
</p>

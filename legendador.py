from openai import OpenAI
from dotenv import load_dotenv
from pydub import AudioSegment

# Aqui estou transformado todo esse código em uma função
def legendar(arquivo_video):
    """ Ao chama o arquivo onde está localizado o vídeo e usado o (.name) pois o (.split) precisa de uma string(nome) nesse caso para funciona, 
    e o (.split) passando para ele o (".") ele ira me devolver uma lista com o nome do arquivo[] e seu formato[], 
    assim me retorna dois item, eu só tenho que pega o item de indice 1 quer será o formato """
    formato_arq = arquivo_video.name.split(".")[1]
    # O (AudioSegment) do pydub ira recebe essa duas informações: o arquivo e o formato, e retorna-lo na forma de audio
    audio = AudioSegment.from_file(file=arquivo_video, format= formato_arq)

    """ Agora irei pegar o audio extraido, usado .export para exportá-lo, nisso temos que passa dois parâmentros o nome do arquivo de audio
    e o formato dele """
    audio.export("audio.mp3", format="mp3")

    load_dotenv()

    cliente = OpenAI()

    """ 
    Aqui estou abrindo o arquivo em modo de leitura no formanto de bits(rb=Leitura Binária), já que para a transcrição tem que passar o áudio no formato de bit
    que são vários caracteres, no qual o modelo vai entender e transcreve o conteúdo do áudio.
    """
    with open("audio.mp3", "rb") as arquivo:
        transcricao = cliente.audio.transcriptions.create(
            model="whisper-1", # Modelo mais barato atualmente
            file=arquivo,
            language="pt", # Aqui ao passar o idioma usado, assim ele não tera quer idetificar o idioma, facilitando o trabalho
            response_format="srt" # O formato srt(SubRip Subtitle) é o formanto padrão de criação de legendas e mais comum de ser usado
            )

    # Aqui estou criando o arquivo da legenda, abrindo e escrevendo(w) o texto, usando o encoding(utf-8) por conta dos caracteres especiais do idioma pt.
    with open("legenda.srt", "w", encoding="utf-8") as arquivo_legenda:
        arquivo_legenda.write(transcricao)

    # E por fim ele vai me devolver essa transcrição, pois com ela posso exiber ou utilizar ela em outro lugar
    return transcricao
from legendador import legendar
import streamlit as st

# Aqui vai ser a função principal, onde ire colocar todo o código como interface, titulos, etc...
def meu_app():
    # Titulo e divisoria
    st.header("Legendador de Vídeo e áudio", divider=True)

    # Subtitulo
        # Os textos do streamlit tem formato Markdown
    st.markdown("#### Gere a legenda de qualquer vídeo ou áudio automaticamente")

    # Aqui estou fazendo a chamada da ferramenta(file_uploader) do streamlit para fazer upload de arquivos, e usado (type) para define quais formatos vai ser aceito
    arquivo_video = st.file_uploader("Selecione o vídio (.mp4) ou áudio (.mp3) para legenda", type=["mp4", "mp3"])

    # Aqui caso a legenda já exista não ira fazer nada, caso ela não exista ela sera criada
    if arquivo_video:
        legenda = legendar(arquivo_video)
        # Aqui estou usado o (.write) para escrever a mensagem de sucesso, e o (.name) para pegar somente o nome do arquivo
        st.write(f"Arquivo {arquivo_video.name} legendado com sucesso")
        # Aqui novamente usado o (.write) mas para escrever dessa vez a legenda em si
        st.write(legenda)


#Utilizado boas práticas
#Não é obrigatório, mas isso diz básicamente quer, se eu importa ele para outro arquivo no qual
    #não tenha o nome "main" ele não ira inicia porque o if sera igual a false, e só uma estrutura que
        #colocamos para quando queremos roda diretamente ele executar o quer tiver dentro, e caso nos quisemos importa-lo 
            #ele não ira executar o que estive dentro.


# Para executar o código no streamlit tem que usar o stramlit run e o nome do arquivo no terminal: streamlit run main.py
if __name__ == "__main__":
    meu_app()
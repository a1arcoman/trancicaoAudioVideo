# 🎵 VideoTranslate - Transcritor de Áudio e Vídeo

Um software livre desenvolvido em Python que utiliza APIs do Windows para transcrever arquivos MP4 (vídeos) e MP3 (áudios) para texto, com interface gráfica intuitiva.

## 📋 Características

- ✅ **Transcrição automática** de arquivos MP4 e MP3
- ✅ **Interface gráfica** amigável com Tkinter
- ✅ **Processamento em tempo real** com feedback visual
- ✅ **Suporte ao português brasileiro** (pt-BR)
- ✅ **Conversão automática** de formatos para WAV
- ✅ **Divisão inteligente** de áudio em segmentos
- ✅ **Tratamento robusto de erros** com fallback offline
- ✅ **Exportação** para arquivo TXT

## 🛠️ Tecnologias Utilizadas

- **Python 3.13+**
- **SpeechRecognition** - Reconhecimento de voz
- **pydub** - Processamento de áudio
- **tkinter** - Interface gráfica
- **Google Speech API** - Transcrição online
- **PocketSphinx** - Transcrição offline (fallback)

## 📦 Pré-requisitos

### Dependências Python
```bash
pip install SpeechRecognition pydub pocketsphinx
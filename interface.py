import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from transcriber import transcribe_audio, converter_para_wav
import threading
import os
import glob

# Lista global para armazenar arquivos selecionados
arquivos_selecionados = []

def iniciar_transcricao():
    try:
        if not arquivos_selecionados:
            messagebox.showwarning("Atenção", "Selecione arquivos ou uma pasta para transcrever")
            return
        
        # Atualiza UI
        btn_iniciar.config(state=tk.DISABLED)
        btn_selecionar_arquivo.config(state=tk.DISABLED)
        btn_selecionar_multiplos.config(state=tk.DISABLED)
        btn_selecionar_pasta.config(state=tk.DISABLED)
        btn_limpar.config(state=tk.DISABLED)
        txt_saida.delete(1.0, tk.END)
        
        # Cria thread para evitar congelamento da UI
        thread = threading.Thread(target=executar_transcricao_lote, args=(arquivos_selecionados.copy(),))
        thread.start()
    except Exception as e:
        messagebox.showerror("Erro", str(e))
        reativar_botoes()

def executar_transcricao_lote(lista_arquivos):
    try:
        total_arquivos = len(lista_arquivos)
        arquivos_processados = 0
        arquivos_com_erro = 0
        
        def callback_progresso(mensagem):
            txt_saida.insert(tk.END, mensagem + '\n')
            txt_saida.see(tk.END)
            txt_saida.update()
        
        callback_progresso(f"=== INICIANDO PROCESSAMENTO EM LOTE ===")
        callback_progresso(f"Total de arquivos: {total_arquivos}")
        callback_progresso(f"="*50)
        
        for i, arquivo in enumerate(lista_arquivos, 1):
            try:
                callback_progresso(f"\n[{i}/{total_arquivos}] Processando: {os.path.basename(arquivo)}")
                
                # Atualizar barra de progresso
                progresso_geral = (i-1) / total_arquivos * 100
                progress_bar['value'] = progresso_geral
                progress_bar.update()
                
                wav_file = converter_para_wav(arquivo)
                callback_progresso(f"✓ Arquivo convertido para WAV")
                
                resultado = ""
                chunk_count = 0
                for chunk in transcribe_audio(wav_file, ".", callback_progresso):
                    resultado += chunk + " "
                    chunk_count += 1
                    
                    # Atualizar progresso do arquivo atual
                    callback_progresso(f"  → Chunk {chunk_count} processado")
                    
                nome_saida = os.path.splitext(arquivo)[0] + "_transcrito.txt"
                with open(nome_saida, 'w', encoding='utf-8') as f:
                    f.write(resultado.strip())
                    
                callback_progresso(f"✓ Transcrição salva: {os.path.basename(nome_saida)}")
                arquivos_processados += 1
                
            except Exception as e:
                callback_progresso(f"✗ ERRO no arquivo {os.path.basename(arquivo)}: {str(e)}")
                arquivos_com_erro += 1
            
            # Atualizar barra de progresso final do arquivo
            progresso_geral = i / total_arquivos * 100
            progress_bar['value'] = progresso_geral
            progress_bar.update()
        
        # Relatório final
        callback_progresso(f"\n" + "="*50)
        callback_progresso(f"=== PROCESSAMENTO CONCLUÍDO ===")
        callback_progresso(f"Arquivos processados com sucesso: {arquivos_processados}")
        callback_progresso(f"Arquivos com erro: {arquivos_com_erro}")
        callback_progresso(f"Total: {total_arquivos}")
        
        if arquivos_processados > 0:
            # Adiciona botão para abrir pasta apenas se não existir
            if not hasattr(executar_transcricao_lote, 'btn_pasta_criado'):
                btn_abrir_pasta = tk.Button(frame_botoes, text="Abrir Pasta dos Resultados", 
                                          command=lambda: os.startfile(os.path.dirname(lista_arquivos[0])))
                btn_abrir_pasta.pack(side=tk.LEFT, padx=5)
                executar_transcricao_lote.btn_pasta_criado = True
        
        if arquivos_com_erro == 0:
            messagebox.showinfo("Sucesso", f"Todos os {arquivos_processados} arquivos foram transcritos com sucesso!")
        else:
            messagebox.showwarning("Concluído com avisos", 
                                 f"Processamento concluído:\n" +
                                 f"• Sucessos: {arquivos_processados}\n" +
                                 f"• Erros: {arquivos_com_erro}")
        
    except Exception as e:
        messagebox.showerror("Erro", f"Erro geral no processamento: {str(e)}")
    finally:
        progress_bar['value'] = 100
        reativar_botoes()

def reativar_botoes():
    btn_iniciar.config(state=tk.NORMAL)
    btn_selecionar_arquivo.config(state=tk.NORMAL)
    btn_selecionar_multiplos.config(state=tk.NORMAL)
    btn_selecionar_pasta.config(state=tk.NORMAL)
    btn_limpar.config(state=tk.NORMAL)

def selecionar_arquivo_unico():
    arquivo = filedialog.askopenfilename(
        title="Selecionar um arquivo",
        filetypes=(
            ("Arquivos de Áudio/Vídeo", "*.mp4 *.mp3 *.wav"),
            ("Arquivos MP4", "*.mp4"), 
            ("Arquivos MP3", "*.mp3"),
            ("Arquivos WAV", "*.wav"),
            ("Todos os arquivos", "*.*")
        )
    )
    if arquivo:
        arquivos_selecionados.clear()
        arquivos_selecionados.append(arquivo)
        atualizar_lista_arquivos()

def selecionar_multiplos_arquivos():
    arquivos = filedialog.askopenfilenames(
        title="Selecionar múltiplos arquivos",
        filetypes=(
            ("Arquivos de Áudio/Vídeo", "*.mp4 *.mp3 *.wav"),
            ("Arquivos MP4", "*.mp4"), 
            ("Arquivos MP3", "*.mp3"),
            ("Arquivos WAV", "*.wav"),
            ("Todos os arquivos", "*.*")
        )
    )
    if arquivos:
        arquivos_selecionados.clear()
        arquivos_selecionados.extend(arquivos)
        atualizar_lista_arquivos()

def selecionar_pasta():
    pasta = filedialog.askdirectory(title="Selecionar pasta com arquivos de áudio/vídeo")
    if pasta:
        # Buscar todos os arquivos compatíveis na pasta
        extensoes = ['*.mp3', '*.mp4', '*.wav']
        arquivos_encontrados = []
        
        for extensao in extensoes:
            arquivos_encontrados.extend(glob.glob(os.path.join(pasta, extensao)))
            # Buscar também em subpastas (opcional)
            arquivos_encontrados.extend(glob.glob(os.path.join(pasta, '**', extensao), recursive=True))
        
        if arquivos_encontrados:
            arquivos_selecionados.clear()
            arquivos_selecionados.extend(sorted(set(arquivos_encontrados)))  # Remove duplicatas e ordena
            atualizar_lista_arquivos()
            messagebox.showinfo("Pasta selecionada", 
                              f"Encontrados {len(arquivos_selecionados)} arquivos compatíveis na pasta selecionada.")
        else:
            messagebox.showwarning("Nenhum arquivo encontrado", 
                                 "Não foram encontrados arquivos MP3, MP4 ou WAV na pasta selecionada.")

def limpar_selecao():
    arquivos_selecionados.clear()
    atualizar_lista_arquivos()
    progress_bar['value'] = 0

def atualizar_lista_arquivos():
    # Limpar lista
    lista_arquivos.delete(0, tk.END)
    
    # Adicionar arquivos selecionados
    for arquivo in arquivos_selecionados:
        nome_arquivo = os.path.basename(arquivo)
        lista_arquivos.insert(tk.END, nome_arquivo)
    
    # Atualizar label de contagem
    label_contagem.config(text=f"Arquivos selecionados: {len(arquivos_selecionados)}")

# Configuração da janela principal
janela = tk.Tk()
janela.title("Transcrição de Vídeos e Áudios - Processamento em Lote")
janela.geometry("800x600")
janela.minsize(600, 500)

# Frame principal
frame = tk.Frame(janela, padx=10, pady=10)
frame.pack(fill=tk.BOTH, expand=True)

# Frame para seleção de arquivos
frame_selecao = tk.LabelFrame(frame, text="Seleção de Arquivos", padx=5, pady=5)
frame_selecao.pack(fill=tk.X, pady=(0, 10))

# Botões de seleção
frame_botoes = tk.Frame(frame_selecao)
frame_botoes.pack(fill=tk.X, pady=5)

btn_selecionar_arquivo = tk.Button(frame_botoes, text="📄 Arquivo Único", command=selecionar_arquivo_unico)
btn_selecionar_arquivo.pack(side=tk.LEFT, padx=(0, 5))

btn_selecionar_multiplos = tk.Button(frame_botoes, text="📄📄 Múltiplos Arquivos", command=selecionar_multiplos_arquivos)
btn_selecionar_multiplos.pack(side=tk.LEFT, padx=5)

btn_selecionar_pasta = tk.Button(frame_botoes, text="📁 Pasta Completa", command=selecionar_pasta)
btn_selecionar_pasta.pack(side=tk.LEFT, padx=5)

btn_limpar = tk.Button(frame_botoes, text="🗑️ Limpar", command=limpar_selecao)
btn_limpar.pack(side=tk.LEFT, padx=5)

# Label de contagem
label_contagem = tk.Label(frame_selecao, text="Arquivos selecionados: 0", font=("Arial", 9))
label_contagem.pack(anchor="w", pady=(5, 0))

# Lista de arquivos selecionados
frame_lista = tk.Frame(frame_selecao)
frame_lista.pack(fill=tk.BOTH, expand=True, pady=5)

scrollbar_lista = tk.Scrollbar(frame_lista)
scrollbar_lista.pack(side=tk.RIGHT, fill=tk.Y)

lista_arquivos = tk.Listbox(frame_lista, height=4, yscrollcommand=scrollbar_lista.set)
lista_arquivos.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
scrollbar_lista.config(command=lista_arquivos.yview)

# Barra de progresso
frame_progresso = tk.Frame(frame)
frame_progresso.pack(fill=tk.X, pady=(0, 10))

tk.Label(frame_progresso, text="Progresso Geral:").pack(anchor="w")
progress_bar = ttk.Progressbar(frame_progresso, length=400, mode='determinate')
progress_bar.pack(fill=tk.X, pady=5)

# Botão de iniciar
btn_iniciar = tk.Button(frame, text="🚀 Iniciar Transcrição em Lote", command=iniciar_transcricao, 
                       font=("Arial", 10, "bold"), bg="#4CAF50", fg="white")
btn_iniciar.pack(pady=10)

# Área de texto para saída
tk.Label(frame, text="Log de Progresso:").pack(anchor="w")
txt_saida = scrolledtext.ScrolledText(frame, height=12)
txt_saida.pack(fill=tk.BOTH, expand=True)

janela.mainloop()
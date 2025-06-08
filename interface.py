import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
from transcriber import transcribe_audio, converter_para_wav, limpar_arquivo_temp
import threading
import os
import glob
import json
import hashlib
import json
from datetime import datetime

# Lista global para armazenar arquivos selecionados
arquivos_selecionados = []

# Configurações padrão
config_transcricao = {
    # Reconhecimento
    'energy_threshold': 300,
    'pause_threshold': 0.6,
    'operation_timeout': 30,
    'phrase_threshold': 0.3,
    'non_speaking_duration': 0.6,
    
    # Divisão de áudio
    'min_silence_len': 700,
    'silence_thresh_offset': -12,
    'keep_silence': 400,
    'chunk_length': 10000,
    'max_chunk_size': 15000,
    'sub_chunk_length': 8000,
    
    # Processamento
    'max_tentativas': 2,
    'timeout_tentativa': 15,
    'pausa_entre_tentativas': 0.8,
    'sample_rate': 16000,
    'filtro_freq_baixa': 80,
    'filtro_freq_alta': 8000,
    
    # Timestamp
    'incluir_timestamp': False
}

def salvar_configuracoes():
    try:
        with open('config_transcricao.json', 'w', encoding='utf-8') as f:
            json.dump(config_transcricao, f, indent=2)
    except Exception as e:
        print(f"Erro ao salvar configurações: {e}")

def carregar_configuracoes():
    global config_transcricao
    try:
        if os.path.exists('config_transcricao.json'):
            with open('config_transcricao.json', 'r', encoding='utf-8') as f:
                config_carregada = json.load(f)
                config_transcricao.update(config_carregada)
    except Exception as e:
        messagebox.showwarning("Aviso", f"Erro ao carregar configurações: {str(e)}\nUsando configurações padrão.")

def abrir_configuracoes():
    # Janela de configurações
    janela_config = tk.Toplevel(janela)
    janela_config.title("Configurações de Transcrição")
    janela_config.geometry("600x700")
    janela_config.resizable(True, True)
    
    # Notebook para organizar as abas
    notebook = ttk.Notebook(janela_config)
    notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # Aba 1: Reconhecimento de Voz
    frame_reconhecimento = ttk.Frame(notebook)
    notebook.add(frame_reconhecimento, text="Reconhecimento")
    
    # Variáveis para os campos
    vars_config = {}
    
    # Função para criar campo numérico
    def criar_campo_numerico(parent, label, key, tipo=float, row=0):
        tk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=5, pady=2)
        var = tk.StringVar(value=str(config_transcricao[key]))
        entry = tk.Entry(parent, textvariable=var, width=15)
        entry.grid(row=row, column=1, padx=5, pady=2)
        vars_config[key] = (var, tipo)
        return var
    
    # Campos de Reconhecimento
    tk.Label(frame_reconhecimento, text="Configurações do Reconhecedor:", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=5, pady=(10,5))
    
    criar_campo_numerico(frame_reconhecimento, "Limite de Energia (energy_threshold):", 'energy_threshold', int, 1)
    criar_campo_numerico(frame_reconhecimento, "Pausa entre Frases (s):", 'pause_threshold', float, 2)
    criar_campo_numerico(frame_reconhecimento, "Timeout Operação (s):", 'operation_timeout', int, 3)
    criar_campo_numerico(frame_reconhecimento, "Limite de Frase (s):", 'phrase_threshold', float, 4)
    criar_campo_numerico(frame_reconhecimento, "Duração Não-Fala (s):", 'non_speaking_duration', float, 5)
    
    # Aba 2: Divisão de Áudio
    frame_divisao = ttk.Frame(notebook)
    notebook.add(frame_divisao, text="Divisão de Áudio")
    
    tk.Label(frame_divisao, text="Configurações de Divisão:", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=5, pady=(10,5))
    
    criar_campo_numerico(frame_divisao, "Silêncio Mínimo (ms):", 'min_silence_len', int, 1)
    criar_campo_numerico(frame_divisao, "Offset Threshold Silêncio (dB):", 'silence_thresh_offset', int, 2)
    criar_campo_numerico(frame_divisao, "Manter Silêncio (ms):", 'keep_silence', int, 3)
    criar_campo_numerico(frame_divisao, "Tamanho Chunk Forçado (ms):", 'chunk_length', int, 4)
    criar_campo_numerico(frame_divisao, "Tamanho Máximo Chunk (ms):", 'max_chunk_size', int, 5)
    criar_campo_numerico(frame_divisao, "Tamanho Sub-chunk (ms):", 'sub_chunk_length', int, 6)
    
    # Aba 3: Processamento
    frame_processamento = ttk.Frame(notebook)
    notebook.add(frame_processamento, text="Processamento")
    
    tk.Label(frame_processamento, text="Configurações de Processamento:", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", padx=5, pady=(10,5))
    
    criar_campo_numerico(frame_processamento, "Máximo de Tentativas:", 'max_tentativas', int, 1)
    criar_campo_numerico(frame_processamento, "Timeout por Tentativa (s):", 'timeout_tentativa', int, 2)
    criar_campo_numerico(frame_processamento, "Pausa entre Tentativas (s):", 'pausa_entre_tentativas', float, 3)
    criar_campo_numerico(frame_processamento, "Taxa de Amostragem (Hz):", 'sample_rate', int, 4)
    criar_campo_numerico(frame_processamento, "Filtro Freq. Baixa (Hz):", 'filtro_freq_baixa', int, 5)
    criar_campo_numerico(frame_processamento, "Filtro Freq. Alta (Hz):", 'filtro_freq_alta', int, 6)
    
    # Frame para botões
    frame_botoes_config = tk.Frame(janela_config)
    frame_botoes_config.pack(fill=tk.X, padx=10, pady=10)
    
    def aplicar_configuracoes():
        try:
            # Validar e aplicar configurações
            for key, (var, tipo) in vars_config.items():
                valor = var.get().strip()
                if not valor:
                    raise ValueError(f"Campo '{key}' não pode estar vazio")
                
                if tipo == int:
                    config_transcricao[key] = int(valor)
                elif tipo == float:
                    config_transcricao[key] = float(valor)
            
            # Validações específicas
            if config_transcricao['energy_threshold'] < 0:
                raise ValueError("Energy threshold deve ser positivo")
            if config_transcricao['pause_threshold'] <= 0:
                raise ValueError("Pause threshold deve ser maior que zero")
            if config_transcricao['min_silence_len'] < 100:
                raise ValueError("Silêncio mínimo deve ser pelo menos 100ms")
            if config_transcricao['max_tentativas'] < 1:
                raise ValueError("Deve haver pelo menos 1 tentativa")
            
            messagebox.showinfo("Sucesso", "Configurações aplicadas com sucesso!")
            janela_config.destroy()
            
        except ValueError as e:
            messagebox.showerror("Erro de Validação", str(e))
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao aplicar configurações: {str(e)}")
    
    def resetar_configuracoes():
        if messagebox.askyesno("Confirmar", "Resetar todas as configurações para os valores padrão?"):
            # Resetar para valores padrão
            config_padrao = {
                'energy_threshold': 300,
                'pause_threshold': 0.6,
                'operation_timeout': 30,
                'phrase_threshold': 0.3,
                'non_speaking_duration': 0.6,
                'min_silence_len': 700,
                'silence_thresh_offset': -12,
                'keep_silence': 400,
                'chunk_length': 10000,
                'max_chunk_size': 15000,
                'sub_chunk_length': 8000,
                'max_tentativas': 2,
                'timeout_tentativa': 15,
                'pausa_entre_tentativas': 0.8,
                'sample_rate': 16000,
                'filtro_freq_baixa': 80,
                'filtro_freq_alta': 8000
            }
            
            config_transcricao.update(config_padrao)
            
            # Atualizar campos na interface
            for key, (var, tipo) in vars_config.items():
                var.set(str(config_transcricao[key]))
    
    # Botões
    tk.Button(frame_botoes_config, text="Aplicar", command=aplicar_configuracoes, bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
    tk.Button(frame_botoes_config, text="Salvar", command=salvar_configuracoes, bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=5)
    tk.Button(frame_botoes_config, text="Resetar", command=resetar_configuracoes, bg="#FF9800", fg="white").pack(side=tk.LEFT, padx=5)
    tk.Button(frame_botoes_config, text="Cancelar", command=janela_config.destroy, bg="#f44336", fg="white").pack(side=tk.RIGHT, padx=5)

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
        callback_progresso(f"Configurações ativas: {len(config_transcricao)} parâmetros")
        if incluir_timestamp.get():
            callback_progresso(f"✓ Timestamps habilitados")
        callback_progresso(f"="*50)
        
        for i, arquivo in enumerate(lista_arquivos, 1):
            wav_file = None
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
                chunks_com_erro = 0
                
                # Atualizar configuração com timestamp
                config_atual = config_transcricao.copy()
                config_atual['incluir_timestamp'] = incluir_timestamp.get()
                
                # Passar configurações para a função de transcrição
                for chunk_data in transcribe_audio(wav_file, ".", callback_progresso, config=config_atual):
                    if isinstance(chunk_data, dict) and 'texto' in chunk_data:
                        # Formato com timestamp
                        if chunk_data.get('timestamp'):
                            resultado += f"[{chunk_data['timestamp']}] {chunk_data['texto']}\n"
                        else:
                            resultado += chunk_data['texto'] + " "
                    else:
                        # Formato antigo (só texto)
                        resultado += str(chunk_data) + " "
                    
                    chunk_count += 1
                    
                    # Contar erros
                    texto_chunk = chunk_data.get('texto', str(chunk_data)) if isinstance(chunk_data, dict) else str(chunk_data)
                    if "[ERRO" in texto_chunk or "[Erro" in texto_chunk:
                        chunks_com_erro += 1
                    
                    # Atualizar progresso do arquivo atual
                    if chunk_count % 5 == 0:  # A cada 5 chunks
                        callback_progresso(f"  → {chunk_count} chunks processados")
                
                # Salvar resultado
                sufixo = "_transcrito_com_timestamp.txt" if incluir_timestamp.get() else "_transcrito.txt"
                nome_saida = os.path.splitext(arquivo)[0] + sufixo
                with open(nome_saida, 'w', encoding='utf-8') as f:
                    f.write(resultado.strip())
                    
                callback_progresso(f"✓ Transcrição salva: {os.path.basename(nome_saida)}")
                callback_progresso(f"  → Total de chunks: {chunk_count}, Chunks com erro: {chunks_com_erro}")
                
                if chunks_com_erro > 0:
                    callback_progresso(f"  ⚠️ Atenção: {chunks_com_erro} chunks tiveram problemas")
                
                arquivos_processados += 1
                
            except Exception as e:
                callback_progresso(f"✗ ERRO no arquivo {os.path.basename(arquivo)}: {str(e)}")
                arquivos_com_erro += 1
            
            finally:
                # Limpar arquivo temporário WAV
                if wav_file:
                    limpar_arquivo_temp(wav_file)
                    callback_progresso(f"  → Arquivos temporários removidos")
            
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
janela.geometry("800x680")
janela.minsize(600, 500)

# MOVER A CRIAÇÃO DA VARIÁVEL PARA AQUI (após criar a janela):
# Variável global para controlar timestamp
incluir_timestamp = tk.BooleanVar()

# Carregar configurações ao iniciar
carregar_configuracoes()

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

# Botão de configurações
btn_configuracoes = tk.Button(frame_botoes, text="⚙️ Configurações", command=abrir_configuracoes, bg="#9C27B0", fg="white")
btn_configuracoes.pack(side=tk.RIGHT, padx=5)

# Comentar ou remover estas linhas temporariamente:
# btn_verificar_consistencia = tk.Button(frame_botoes, text="🔍 Verificar Consistência", 
#                                       command=verificar_consistencia_arquivos, 
#                                       bg="#2196F3", fg="white")
# btn_verificar_consistencia.pack(side=tk.RIGHT, padx=(5, 0))

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

# Frame para opções de transcrição
frame_opcoes = tk.LabelFrame(frame, text="Opções de Transcrição", padx=5, pady=5)
frame_opcoes.pack(fill=tk.X, pady=(0, 10))

# Checkbox para timestamp
chk_timestamp = tk.Checkbutton(frame_opcoes, text="🕒 Incluir timestamps na transcrição", 
                              variable=incluir_timestamp, font=("Arial", 9))
chk_timestamp.pack(anchor="w", padx=5, pady=5)

# Label explicativo
label_explicacao = tk.Label(frame_opcoes, 
                           text="Quando ativado, cada segmento de áudio terá seu tempo de início marcado no formato [MM:SS]",
                           font=("Arial", 8), fg="gray")
label_explicacao.pack(anchor="w", padx=20, pady=(0, 5))

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


def verificar_consistencia_arquivos():
    """Verifica a consistência dos arquivos de transcrição gerados"""
    if not arquivos_selecionados:
        messagebox.showwarning("Aviso", "Selecione os arquivos originais para verificar a consistência.")
        return
    
    # Criar janela de verificação
    janela_verificacao = tk.Toplevel(janela)
    janela_verificacao.title("Verificação de Consistência")
    janela_verificacao.geometry("700x500")
    janela_verificacao.resizable(True, True)
    
    # Frame principal
    frame_verif = tk.Frame(janela_verificacao, padx=10, pady=10)
    frame_verif.pack(fill=tk.BOTH, expand=True)
    
    # Título
    tk.Label(frame_verif, text="Verificação de Consistência dos Arquivos", 
             font=("Arial", 12, "bold")).pack(pady=(0, 10))
    
    # Área de texto para resultados
    txt_verificacao = scrolledtext.ScrolledText(frame_verif, height=20)
    txt_verificacao.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
    
    # Frame para botões
    frame_btn_verif = tk.Frame(frame_verif)
    frame_btn_verif.pack(fill=tk.X)
    
    def executar_verificacao():
        txt_verificacao.delete(1.0, tk.END)
        txt_verificacao.insert(tk.END, "=== INICIANDO VERIFICAÇÃO DE CONSISTÊNCIA ===\n\n")
        txt_verificacao.update()
        
        arquivos_ok = 0
        arquivos_problemas = 0
        arquivos_faltando = 0
        problemas_encontrados = []
        
        for i, arquivo_original in enumerate(arquivos_selecionados, 1):
            nome_base = os.path.splitext(arquivo_original)[0]
            
            # Verificar ambos os tipos de arquivo de saída
            arquivo_normal = nome_base + "_transcrito.txt"
            arquivo_timestamp = nome_base + "_transcrito_com_timestamp.txt"
            
            txt_verificacao.insert(tk.END, f"[{i}/{len(arquivos_selecionados)}] Verificando: {os.path.basename(arquivo_original)}\n")
            txt_verificacao.update()
            
            arquivo_transcricao = None
            if os.path.exists(arquivo_timestamp):
                arquivo_transcricao = arquivo_timestamp
                tipo_arquivo = "com timestamp"
            elif os.path.exists(arquivo_normal):
                arquivo_transcricao = arquivo_normal
                tipo_arquivo = "normal"
            
            if not arquivo_transcricao:
                txt_verificacao.insert(tk.END, f"  ❌ FALTANDO: Arquivo de transcrição não encontrado\n")
                arquivos_faltando += 1
                problemas_encontrados.append({
                    'arquivo': arquivo_original,
                    'problema': 'Arquivo de transcrição não encontrado',
                    'tipo': 'faltando'
                })
                continue
            
            # Verificar integridade do arquivo
            try:
                with open(arquivo_transcricao, 'r', encoding='utf-8') as f:
                    conteudo = f.read()
                
                # Verificações de consistência
                problemas_arquivo = []
                
                # 1. Verificar se o arquivo não está vazio
                if len(conteudo.strip()) == 0:
                    problemas_arquivo.append("Arquivo vazio")
                
                # 2. Verificar se há muitos erros de transcrição
                linhas = conteudo.split('\n')
                linhas_com_erro = sum(1 for linha in linhas if '[ERRO' in linha or '[Erro' in linha)
                total_linhas = len([linha for linha in linhas if linha.strip()])
                
                if total_linhas > 0:
                    percentual_erro = (linhas_com_erro / total_linhas) * 100
                    if percentual_erro > 50:
                        problemas_arquivo.append(f"Alto percentual de erros: {percentual_erro:.1f}%")
                
                # 3. Verificar tamanho mínimo esperado
                tamanho_arquivo = os.path.getsize(arquivo_transcricao)
                if tamanho_arquivo < 50:  # Menos de 50 bytes é suspeito
                    problemas_arquivo.append(f"Arquivo muito pequeno: {tamanho_arquivo} bytes")
                
                # 4. Verificar se há timestamps quando esperado
                if "timestamp" in arquivo_transcricao and not any('[' in linha and ']' in linha for linha in linhas[:10]):
                    problemas_arquivo.append("Timestamps esperados mas não encontrados")
                
                # 5. Verificar encoding e caracteres estranhos
                caracteres_estranhos = sum(1 for char in conteudo if ord(char) > 127 and char not in 'áéíóúàèìòùâêîôûãõçÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÃÕÇ')
                if caracteres_estranhos > len(conteudo) * 0.1:  # Mais de 10% de caracteres estranhos
                    problemas_arquivo.append(f"Muitos caracteres não reconhecidos: {caracteres_estranhos}")
                
                if problemas_arquivo:
                    txt_verificacao.insert(tk.END, f"  ⚠️ PROBLEMAS ({tipo_arquivo}): {', '.join(problemas_arquivo)}\n")
                    arquivos_problemas += 1
                    problemas_encontrados.append({
                        'arquivo': arquivo_original,
                        'transcricao': arquivo_transcricao,
                        'problema': ', '.join(problemas_arquivo),
                        'tipo': 'problemas'
                    })
                else:
                    txt_verificacao.insert(tk.END, f"  ✅ OK ({tipo_arquivo}): {total_linhas} linhas, {tamanho_arquivo} bytes")
                    if linhas_com_erro > 0:
                        txt_verificacao.insert(tk.END, f", {linhas_com_erro} erros")
                    txt_verificacao.insert(tk.END, "\n")
                    arquivos_ok += 1
                    
            except Exception as e:
                txt_verificacao.insert(tk.END, f"  ❌ ERRO: Não foi possível ler o arquivo: {str(e)}\n")
                arquivos_problemas += 1
                problemas_encontrados.append({
                    'arquivo': arquivo_original,
                    'transcricao': arquivo_transcricao,
                    'problema': f'Erro de leitura: {str(e)}',
                    'tipo': 'erro_leitura'
                })
        
        # Relatório final
        txt_verificacao.insert(tk.END, "\n" + "="*50 + "\n")
        txt_verificacao.insert(tk.END, "=== RELATÓRIO DE CONSISTÊNCIA ===\n")
        txt_verificacao.insert(tk.END, f"Arquivos verificados: {len(arquivos_selecionados)}\n")
        txt_verificacao.insert(tk.END, f"✅ Arquivos OK: {arquivos_ok}\n")
        txt_verificacao.insert(tk.END, f"⚠️ Arquivos com problemas: {arquivos_problemas}\n")
        txt_verificacao.insert(tk.END, f"❌ Arquivos faltando: {arquivos_faltando}\n")
        
        # Calcular taxa de sucesso
        if len(arquivos_selecionados) > 0:
            taxa_sucesso = (arquivos_ok / len(arquivos_selecionados)) * 100
            txt_verificacao.insert(tk.END, f"📊 Taxa de sucesso: {taxa_sucesso:.1f}%\n")
        
        # Salvar relatório detalhado
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nome_relatorio = f"relatorio_consistencia_{timestamp}.json"
        
        relatorio = {
            'timestamp': datetime.now().isoformat(),
            'total_arquivos': len(arquivos_selecionados),
            'arquivos_ok': arquivos_ok,
            'arquivos_problemas': arquivos_problemas,
            'arquivos_faltando': arquivos_faltando,
            'taxa_sucesso': taxa_sucesso if len(arquivos_selecionados) > 0 else 0,
            'problemas_detalhados': problemas_encontrados
        }
        
        try:
            with open(nome_relatorio, 'w', encoding='utf-8') as f:
                json.dump(relatorio, f, indent=2, ensure_ascii=False)
            txt_verificacao.insert(tk.END, f"\n📄 Relatório salvo: {nome_relatorio}\n")
        except Exception as e:
            txt_verificacao.insert(tk.END, f"\n⚠️ Erro ao salvar relatório: {str(e)}\n")
        
        # Habilitar botão de reprocessamento se houver problemas
        if problemas_encontrados:
            btn_reprocessar.config(state=tk.NORMAL)
        
        txt_verificacao.see(tk.END)
    
    def reprocessar_problemas():
        """Reprocessa apenas os arquivos que tiveram problemas"""
        arquivos_problema = [item['arquivo'] for item in problemas_encontrados 
                           if item['tipo'] in ['faltando', 'problemas']]
        
        if not arquivos_problema:
            messagebox.showinfo("Info", "Não há arquivos para reprocessar.")
            return
        
        resposta = messagebox.askyesno("Reprocessar", 
                                     f"Deseja reprocessar {len(arquivos_problema)} arquivos com problemas?")
        if resposta:
            # Fechar janela de verificação
            janela_verificacao.destroy()
            
            # Definir apenas os arquivos com problema para reprocessamento
            global arquivos_selecionados
            arquivos_selecionados_backup = arquivos_selecionados.copy()
            arquivos_selecionados.clear()
            arquivos_selecionados.extend(arquivos_problema)
            atualizar_lista_arquivos()
            
            # Iniciar transcrição
            iniciar_transcricao()
            
            # Restaurar lista original após processamento
            def restaurar_lista():
                global arquivos_selecionados
                arquivos_selecionados.clear()
                arquivos_selecionados.extend(arquivos_selecionados_backup)
                atualizar_lista_arquivos()
            
            janela.after(1000, restaurar_lista)  # Restaurar após 1 segundo
    
    # Botões
    btn_verificar = tk.Button(frame_btn_verif, text="🔍 Iniciar Verificação", 
                             command=executar_verificacao, bg="#2196F3", fg="white")
    btn_verificar.pack(side=tk.LEFT, padx=(0, 5))
    
    btn_reprocessar = tk.Button(frame_btn_verif, text="🔄 Reprocessar Problemas", 
                               command=reprocessar_problemas, bg="#FF9800", fg="white", state=tk.DISABLED)
    btn_reprocessar.pack(side=tk.LEFT, padx=5)
    
    btn_fechar = tk.Button(frame_btn_verif, text="❌ Fechar", 
                          command=janela_verificacao.destroy)
    btn_fechar.pack(side=tk.RIGHT)
    
    # Variável para armazenar problemas encontrados
    problemas_encontrados = []

# Adicionar botão de verificação na interface principal
# No frame_botoes, após o botão de configurações:
btn_verificar_consistencia = tk.Button(frame_botoes, text="🔍 Verificar Consistência", 
                                      command=verificar_consistencia_arquivos, 
                                      bg="#2196F3", fg="white")
btn_verificar_consistencia.pack(side=tk.RIGHT, padx=(5, 0))
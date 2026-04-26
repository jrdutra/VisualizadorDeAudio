import json
import subprocess
import threading
from pathlib import Path
import tkinter as tk
from tkinter import colorchooser, filedialog, messagebox
from tkinter import ttk


CONFIG_FILE = "config.json"
SUBPROCESS_CREATIONFLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)
LARGURA_VIDEO_PADRAO = 1920
ALTURA_VIDEO_PADRAO = 1080
COR_VISUALIZADOR_PADRAO = "614c00"
LARGURA_ONDA_PADRAO = int(LARGURA_VIDEO_PADRAO * 0.682)
ALTURA_ONDA_PADRAO = int(ALTURA_VIDEO_PADRAO * 0.35)
MARGEM_ESQUERDA_PADRAO = 0
MARGEM_DIREITA_PADRAO = LARGURA_VIDEO_PADRAO - LARGURA_ONDA_PADRAO
POSICAO_X_ONDA_PADRAO = MARGEM_ESQUERDA_PADRAO
POSICAO_Y_ONDA_PADRAO = int((ALTURA_VIDEO_PADRAO - ALTURA_ONDA_PADRAO) / 2)


def carregar_config():
    config_padrao = {
        "audio": "audio.m4a",
        "imagem_fundo": "Fundo-Audio.jpg",
        "pasta_saida": str(Path.cwd()),
        "nome_saida": "renderizado.mp4",
        "cor_visualizador": COR_VISUALIZADOR_PADRAO,
        "largura_onda": str(LARGURA_ONDA_PADRAO),
        "altura_onda": str(ALTURA_ONDA_PADRAO),
        "margem_esquerda": str(MARGEM_ESQUERDA_PADRAO),
        "margem_direita": str(MARGEM_DIREITA_PADRAO),
        "posicao_x_onda": str(POSICAO_X_ONDA_PADRAO),
        "posicao_y_onda": str(POSICAO_Y_ONDA_PADRAO)
    }

    arquivo = Path(CONFIG_FILE)

    if not arquivo.exists():
        arquivo.write_text(json.dumps(config_padrao, indent=4), encoding="utf-8")
        return config_padrao

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)

        config_alterado = False
        for chave, valor in config_padrao.items():
            if chave not in config:
                config[chave] = valor
                config_alterado = True

        pasta_saida = Path(config["pasta_saida"])
        if not pasta_saida.exists():
            config["pasta_saida"] = config_padrao["pasta_saida"]
            config_alterado = True

        if config_alterado:
            salvar_config(config)

        return config

    except Exception:
        arquivo.write_text(json.dumps(config_padrao, indent=4), encoding="utf-8")
        return config_padrao


def salvar_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)


def comando_disponivel(comando):
    try:
        resultado = subprocess.run(
            [comando, "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=SUBPROCESS_CREATIONFLAGS
        )
        return resultado.returncode == 0
    except FileNotFoundError:
        return False


def verificar_dependencias_ffmpeg():
    ausentes = []

    if not comando_disponivel("ffmpeg"):
        ausentes.append("ffmpeg")

    if not comando_disponivel("ffprobe"):
        ausentes.append("ffprobe")

    return ausentes


def obter_duracao_audio(audio):
    comando = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio)
    ]

    resultado = subprocess.run(
        comando,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=SUBPROCESS_CREATIONFLAGS
    )

    if resultado.returncode != 0:
        raise RuntimeError(
            "Não foi possível ler a duração do áudio com o ffprobe.\n\n"
            f"Detalhes:\n{resultado.stderr.strip()}"
        )

    return float(resultado.stdout.strip())


def criar_video_com_visualizador(
    audio: str,
    imagem_fundo: str,
    saida_mp4: str,
    progresso_callback=None,
    largura: int = LARGURA_VIDEO_PADRAO,
    altura: int = ALTURA_VIDEO_PADRAO,
    cor_visualizador: str = COR_VISUALIZADOR_PADRAO,
    largura_onda: int = LARGURA_ONDA_PADRAO,
    altura_onda: int = ALTURA_ONDA_PADRAO,
    margem_esquerda: int = MARGEM_ESQUERDA_PADRAO,
    margem_direita: int = MARGEM_DIREITA_PADRAO,
    posicao_x_onda: int = POSICAO_X_ONDA_PADRAO,
    posicao_y_onda: int = POSICAO_Y_ONDA_PADRAO,
):
    audio = Path(audio)
    imagem_fundo = Path(imagem_fundo)
    saida_mp4 = Path(saida_mp4)

    if not audio.exists():
        raise FileNotFoundError(f"Áudio não encontrado: {audio}")

    if not imagem_fundo.exists():
        raise FileNotFoundError(f"Imagem de fundo não encontrada: {imagem_fundo}")

    if not saida_mp4.parent.exists():
        raise FileNotFoundError(f"Pasta de saída não encontrada: {saida_mp4.parent}")

    duracao = obter_duracao_audio(audio)

    largura_wave = min(largura_onda, largura - posicao_x_onda - margem_direita)
    altura_wave = altura_onda

    filtro = (
        f"[0:a]showwaves=s={largura_wave}x{altura_wave}:"
        f"mode=cline:"
        f"colors=#{cor_visualizador}:"
        f"draw=full,"
        f"format=rgba[waves];"
        f"[1:v]scale={largura}:{altura}:force_original_aspect_ratio=increase,"
        f"crop={largura}:{altura}[bg];"
        f"[bg][waves]overlay={posicao_x_onda}:{posicao_y_onda}[v]"
    )

    comando = [
        "ffmpeg",
        "-y",
        "-fflags", "+genpts",
        "-i", str(audio),
        "-loop", "1",
        "-i", str(imagem_fundo),
        "-filter_complex", filtro,
        "-map", "[v]",
        "-map", "0:a",
        "-shortest",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-progress", "pipe:1",
        "-nostats",
        str(saida_mp4)
    ]

    processo = subprocess.Popen(
        comando,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        universal_newlines=True,
        creationflags=SUBPROCESS_CREATIONFLAGS
    )

    saida_ffmpeg = []

    for linha in processo.stdout:
        linha = linha.strip()
        if linha:
            saida_ffmpeg.append(linha)

        if linha.startswith("out_time_ms="):
            valor_tempo = linha.split("=", 1)[1]
            if not valor_tempo.isdigit():
                continue

            tempo_ms = int(valor_tempo)
            tempo_segundos = tempo_ms / 1_000_000
            progresso = min((tempo_segundos / duracao) * 100, 100)

            if progresso_callback:
                progresso_callback(progresso)

    processo.wait()

    if processo.returncode != 0:
        detalhes = "\n".join(saida_ffmpeg[-25:])
        raise RuntimeError(
            "Erro ao renderizar o vídeo com FFmpeg.\n\n"
            f"Detalhes:\n{detalhes}"
        )

    if progresso_callback:
        progresso_callback(100)


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Renderizador de Áudio com Visualizador")
        self.root.geometry("820x620")
        self.root.minsize(760, 590)
        self.root.resizable(True, False)

        self.config = carregar_config()
        self.dependencias_ausentes = verificar_dependencias_ffmpeg()

        self.audio_var = tk.StringVar(value=self.config["audio"])
        self.imagem_var = tk.StringVar(value=self.config["imagem_fundo"])
        self.pasta_saida_var = tk.StringVar(value=self.config["pasta_saida"])
        self.nome_saida_var = tk.StringVar(value=self.config["nome_saida"])
        self.cor_visualizador_var = tk.StringVar(value=self.config["cor_visualizador"])
        self.largura_onda_var = tk.StringVar(value=self.config["largura_onda"])
        self.altura_onda_var = tk.StringVar(value=self.config["altura_onda"])
        self.margem_esquerda_var = tk.StringVar(value=self.config["margem_esquerda"])
        self.margem_direita_var = tk.StringVar(value=self.config["margem_direita"])
        self.posicao_x_onda_var = tk.StringVar(value=self.config["posicao_x_onda"])
        self.posicao_y_onda_var = tk.StringVar(value=self.config["posicao_y_onda"])

        self.criar_interface()

        self.audio_var.trace_add("write", self.persistir_config)
        self.imagem_var.trace_add("write", self.persistir_config)
        self.pasta_saida_var.trace_add("write", self.persistir_config)
        self.nome_saida_var.trace_add("write", self.persistir_config)
        self.cor_visualizador_var.trace_add("write", self.persistir_config)
        self.largura_onda_var.trace_add("write", self.persistir_config)
        self.altura_onda_var.trace_add("write", self.persistir_config)
        self.margem_esquerda_var.trace_add("write", self.persistir_config)
        self.margem_direita_var.trace_add("write", self.persistir_config)
        self.posicao_x_onda_var.trace_add("write", self.persistir_config)
        self.posicao_y_onda_var.trace_add("write", self.persistir_config)

        self.root.after(200, self.avisar_dependencias_ausentes)

    def criar_interface(self):
        self.root.columnconfigure(0, weight=1)

        container = ttk.Frame(self.root, padding=16)
        container.grid(row=0, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)

        entrada_frame = ttk.LabelFrame(container, text="Arquivos de entrada", padding=12)
        entrada_frame.grid(row=0, column=0, sticky="ew")
        entrada_frame.columnconfigure(1, weight=1)

        self.criar_linha_arquivo(
            entrada_frame,
            linha=0,
            texto="Arquivo de áudio:",
            variavel=self.audio_var,
            comando=self.selecionar_audio
        )
        self.criar_linha_arquivo(
            entrada_frame,
            linha=1,
            texto="Imagem de fundo:",
            variavel=self.imagem_var,
            comando=self.selecionar_imagem
        )

        saida_frame = ttk.LabelFrame(container, text="Saída", padding=12)
        saida_frame.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        saida_frame.columnconfigure(1, weight=1)

        self.criar_linha_arquivo(
            saida_frame,
            linha=0,
            texto="Pasta de saída:",
            variavel=self.pasta_saida_var,
            comando=self.selecionar_pasta_saida
        )

        ttk.Label(saida_frame, text="Nome do arquivo MP4:").grid(
            row=1, column=0, sticky="w", padx=(0, 10), pady=(10, 0)
        )
        ttk.Entry(saida_frame, textvariable=self.nome_saida_var).grid(
            row=1, column=1, columnspan=2, sticky="ew", pady=(10, 0)
        )

        visualizador_frame = ttk.LabelFrame(container, text="Visualizador de áudio", padding=12)
        visualizador_frame.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        visualizador_frame.columnconfigure(1, weight=1)
        visualizador_frame.columnconfigure(3, weight=1)
        visualizador_frame.columnconfigure(5, weight=1)

        ttk.Label(visualizador_frame, text="Cor:").grid(
            row=0, column=0, sticky="w", padx=(0, 10)
        )
        ttk.Entry(
            visualizador_frame,
            textvariable=self.cor_visualizador_var,
            width=12
        ).grid(row=0, column=1, sticky="w")

        self.botao_cor = tk.Button(
            visualizador_frame,
            text="Selecionar cor",
            command=self.selecionar_cor_visualizador,
            bg=f"#{self.obter_cor_visualizador()}",
            fg="white",
            activebackground=f"#{self.obter_cor_visualizador()}"
        )
        self.botao_cor.grid(row=0, column=2, sticky="w", padx=(8, 22))

        ttk.Label(visualizador_frame, text="Largura da onda:").grid(
            row=0, column=4, sticky="w", padx=(8, 10)
        )
        ttk.Entry(
            visualizador_frame,
            textvariable=self.largura_onda_var,
            width=10
        ).grid(row=0, column=5, sticky="w")

        ttk.Label(visualizador_frame, text="Altura da onda:").grid(
            row=1, column=0, sticky="w", padx=(0, 10), pady=(10, 0)
        )
        ttk.Entry(
            visualizador_frame,
            textvariable=self.altura_onda_var,
            width=10
        ).grid(row=1, column=1, sticky="w", pady=(10, 0))

        ttk.Label(visualizador_frame, text="Margem esquerda:").grid(
            row=1, column=2, sticky="w", padx=(8, 10), pady=(10, 0)
        )
        ttk.Entry(
            visualizador_frame,
            textvariable=self.margem_esquerda_var,
            width=10
        ).grid(row=1, column=3, sticky="w", pady=(10, 0))

        ttk.Label(visualizador_frame, text="Margem direita:").grid(
            row=1, column=4, sticky="w", padx=(8, 10), pady=(10, 0)
        )
        ttk.Entry(
            visualizador_frame,
            textvariable=self.margem_direita_var,
            width=10
        ).grid(row=1, column=5, sticky="w", pady=(10, 0))

        ttk.Label(visualizador_frame, text="Posição X inicial:").grid(
            row=2, column=0, sticky="w", padx=(0, 10), pady=(10, 0)
        )
        ttk.Entry(
            visualizador_frame,
            textvariable=self.posicao_x_onda_var,
            width=10
        ).grid(row=2, column=1, sticky="w", pady=(10, 0))

        ttk.Label(visualizador_frame, text="Posição Y inicial:").grid(
            row=2, column=2, sticky="w", padx=(8, 10), pady=(10, 0)
        )
        ttk.Entry(
            visualizador_frame,
            textvariable=self.posicao_y_onda_var,
            width=10
        ).grid(row=2, column=3, sticky="w", pady=(10, 0))

        render_frame = ttk.LabelFrame(container, text="Renderização", padding=12)
        render_frame.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        render_frame.columnconfigure(0, weight=1)

        self.progress = ttk.Progressbar(
            render_frame,
            orient="horizontal",
            mode="determinate"
        )
        self.progress.grid(row=0, column=0, sticky="ew", padx=(0, 12))

        self.botao_renderizar = ttk.Button(
            render_frame,
            text="Renderizar vídeo",
            command=self.iniciar_renderizacao
        )
        self.botao_renderizar.grid(row=0, column=1, sticky="e")

        self.status_label = ttk.Label(render_frame, text="Aguardando renderização...")
        self.status_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))

        info_frame = ttk.LabelFrame(container, text="Informações", padding=12)
        info_frame.grid(row=4, column=0, sticky="ew", pady=(12, 0))

        ttk.Label(
            info_frame,
            text="É necessário ter o FFmpeg instalado no computador para renderizar os vídeos."
        ).grid(row=0, column=0, sticky="w")

        ttk.Label(
            info_frame,
            text="Idealizado e criado por João Ricardo Côre Dutra."
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))

        if self.dependencias_ausentes:
            self.botao_renderizar.config(state="disabled")
            self.status_label.config(
                text="Instale o FFmpeg e o FFprobe para habilitar a renderização."
            )

    def criar_linha_arquivo(self, frame, linha, texto, variavel, comando):
        pady = (0, 10) if linha == 0 else (0, 0)

        ttk.Label(frame, text=texto).grid(
            row=linha, column=0, sticky="w", padx=(0, 10), pady=pady
        )
        ttk.Entry(frame, textvariable=variavel).grid(
            row=linha, column=1, sticky="ew", pady=pady
        )
        ttk.Button(frame, text="Selecionar", command=comando).grid(
            row=linha, column=2, sticky="e", padx=(8, 0), pady=pady
        )

    def persistir_config(self, *args):
        self.config["audio"] = self.audio_var.get()
        self.config["imagem_fundo"] = self.imagem_var.get()
        self.config["pasta_saida"] = self.pasta_saida_var.get()
        self.config["nome_saida"] = self.nome_saida_var.get()
        self.config["cor_visualizador"] = self.cor_visualizador_var.get()
        self.config["largura_onda"] = self.largura_onda_var.get()
        self.config["altura_onda"] = self.altura_onda_var.get()
        self.config["margem_esquerda"] = self.margem_esquerda_var.get()
        self.config["margem_direita"] = self.margem_direita_var.get()
        self.config["posicao_x_onda"] = self.posicao_x_onda_var.get()
        self.config["posicao_y_onda"] = self.posicao_y_onda_var.get()
        salvar_config(self.config)
        self.atualizar_botao_cor()

    def obter_cor_visualizador(self):
        cor = self.cor_visualizador_var.get().strip().lstrip("#")
        if len(cor) == 6 and all(c in "0123456789abcdefABCDEF" for c in cor):
            return cor.lower()
        return COR_VISUALIZADOR_PADRAO

    def atualizar_botao_cor(self):
        if not hasattr(self, "botao_cor"):
            return

        cor = self.obter_cor_visualizador()
        self.botao_cor.config(bg=f"#{cor}", activebackground=f"#{cor}")

    def selecionar_cor_visualizador(self):
        cor_inicial = f"#{self.obter_cor_visualizador()}"
        _, cor_hex = colorchooser.askcolor(
            color=cor_inicial,
            title="Selecione a cor do visualizador"
        )

        if cor_hex:
            self.cor_visualizador_var.set(cor_hex.lstrip("#"))

    def avisar_dependencias_ausentes(self):
        if not self.dependencias_ausentes:
            return

        programas = ", ".join(self.dependencias_ausentes)
        messagebox.showerror(
            "FFmpeg não encontrado",
            "Não foi possível localizar os seguintes programas no computador:\n\n"
            f"{programas}\n\n"
            "Instale o FFmpeg e garanta que ffmpeg e ffprobe estejam disponíveis "
            "no PATH do Windows."
        )

    def selecionar_audio(self):
        arquivo = filedialog.askopenfilename(
            title="Selecione o áudio",
            filetypes=[
                ("Arquivos de áudio", "*.mp3 *.m4a *.wav *.aac *.flac *.ogg"),
                ("Todos os arquivos", "*.*")
            ]
        )

        if arquivo:
            self.audio_var.set(arquivo)

    def selecionar_imagem(self):
        arquivo = filedialog.askopenfilename(
            title="Selecione a imagem de fundo",
            filetypes=[
                ("Arquivos de imagem", "*.jpg *.jpeg *.png *.webp"),
                ("Todos os arquivos", "*.*")
            ]
        )

        if arquivo:
            self.imagem_var.set(arquivo)

    def selecionar_pasta_saida(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta de saída")

        if pasta:
            self.pasta_saida_var.set(pasta)

    def atualizar_progresso(self, valor):
        self.root.after(0, lambda: self.progress.config(value=valor))
        self.root.after(0, lambda: self.status_label.config(
            text=f"Renderizando... {valor:.1f}%"
        ))

    def obter_inteiro_positivo(self, variavel, nome, permitir_zero=False):
        valor_texto = variavel.get().strip()

        try:
            valor = int(valor_texto)
        except ValueError:
            raise ValueError(f"{nome} deve ser um número inteiro.")

        if permitir_zero and valor < 0:
            raise ValueError(f"{nome} não pode ser menor que zero.")

        if not permitir_zero and valor <= 0:
            raise ValueError(f"{nome} deve ser maior que zero.")

        return valor

    def validar_campos(self):
        audio = Path(self.audio_var.get())
        imagem = Path(self.imagem_var.get())
        pasta_saida = Path(self.pasta_saida_var.get())
        nome_saida = self.nome_saida_var.get().strip()
        cor_visualizador = self.obter_cor_visualizador()
        largura_onda = self.obter_inteiro_positivo(
            self.largura_onda_var, "Largura da onda"
        )
        altura_onda = self.obter_inteiro_positivo(
            self.altura_onda_var, "Altura da onda"
        )
        margem_esquerda = self.obter_inteiro_positivo(
            self.margem_esquerda_var, "Margem esquerda", permitir_zero=True
        )
        margem_direita = self.obter_inteiro_positivo(
            self.margem_direita_var, "Margem direita", permitir_zero=True
        )
        posicao_x_onda = self.obter_inteiro_positivo(
            self.posicao_x_onda_var, "Posição X inicial", permitir_zero=True
        )
        posicao_y_onda = self.obter_inteiro_positivo(
            self.posicao_y_onda_var, "Posição Y inicial", permitir_zero=True
        )

        if not audio.exists():
            raise FileNotFoundError(f"Áudio não encontrado:\n{audio}")

        if not imagem.exists():
            raise FileNotFoundError(f"Imagem de fundo não encontrada:\n{imagem}")

        if not pasta_saida.exists():
            raise FileNotFoundError(f"Pasta de saída não encontrada:\n{pasta_saida}")

        if not pasta_saida.is_dir():
            raise NotADirectoryError(f"O caminho de saída não é uma pasta:\n{pasta_saida}")

        if not nome_saida:
            raise ValueError("Informe o nome do arquivo MP4 de saída.")

        if not nome_saida.lower().endswith(".mp4"):
            nome_saida += ".mp4"
            self.nome_saida_var.set(nome_saida)

        if largura_onda > LARGURA_VIDEO_PADRAO:
            raise ValueError(f"Largura da onda não pode passar de {LARGURA_VIDEO_PADRAO}.")

        if altura_onda > ALTURA_VIDEO_PADRAO:
            raise ValueError(f"Altura da onda não pode passar de {ALTURA_VIDEO_PADRAO}.")

        largura_total = posicao_x_onda + largura_onda + margem_direita
        if largura_total > LARGURA_VIDEO_PADRAO:
            raise ValueError(
                "A soma da posição X inicial, largura da onda e margem direita "
                f"não pode passar de {LARGURA_VIDEO_PADRAO}."
            )

        altura_total = posicao_y_onda + altura_onda
        if altura_total > ALTURA_VIDEO_PADRAO:
            raise ValueError(
                "A soma da posição Y inicial e altura da onda "
                f"não pode passar de {ALTURA_VIDEO_PADRAO}."
            )

        self.cor_visualizador_var.set(cor_visualizador)
        self.margem_esquerda_var.set(str(margem_esquerda))
        self.posicao_x_onda_var.set(str(posicao_x_onda))
        self.posicao_y_onda_var.set(str(posicao_y_onda))

        opcoes_visualizador = {
            "cor_visualizador": cor_visualizador,
            "largura_onda": largura_onda,
            "altura_onda": altura_onda,
            "margem_esquerda": margem_esquerda,
            "margem_direita": margem_direita,
            "posicao_x_onda": posicao_x_onda,
            "posicao_y_onda": posicao_y_onda
        }

        return audio, imagem, pasta_saida / nome_saida, opcoes_visualizador

    def iniciar_renderizacao(self):
        self.dependencias_ausentes = verificar_dependencias_ffmpeg()
        if self.dependencias_ausentes:
            self.botao_renderizar.config(state="disabled")
            self.avisar_dependencias_ausentes()
            return

        try:
            audio, imagem, saida_mp4, opcoes_visualizador = self.validar_campos()
        except Exception as erro:
            messagebox.showerror("Erro", str(erro))
            return

        self.progress["value"] = 0
        self.status_label.config(text="Iniciando renderização...")
        self.botao_renderizar.config(state="disabled")

        thread = threading.Thread(
            target=self.renderizar_em_thread,
            args=(audio, imagem, saida_mp4, opcoes_visualizador),
            daemon=True
        )
        thread.start()

    def renderizar_em_thread(self, audio, imagem, saida_mp4, opcoes_visualizador):
        try:
            criar_video_com_visualizador(
                audio=audio,
                imagem_fundo=imagem,
                saida_mp4=str(saida_mp4),
                progresso_callback=self.atualizar_progresso,
                **opcoes_visualizador
            )

            self.root.after(0, lambda: self.status_label.config(
                text=f"Vídeo gerado com sucesso: {saida_mp4}"
            ))

            self.root.after(0, lambda: messagebox.showinfo(
                "Sucesso",
                f"Vídeo gerado com sucesso:\n{saida_mp4}"
            ))

        except Exception as erro:
            mensagem = str(erro)
            self.root.after(0, lambda: self.status_label.config(
                text="Erro na renderização."
            ))

            self.root.after(0, lambda: messagebox.showerror(
                "Erro",
                mensagem
            ))

        finally:
            self.root.after(0, lambda: self.botao_renderizar.config(state="normal"))


if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()

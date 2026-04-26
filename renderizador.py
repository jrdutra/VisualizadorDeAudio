import subprocess
from pathlib import Path


def criar_video_com_visualizador(
    audio: str,
    imagem_fundo: str,
    saida_mp4: str = "renderizado.mp4",
    largura: int = 1920,
    altura: int = 1080,
    cor_visualizador: str = "614c00",
):
    audio = Path(audio)
    imagem_fundo = Path(imagem_fundo)

    if not audio.exists():
        raise FileNotFoundError(f"Áudio não encontrado: {audio}")

    if not imagem_fundo.exists():
        raise FileNotFoundError(f"Imagem de fundo não encontrada: {imagem_fundo}")

    largura_wave = int(largura * 0.682)
    altura_wave = int(altura * 0.35)

    margem_esquerda = int(largura * 0)
    pos_y = int((altura - altura_wave) / 2)

    filtro = (
        f"[0:a]showwaves=s={largura_wave}x{altura_wave}:"
        f"mode=cline:"
        f"colors=#{cor_visualizador}:"
        f"draw=full,"
        f"format=rgba[waves];"
        f"[1:v]scale={largura}:{altura}:force_original_aspect_ratio=increase,"
        f"crop={largura}:{altura}[bg];"
        f"[bg][waves]overlay={margem_esquerda}:{pos_y}[v]"
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
        str(saida_mp4)
    ]

    subprocess.run(comando, check=True)

    print(f"Vídeo gerado com sucesso: {saida_mp4}")


criar_video_com_visualizador(
    audio="audio.m4a",
    imagem_fundo="Fundo-Audio.jpg",
    saida_mp4="renderizado.mp4"
)
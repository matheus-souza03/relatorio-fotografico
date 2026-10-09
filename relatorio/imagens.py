"""Preparação das fotos para o relatório: rotação, formato e tamanho."""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

try:  # suporte a fotos HEIC (iPhone); opcional
    import pillow_heif

    pillow_heif.register_heif_opener()
except ImportError:
    pass

# A foto ocupa cerca de 3,5 x 5 cm no relatório: 600 px no lado maior dá ~300 dpi,
# boa qualidade de impressão sem deixar o .docx pesado demais para enviar por e-mail.
LADO_MAXIMO_PX = 600
QUALIDADE_JPEG = 82
Image.MAX_IMAGE_PIXELS = 250_000_000  # celulares com câmera de 200 MP


class ErroFoto(Exception):
    """Problema com uma foto específica; a mensagem é escrita no lugar da foto no relatório."""


def processar_imagem(dados: bytes) -> bytes:
    """Converte a foto para JPEG, na orientação correta e reduzida para LADO_MAXIMO_PX."""
    try:
        imagem = Image.open(BytesIO(dados))
        imagem.draft("RGB", (LADO_MAXIMO_PX, LADO_MAXIMO_PX))  # decodifica JPEGs grandes já reduzidos
        imagem.load()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as erro:
        raise ErroFoto("O arquivo do link não é uma foto válida.") from erro

    imagem = _corrigir_rotacao(imagem)
    imagem = _para_rgb(imagem)
    imagem.thumbnail((LADO_MAXIMO_PX, LADO_MAXIMO_PX), Image.Resampling.LANCZOS)

    saida = BytesIO()
    imagem.save(saida, "JPEG", quality=QUALIDADE_JPEG, optimize=True)
    return saida.getvalue()


def _corrigir_rotacao(imagem: Image.Image) -> Image.Image:
    """Aplica a rotação gravada pelo celular (EXIF), senão a foto pode sair deitada."""
    try:
        return ImageOps.exif_transpose(imagem)
    except Exception:  # EXIF corrompido: usa a foto como está
        return imagem


def _para_rgb(imagem: Image.Image) -> Image.Image:
    if imagem.mode == "RGB":
        return imagem
    if imagem.mode in ("RGBA", "LA", "PA") or "transparency" in imagem.info:
        com_transparencia = imagem.convert("RGBA")
        fundo = Image.new("RGB", com_transparencia.size, "white")
        fundo.paste(com_transparencia, mask=com_transparencia.getchannel("A"))
        return fundo
    return imagem.convert("RGB")

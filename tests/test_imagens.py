import io

import pytest
from PIL import Image

from relatorio.imagens import LADO_MAXIMO_PX, ErroFoto, processar_imagem


def abrir(dados: bytes) -> Image.Image:
    return Image.open(io.BytesIO(dados))


def test_reduz_mantendo_a_proporcao():
    original = io.BytesIO()
    Image.new("RGB", (3000, 4000), "red").save(original, "JPEG")
    foto = abrir(processar_imagem(original.getvalue()))
    assert foto.format == "JPEG"
    assert foto.size == (LADO_MAXIMO_PX * 3 // 4, LADO_MAXIMO_PX)


def test_aplica_a_rotacao_do_celular():
    original = io.BytesIO()
    exif = Image.Exif()
    exif[0x0112] = 6  # orientação: girar 90°
    Image.new("RGB", (400, 300), "red").save(original, "JPEG", exif=exif)
    assert abrir(processar_imagem(original.getvalue())).size == (300, 400)


def test_png_transparente_vira_jpeg_com_fundo_branco():
    original = io.BytesIO()
    Image.new("RGBA", (100, 100), (0, 0, 0, 0)).save(original, "PNG")
    foto = abrir(processar_imagem(original.getvalue()))
    assert foto.mode == "RGB"
    assert foto.getpixel((50, 50))[0] > 240


def test_arquivo_que_nao_e_imagem():
    with pytest.raises(ErroFoto):
        processar_imagem(b"%PDF-1.4 isto nao e uma foto")

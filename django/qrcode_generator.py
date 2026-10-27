import hashlib
from decimal import Decimal
from pathlib import Path

import qrcode


def calcula_crc16(payload: str) -> str:
    """Calcula o CRC16-CCITT (False) exigido pelo padrão Pix (EMV)."""
    crc = 0xFFFF
    for byte in payload.encode("ascii"):
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return f"{crc:04X}"


def _tlv(tag: str, value: str) -> str:
    if not value.isascii():
        raise ValueError(f"O campo Pix {tag} deve conter somente caracteres ASCII.")
    if len(value) > 99:
        raise ValueError(f"O campo Pix {tag} excede o limite de 99 caracteres.")
    return f"{tag}{len(value):02d}{value}"


def gerar_payload_pix(pix_key, merchant_name, merchant_city, amount, txid="***"):
    """Gera o texto Pix Copia e Cola estático conforme a estrutura EMV BR Code."""
    amount_value = Decimal(str(amount)).quantize(Decimal("0.01"))
    if amount_value <= 0:
        raise ValueError("O valor do Pix deve ser maior que zero.")

    gui = _tlv("00", "br.gov.bcb.pix")
    pix_key_field = _tlv("01", pix_key)
    merchant_account = _tlv("26", gui + pix_key_field)
    additional_data = _tlv("62", _tlv("05", txid))
    payload_without_crc = "".join((
        _tlv("00", "01"),
        _tlv("01", "11"),  # QR estático
        merchant_account,
        _tlv("52", "0000"),
        _tlv("53", "986"),
        _tlv("54", f"{amount_value:.2f}"),
        _tlv("58", "BR"),
        _tlv("59", merchant_name),
        _tlv("60", merchant_city),
        additional_data,
        "6304",
    ))
    return payload_without_crc + calcula_crc16(payload_without_crc)


def gera_qrcode(chave_pix, nome_recebedor, cidade, valor, txid="***"):
    """Gera QR Pix e retorna o caminho relativo a MEDIA_ROOT."""
    payload = gerar_payload_pix(chave_pix, nome_recebedor, cidade, valor, txid)
    filename = f"pix_{hashlib.sha256(payload.encode('ascii')).hexdigest()[:16]}.png"
    output_dir = Path(__file__).resolve().parent / "media" / "temp"
    output_dir.mkdir(parents=True, exist_ok=True)
    qrcode.make(payload).save(output_dir / filename)
    return f"temp/{filename}"


if __name__ == "__main__":
    payload_pix = gerar_payload_pix(
        pix_key="88422070634",
        merchant_name="Luiz Quintino",
        merchant_city="Belo Horizonte",
        amount=200.00,
        txid="PAGTO200",
    )
    print("--- PIX COPIA E COLA ---")
    print(payload_pix)
    print("------------------------")
    print(f"QR Code salvo em: {gera_qrcode('88422070634', 'Luiz Quintino', 'Belo Horizonte', 200.00, 'PAGTO200')}")
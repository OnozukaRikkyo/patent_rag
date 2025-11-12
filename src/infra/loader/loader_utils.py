import xml.etree.ElementTree as ET


def get_text(elem: ET.Element | None) -> str | None:
    """
    要素のテキストを取得（前後空白をトリム）する。
    要素が None の場合は None を返す。
    """
    if elem is None:
        return None
    if elem.text is None:
        return None
    txt: str = elem.text.strip()
    return txt


def get_iter_text(elem: ET.Element | None) -> str | None:
    """
    子孫要素を含めた結合テキスト（<br/> 等の混在に対応）。
    """
    if elem is None:
        return None
    text: str = "".join(elem.itertext())
    if not text:
        return None
    # 連続空白を適度に畳み込み、前後をトリム
    text_trimmed: str = " ".join(text.split()).strip()
    return text_trimmed

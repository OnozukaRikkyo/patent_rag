from pathlib import Path

from model.patent import Application, Classifications, Description, Disclosure, Parties, Patent, Person, Publication


class OtherLoaders:
    """
    ST36やST96などの標準ローダではパースできない特殊なXMLに個別対応するためのクラスです。
    """

    def __init__(self):
        pass

    def load_JP2024524707A(self, path: Path) -> Patent:
        """
        XMLの中身がProxyErrorでパースできなかった公開番号「JP2024524707A」をロードします。
        PDFからコピペしてきたテキストを用いて、Patentオブジェクトを作成します。
        公開番号や請求項など、必要最低限の情報のみ作成します。
        """
        # 1. 公開情報
        publication = Publication(
            doc_number="2024524707",
            country="JP",
            kind="公開特許公報(A)",
            date="20240705",
        )
        # 2. 出願情報
        application = Application(doc_number="2024-502112", date=None)
        # 3.発明の名称
        title: str = "ビエッティ結晶性ジストロフィー治療のための遺伝子組換アデノ随伴ウイルスベクター"

        # 4.パーティ（出願人・代理人・発明者）
        applicants: list[Person] = []
        agents: list[Person] = []
        inventors: list[Person] = []
        parties = Parties(applicants=applicants, agents=agents, inventors=inventors)

        # 5.分類（IPC国際分類、FI国内分類）
        classifications = Classifications(
            ipc_main="",
            ipc_further=[],
            jp_main="",
            jp_further=[],
        )

        # 6.テーマコード
        theme_codes: list[str] = []

        # 7.Fターム
        f_terms: list[str] = []

        # 8.請求項
        claims: list[str] = [
            "【請求項１】　配列番号２～１７からなる配列群から選択され、かつヒトＣＹＰ４Ｖ２ポリペプチドをエンコードするヌクレオチド配列を有する、単離された核酸分子。",
            "【請求項２】　前記ヌクレオチド配列が、配列番号８、９、１５、１６及び１７から選択される、請求項１に記載の単離された核酸分子。",
            "【請求項３】　前記ヌクレオチド配列が、配列番号８又は配列番号１６である、請求項２に記載の単離された核酸分子。",
            "【請求項４】　ＣＹＰ４Ｖ２をエンコードするヌクレオチド配列の５’末端と機能的に連結されたプロモーターを更に有する、請求項１に記載の単離された核酸分子。",
            "【請求項５】　前記プロモーターがＣＡＧプロモーターである、請求項４に記載の単離された核酸分子。",
            "【請求項６】　ＣＹＰ４Ｖ２をエンコードするヌクレオチド配列の３’末端にポリアデニレーション配列を更に有する、請求項１に記載の単離された核酸分子。",
            "【請求項７】　前記ポリアデニレーション配列がウシ成長ホルモン（ｂＧＨ）ｐｏｌｙＡ、合成  ｐｏｌｙＡ（ＳＰＡ）、又は雑種ウイルス（ＳＶ４０）  ｐｏｌｙＡ、より好ましくはＳＶ４０  ｐｏｌｙＡである、請求項６に記載の単離された核酸分子。",
            "【請求項８】　ウッドチャック肝炎ウイルス転写後調整エレメント（ＷＰＲＥ）を更に有する、請求項１に記載の単離された核酸分子。",
            "【請求項９】　（ａ）又は（ｂ）を更に有する、請求項１に記載の単離された核酸分子。（ａ）配列番号１８～３４のいずれか一つのヌクレオチド配列、又は、（ｂ）配列番号１８～３４のいずれか一つに対する相同性が少なくとも８５％、少なくとも９０％、少なくとも９５％、少なくとも９６％、少なくとも９７％、少なくとも９８％、少なくとも９９％であるヌクレオチド配列。",
            "【請求項１０】　請求項１に記載の核酸分子を有する、組換ＡＡＶベクター。",
            "【請求項１１】　一個又は二個の逆位末端配列（ＩＴＲ）を有する、請求項１０に記載の組換ＡＡＶベクター。",
            "【請求項１２】　二個のＡＡＶ２  ＩＴＲを有する、請求項１１に記載の組換ＡＡＶベクター。",
            "【請求項１３】　ＡＡＶカプシドにパッケージングされた、請求項１０に記載の組換ＡＡＶベクターを有する、ウイルス粒子。",
            "【請求項１４】　前記ＡＡＶカプシドがＡＡＶ８カプシドである、請求項１３に記載のウイルス粒子。",
            "【請求項１５】　請求項１３に記載のウイルス粒子、及び医薬上許容可能な賦形剤を含む医薬組成物。",
            "【請求項１６】　ビエッティ結晶性ジストロフィー（ＢＣＤ）の治療用又は予防用の医薬品の製造における、請求項１０に記載の組替ＡＡＶベクターの使用。",
        ]

        # 9.明細書
        description = Description(
            technical_field=[],
            background_art=[],
            disclosure=Disclosure(tech_problem=[], tech_solution=[], advantageous_effects=[]),
            best_mode=[],
        )

        # 10.要約書
        abstract: str = (
            "【要約】"
            "【課題】ビエッティ結晶性ジストロフィー治療のための遺伝子組換アデノ随伴ウイルスベクターを提供することを課題とする。"
            "【解決手段】本発明では、所定の遺伝子発現抑制配列と関連付けた  ＣＹＰ４Ｖ２をエンコードしたコドン最適化配列から成る組換アデノ随伴ベクター、及び、ビエッティ結晶性ジストロフィー  （ＢＣＤ）の治療におけるこれの使用を提供する。"
        )

        return Patent(
            path=str(path),
            publication=publication,
            application=application,
            invention_title=title,
            parties=parties,
            classifications=classifications,
            theme_codes=theme_codes,
            f_terms=f_terms,
            claims=claims,
            description=description,
            abstract=abstract,
        )

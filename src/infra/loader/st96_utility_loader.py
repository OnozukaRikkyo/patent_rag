import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from infra.loader.loader_utils import get_iter_text, get_text
from model.patent import Application, Classifications, Description, Disclosure, Parties, Patent, Person, Publication


class St96UtilityLoader:
    """
    ST96形式の実用新案（Utility）のXMLをロードして、Patentオブジェクトを生成するクラスです。
    """

    def __init__(self):
        """
        コンストラクタです。名前空間やパスなどを初期化します。
        """
        self.NS = {
            "jputl": "http://www.jpo.go.jp/standards/XMLSchema/ST96/JPUtility",
            "pat": "http://www.wipo.int/standards/XMLSchema/ST96/Patent",
            "com": "http://www.wipo.int/standards/XMLSchema/ST96/Common",
            "jpcom": "http://www.jpo.go.jp/standards/XMLSchema/ST96/JPCommon",
        }
        self.current_path = Path("")

    def run(self, root: ET.Element, path: Optional[Path] = None) -> Patent:
        """
        実用新案（ST96 Utility Model 形式）XMLをパースする。
        ST96形式の特許XMLと似ているが、わりと違うので、別クラスで処理する。
        """
        # デバッグ用
        if path:
            self.current_path = path

        # 書誌事項
        bib = root.find("./jputl:RegisteredUtilityModelPublicationBibliographicData", self.NS)
        if bib is None:
            raise ValueError("bib がありません。")

        # 1.公開情報
        publication: Publication = self._load_publication_ref(bib)

        # 2.出願情報
        application: Application = self._load_application_ref(bib)

        # 3.発明の名称
        title: str = self._load_title(bib)

        # 4.パーティ（出願人・代理人・発明者）
        parties: Parties = self._load_parties(bib)

        # 5.分類（IPC国際分類、FI国内分類）
        classifications: Classifications = self._load_classifications(bib)

        # 6.テーマコード
        theme_codes: list[str] = []  # 無いっぽい（4件で確認済）
        # 7.Fターム
        f_terms: list[str] = []  # 無いっぽい（4件で確認済）

        # 8.請求項
        claims: list[str] = self._load_claims(root)

        # 9.明細書
        description: Description = self._load_description(root)

        # 10.要約書
        abstract: str = self._load_abstract(root)

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

    def _load_publication_ref(self, bib: ET.Element) -> Publication:
        """
        公開情報（publication reference）をパースする。
        """
        pub_id = bib.find("./jputl:UtilityModelPublicationIdentification", self.NS)
        if pub_id is None:
            raise ValueError("公開情報 がありません。")

        doc_number = get_text(pub_id.find("./pat:PublicationNumber", self.NS))
        if doc_number is None:
            raise ValueError("公開番号 がありません。IDなので必須です。")

        publication = Publication(
            doc_number=doc_number,
            country=get_text(pub_id.find("./com:IPOfficeCode", self.NS)),
            kind=None,
            date=get_text(pub_id.find("./com:PublicationDate", self.NS)),
        )
        return publication

    def _load_application_ref(self, bib: ET.Element) -> Application:
        """
        出願情報（application reference）をパースする。
        """
        app_id = bib.find("./jputl:ApplicationIdentification", self.NS)
        if app_id is None:
            raise ValueError("出願情報 がありません。")

        doc_number = get_text(app_id.find("./com:ApplicationNumber/com:ApplicationNumberText", self.NS))
        if doc_number is None:
            raise ValueError("出願番号 がありません。")  # 無くても問題ないかも

        application = Application(
            doc_number=doc_number,
            date=get_text(app_id.find("./pat:FilingDate", self.NS)),
        )
        return application

    def _load_title(self, bib: ET.Element) -> str:
        """
        発明の名称（invention title）を抽出する。
        """
        title_elem = bib.find("./pat:InventionTitle", self.NS)
        title = get_text(title_elem)
        if title is None:
            raise ValueError("発明の名称 がありません。")
        return title

    def _load_parties(self, bib: ET.Element) -> Parties:
        """
        <parties> から出願人・代理人・発明者を抽出する。
        """
        parties = Parties(applicants=[], agents=[], inventors=[])

        # 出願人（Applicants）
        for app in bib.findall(".//jputl:Applicant", self.NS):
            name = get_text(app.find("./jpcom:Contact/com:Name/com:EntityName", self.NS))
            if name is None:
                raise ValueError("<name> は必須です")
            regi = get_text(app.find("./com:PartyIdentifier", self.NS))
            addr = get_text(app.find("./jpcom:Contact/com:PostalAddressBag/com:PostalAddress/com:PostalAddressText", self.NS))
            parties.applicants.append(Person(name=name, registered_number=regi, address=addr))

        # 代理人（Agents, Practitioners）
        for agent in bib.findall(".//jputl:RegisteredPractitioner", self.NS):
            name = get_text(agent.find("./jpcom:Contact/com:Name/com:EntityName", self.NS))
            if name is None:
                raise ValueError("<name> は必須です。")
            regi = get_text(agent.find("./pat:RegisteredPractitionerRegistrationNumber", self.NS))
            parties.agents.append(Person(name=name, registered_number=regi, address=None))

        # 発明者（Inventors）
        for inv in bib.findall(".//jputl:Inventor", self.NS):
            name = get_text(inv.find("./jpcom:Contact/com:Name/com:EntityName", self.NS))
            if name is None:
                raise ValueError("<name> は必須です。")
            addr = get_text(inv.find("./jpcom:Contact/com:PostalAddressBag/com:PostalAddress/com:PostalAddressText", self.NS))
            parties.inventors.append(Person(name=name, registered_number=None, address=addr))

        return parties

    def _load_classifications(self, bib: ET.Element) -> Classifications:
        """
        特許分類（IPC、FI/国内分類）を抽出し、ラップして返す。
        """
        # IPC国際分類
        ipc_main = get_text(bib.find("./jputl:IPCClassification/pat:MainClassification", self.NS))
        if ipc_main is None:
            raise ValueError("<ipc_main> は必須です。")

        ipc_further = []
        for e in bib.findall("./jputl:IPCClassification/pat:FurtherClassification", self.NS):
            text = get_text(e)
            if text:
                ipc_further.append(text)

        # FI国内分類
        jp_main = get_text(bib.find("./jputl:NationalClassification/jputl:MainNationalClassification/pat:PatentClassificationText", self.NS))
        if jp_main is None:
            raise ValueError("<jp_main> は必須です。")

        jp_further = []
        for e in bib.findall("./jputl:NationalClassification/jputl:FurtherNationalClassification/pat:PatentClassificationText", self.NS):
            text = get_text(e)
            if text:
                jp_further.append(text)

        classifications = Classifications(ipc_main=ipc_main, ipc_further=ipc_further, jp_main=jp_main, jp_further=jp_further)
        return classifications

    def _load_claims(self, root: ET.Element) -> list[str]:
        """
        請求項（クレーム）を抽出する。
        """
        # 1. 初回出願
        claims = root.findall(".//pat:Claims/pat:Claim", self.NS)

        # 2. 修正（Amendment）
        amendments = root.findall(".//jputl:WrittenAmendmentBag/jputl:WrittenAmendment", self.NS)
        if amendments:
            for amendment in amendments:
                tmp_claims = amendment.findall("./jputl:AmendmentsBag//jputl:AmendmentContentsBag//pat:Claim", self.NS)
                if tmp_claims:
                    claims = tmp_claims # 最新に上書き（XMLは旧→新の順序、末尾が最新と仮定）

        if not claims:
            raise ValueError("請求項（初回出願、アメンドメント）がありません。")

        claim_texts = []
        for e in claims:
            text = get_iter_text(e.find("./pat:ClaimText", self.NS))
            if text:
                number = get_text(e.find("./pat:ClaimNumber", self.NS))
                header = f"【請求項{number}】" if number else ""
                claim = header + text
                claim_texts.append(claim)
            else:
                raise ValueError(f"請求項の本文 がありません。path: {self.current_path}")

        return claim_texts

    def _load_description(self, root: ET.Element) -> Description:
        """
        明細書（description）の各パラグラフの本文を抽出する。
        """
        node = root.find("./jputl:Description", self.NS)
        if node is None:
            raise ValueError(f"Description がありません。path: {self.current_path}")

        # 【技術分野】
        technical_field = []
        for p in node.findall(".//pat:TechnicalField/com:P", self.NS):
            text = get_iter_text(p)
            if text:
                technical_field.append(text)

        # 【背景技術】
        background_art = []
        for p in node.findall(".//pat:BackgroundArt/com:P", self.NS):
            text = get_iter_text(p)
            if text:
                background_art.append(text)

        # 【考案が解決しようとする課題】
        tech_problem = []
        for p in node.findall(".//pat:InventionSummary/pat:TechnicalProblem/com:P", self.NS):
            text = get_iter_text(p)
            if text:
                tech_problem.append(text)

        # 【課題を解決するための手段】
        tech_solution = []
        for p in node.findall(".//pat:InventionSummary/pat:TechnicalSolution/com:P", self.NS):
            text = get_iter_text(p)
            if text:
                tech_solution.append(text)

        # 【効果】
        advantageous_effects = []
        for p in node.findall(".//pat:InventionSummary/pat:AdvantageousEffects/com:P", self.NS):
            text = get_iter_text(p)
            if text:
                advantageous_effects.append(text)

        # 【考案の概要】
        disclosure = Disclosure(
            tech_problem=tech_problem,
            tech_solution=tech_solution,
            advantageous_effects=advantageous_effects,
        )

        # 実施形態
        best_mode = []
        for p in node.findall(".//pat:EmbodimentDescription/com:P", self.NS):
            text = get_iter_text(p)
            if text:
                best_mode.append(text)

        # 明細書
        description = Description(
            technical_field=technical_field,
            background_art=background_art,
            disclosure=disclosure,
            best_mode=best_mode,
        )
        return description

    def _load_abstract(self, root: ET.Element) -> str:
        """
        要約書（abstract）を抽出する。
        """
        abstract_elem = root.find("./pat:Abstract", self.NS)
        if abstract_elem is None:
            # raise ValueError("要約書 がありません。") 
            return ""

        abstract = get_iter_text(abstract_elem)
        if not abstract:
            # raise ValueError("要約書 の本文がありません。")
            return ""

        return abstract

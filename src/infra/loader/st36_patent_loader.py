import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

from infra.loader.loader_utils import get_iter_text, get_text
from model.patent import Application, Classifications, Description, Disclosure, Parties, Patent, Person, Publication


class St36PatentLoader:
    """
    ST36形式の特許XMLをロードして、Patentオブジェクトを生成するクラスです。
    """

    def __init__(self):
        """
        コンストラクタです。名前空間やパスなどを初期化します。
        """
        self.NS = {"jp": "http://www.jpo.go.jp"}
        self.current_path = Path("")

    def run(self, root: ET.Element, path: Optional[Path] = None) -> Patent:
        """
        JPOの標準的なXMLをパースして、Patentオブジェクトを生成する。
        """
        # デバッグ用
        if path:
            self.current_path = path

        # 書誌事項
        bib: ET.Element | None = root.find("./bibliographic-data", self.NS)
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
        theme_codes: list[str] = self._load_theme_code(bib)

        # 7.Fターム
        f_terms: list[str] = self._load_f_terms(bib)

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
        doc_id = bib.find("./publication-reference/document-id")
        if doc_id is None:
            raise ValueError("公開情報 がありません。")

        doc_number = get_text(doc_id.find("./doc-number"))
        country = get_text(doc_id.find("./country"))
        kind = get_text(doc_id.find("./kind"))
        date = get_text(doc_id.find("./date"))

        if doc_number is None:
            raise ValueError("公開番号 がありません。IDなので必須です。")

        return Publication(
            doc_number=doc_number,
            country=country,
            kind=kind,
            date=date,
        )

    def _load_application_ref(self, bib: ET.Element) -> Application:
        """
        出願情報（application reference）をパースする。
        """
        doc_id = bib.find("./application-reference/document-id")
        if doc_id is None:
            raise ValueError("出願情報 がありません。")

        doc_number = get_text(doc_id.find("./doc-number"))
        if doc_number is None:
            raise ValueError("出願番号 がありません。")  # 無くても問題ないかも

        date = get_text(doc_id.find("./date"))

        return Application(doc_number=doc_number, date=date)

    def _load_title(self, bib: ET.Element) -> str:
        """
        発明の名称（invention title）を抽出する。
        """
        title_elem = bib.find("./invention-title")
        title: str | None = get_text(title_elem)
        if title is None:
            raise ValueError("発明の名称 がありません。")
        return title

    def _load_parties(self, bib: ET.Element) -> Parties:
        """
        <parties> から出願人・代理人・発明者を抽出する。
        """
        parties = Parties(applicants=[], agents=[], inventors=[])

        # 出願人（Applicant）
        for app in bib.findall(".//jp:applicants-agents-article/jp:applicants-agents/applicant", self.NS):  # NSないとエラー
            name = get_text(app.find("./addressbook/name"))
            regi = get_text(app.find("./addressbook/registered-number"))
            addr = get_text(app.find("./addressbook/address/text"))
            if name is None:
                raise ValueError("出願人名 がありません。")
            applicant = Person(name=name, registered_number=regi, address=addr)
            parties.applicants.append(applicant)

        # 代理人（Agent）
        for age in bib.findall(".//jp:applicants-agents-article/jp:applicants-agents/agent", self.NS):  # NSないとエラー
            name = get_text(age.find("./addressbook/name"))
            regi = get_text(age.find("./addressbook/registered-number"))
            if name is None:
                raise ValueError("代理人名 がありません。")
            agent = Person(name=name, registered_number=regi, address=None)
            parties.agents.append(agent)

        # 発明者（Inventor）
        for inv in bib.findall(".//inventors/inventor"):
            name = get_text(inv.find("./addressbook/name"))
            addr = get_text(inv.find("./addressbook/address/text"))
            if name is None:
                raise ValueError("発明者名 がありません。")
            inventor = Person(name=name, registered_number=None, address=addr)
            parties.inventors.append(inventor)

        return parties

    def _load_classifications(self, bib: ET.Element) -> Classifications:
        """
        IPC分類とFI国内分類を抽出し、ラップして返す。
        """
        ipc_main = get_text(bib.find("./classification-ipc/main-clsf"))
        if ipc_main is None:
            raise ValueError("XML に <classification-ipc>/<main-clsf> が見つかりません。")

        ipc_further = []
        for e in bib.findall("./classification-ipc/further-clsf"):
            t = get_text(e)
            if t:
                ipc_further.append(t)  # None除去

        jp_main = get_text(bib.find("./classification-national/main-clsf"))
        if jp_main is None:
            raise ValueError("XML に <classification-national>/<main-clsf> が見つかりません。")

        jp_further = []
        for e in bib.findall("./classification-national/further-clsf"):
            t = get_text(e)
            if t:
                jp_further.append(t)  # None除去

        return Classifications(ipc_main=ipc_main, ipc_further=ipc_further, jp_main=jp_main, jp_further=jp_further)

    def _load_theme_code(self, bib: ET.Element) -> list[str]:
        """
        テーマコード（Fタームのグループ）を抽出する。
        """
        theme_codes = []
        theme_code_info = bib.find(".//jp:theme-code-info", self.NS)

        if theme_code_info is None:
            return theme_codes  # 古い形式では存在しない（2010年以前?）

        for e in theme_code_info.findall("./jp:theme-code", self.NS):
            t = get_text(e)
            if t:
                theme_codes.append(t)  # None除去

        return theme_codes

    def _load_f_terms(self, bib: ET.Element) -> list[str]:
        """
        Fターム を抽出する。
        """
        terms = []
        for e in bib.findall(".//jp:f-term-info/jp:f-term", self.NS):  # NSないとエラー
            t = get_text(e)
            if t:
                terms.append(t)  # None除去
        return terms

    def _load_claims(self, root: ET.Element) -> list[str]:
        """
        請求項（クレーム）を抽出する。
        """
        # 1. 初回出願
        claims = root.find("./claims")
        if claims is None:
            raise ValueError("請求項（初回出願）がありません。")

        # 2. 修正（Amendment）
        amended_claims_list = root.findall(".//jp:written-amendment-group//jp:contents-of-amendment//claims", self.NS)
        if amended_claims_list:
            for amended_claims in amended_claims_list:
                claims = amended_claims  # 最新に上書き（XMLは旧→新の順序、末尾が最新と仮定）

        if claims is None:
            raise ValueError("請求項（初回出願と修正の両方）がありません。")

        claim_texts = []
        for claim in claims.findall("./claim", self.NS):
            num = claim.get("num")
            claim_text = claim.find("./claim-text")
            if claim_text is None:
                raise ValueError("<claim-text> がありません。")

            # Case1. テキスト（通常、9割）
            text = get_iter_text(claim_text)
            if text:
                header = f"【請求項{num}】"
                claim_texts.append(header + text)
                continue

            # Case2. 画像
            # 直下の要素（例：JP2013543684A）
            img = claim_text.find("./img")
            if img is None:
                # すべての子要素（例：表＞画像、数式＞画像）
                img = claim_text.find(".//img")
            if img is not None:  # if img: だと何故かダメ
                header = f"【請求項{num}】"
                claim_texts.append(header + "[画像データ]")  # TODO: OCRでテキスト化してもよい
                continue

            # 上記の対策をしてもダメなら、本当に空っぽと判断
            if not text:
                continue

            # 上記以外は未確認ケースとしてエラーを出す
            raise ValueError("請求項の本文 がありません。")

        return claim_texts

    def _load_description(self, root: ET.Element) -> Description:
        """
        明細書（description）の各パラグラフの本文を抽出する。
        """
        # 1. 初回出願
        description: ET.Element | None = root.find("./description")

        # 2. 修正（Amendment）
        amended_descriptions: list[ET.Element] = root.findall(".//jp:written-amendment-group//jp:contents-of-amendment//description", self.NS)
        if amended_descriptions:
            for amended_description in amended_descriptions:
                description = amended_description  # 最新に上書き（XMLは旧→新の順序、末尾が最新と仮定）

        if description is None:
            raise ValueError("明細書 がありません。")

        # 【技術分野】<technical-field>
        technical_field_paragraphs: list[str] = self.__load_tech_field(description)

        # 【背景技術】<background-art>
        background_art_paragraphs: list[str] = self.__load_background_art(description)

        # 【発明の開示】<disclosure>
        disclosure: Disclosure = self.__load_disclosure(description)

        # 【発明を実施するための形態】<best-mode>
        best_mode_paragraphs: list[str] = self.__load_best_mode(description)

        return Description(
            technical_field=technical_field_paragraphs,
            background_art=background_art_paragraphs,
            disclosure=disclosure,
            best_mode=best_mode_paragraphs,
        )

    def __load_tech_field(self, description: ET.Element) -> list[str]:
        """
        【技術分野】<technical-field> をパースする。
        """
        paragraphs: list[str] = []
        technical_field = description.find("./technical-field")
        if technical_field is None:
            # raise ValueError("XML に <technical-field> が見つかりません。")
            pass  # ない場合もある
        else:
            for p in technical_field.iterfind(".//p"):
                text = get_iter_text(p)
                if text:
                    paragraphs.append(text)
        return paragraphs

    def __load_background_art(self, description: ET.Element) -> list[str]:
        """
        【背景技術】<background-art> をパースする。
        """
        paragraphs: list[str] = []
        background_art = description.find("./background-art")
        if background_art is None:
            # raise ValueError("XML に <background-art> が見つかりません。")
            pass  # 稀にない
        else:
            for p in background_art.iterfind(".//p"):
                text = get_iter_text(p)
                if text:
                    paragraphs.append(text)
        return paragraphs

    def __load_disclosure(self, description: ET.Element) -> Disclosure:
        """
        【発明の開示】<disclosure> をパースして Disclosure に変換する。
        """
        disclosure = description.find("./disclosure", self.NS)
        if disclosure is None:
            disclosure = description.find("./summary-of-invention")  # 旧形式（2013以前？）
            if disclosure is None:
                # raise ValueError("XML に <disclosure> または <summary-of-invention> が見つかりません。")
                return Disclosure(tech_problem=[], tech_solution=[], advantageous_effects=[])  # ごく稀にない（best-mode側に記載されているなど）

        # 【発明が解決しようとする課題】<tech-problem>
        tech_problem_paragraphs: list[str] = []
        tech_problem = disclosure.find("./tech-problem")
        if tech_problem is None:
            # raise ValueError("XML に <tech-problem> が見つかりません。")
            pass  # ない場合もある
        else:
            for p in tech_problem.iterfind(".//p"):
                text = get_iter_text(p)
                if text:
                    tech_problem_paragraphs.append(text)

        # 【課題を解決するための手段】<tech-solution>
        tech_solution_paragraphs: list[str] = []
        tech_solution = disclosure.find("./tech-solution")
        if tech_solution is None:
            # raise ValueError("XML に <tech-solution> が見つかりません。")
            pass  # ない場合もある
        else:
            for p in tech_solution.iterfind(".//p"):
                text = get_iter_text(p)
                if text:
                    tech_solution_paragraphs.append(text)

        # 【発明の効果】<advantageous-effects>
        advantageous_effects_paragraphs: list[str] = []
        advantageous_effects = disclosure.find("./advantageous-effects")
        if advantageous_effects is None:
            # raise ValueError("XML に <advantageous-effects> が見つかりません。")
            pass  # ない場合もある
        else:
            for p in advantageous_effects.iterfind(".//p"):
                text = get_iter_text(p)
                if text:
                    advantageous_effects_paragraphs.append(text)

        return Disclosure(
            tech_problem=tech_problem_paragraphs,
            tech_solution=tech_solution_paragraphs,
            advantageous_effects=advantageous_effects_paragraphs,
        )

    def __load_best_mode(self, description: ET.Element) -> list[str]:
        """
        【発明を実施するための形態】<best-mode> をパースする。
        """
        paragraphs: list[str] = []
        best_mode = description.find("./best-mode")

        if best_mode is None:
            best_mode = description.find("./description-of-embodiments")  # 旧形式（2013以前？）
            if best_mode is None:
                best_mode = description.find("./heading")  # タグで囲まれていないものがある。うまく取得できない。
                if best_mode is None:
                    # raise ValueError("XML に <best-mode> または <description-of-embodiments> が見つかりません。")
                    return paragraphs  # 極まれにない（tech-solution側に記載されているなど）

        for p in best_mode.iterfind(".//p"):
            text = get_iter_text(p)
            if text:
                paragraphs.append(text)

        return paragraphs

    def _load_abstract(self, root: ET.Element) -> str:
        """
        要約書（abstract）を抽出する。
        """
        abstract_elem = root.find("./abstract")
        if abstract_elem is None:
            # raise ValueError("XML に <abstract> が見つかりません。")
            return ""  # Bで終わる古い特許に要約文がないケースあり

        texts = []
        for p in abstract_elem.iterfind(".//p"):
            text = get_iter_text(p)
            if text:
                texts.append(text)

        abstract = "\n".join(texts)
        if not abstract:
            # raise ValueError("要約書 の本文がありません。") 
            # ごく稀にない。
            # 例：JP2014502745A（GooglePatentでPDFを確認したら要約が空欄だった）
            return ""

        return abstract

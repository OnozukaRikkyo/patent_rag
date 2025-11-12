from dataclasses import dataclass
from typing import List, Optional

from langchain_core.documents import Document


@dataclass
class Publication:
    """
    公開番号、出願番号
    XMLの<publication-reference>に対応する。
    """

    doc_number: str
    country: Optional[str] = None
    kind: Optional[str] = None
    date: Optional[str] = None

@dataclass
class Application:
    """
    出願番号、出願日
    XMLの<application-reference>に対応する。
    """
    doc_number: str
    date: Optional[str] = None


@dataclass
class Person:
    """
    人物（出願人、代理人、発明者）を表す。
    XMLの<applicants>、<agents>、<inventors>に対応する。
    """

    name: str
    registered_number: Optional[str] = None
    address: Optional[str] = None


@dataclass
class Parties:
    """
    出願人、代理人、発明者の集合（パーティ）を表す。
    XMLの<parties>に対応する。
    """

    applicants: List[Person]
    agents: List[Person]
    inventors: List[Person]


@dataclass
class Disclosure:
    """
    明細書の【発明の開示】
    """

    tech_problem: List[str]
    tech_solution: List[str]
    advantageous_effects: List[str]


@dataclass
class Description:
    """
    明細書の全文
    """

    technical_field: List[str]
    background_art: List[str]
    disclosure: Disclosure
    best_mode: List[str]


@dataclass
class Classifications:
    """
    特許分類（IPC分類、FI国内分類）を表すデータクラス
    """

    ipc_main: str
    ipc_further: List[str]
    jp_main: str
    jp_further: List[str]


@dataclass
class Patent:
    """
    特許（公開番号、発明の名称、出願人、Fターム、明細書、請求項など）
    """
    path: str
    publication: Publication
    application: Application
    invention_title: str
    parties: Parties
    classifications: Classifications
    theme_codes: List[str]
    f_terms: List[str]
    claims: List[str]
    description: Description
    abstract: str

    def to_str(self) -> str:
        """
        Patentオブジェクトから、特許文書全体を表す文字列に変換する。
        """
        patent_str = ""
        patent_str += f"【発明の名称】\n{self.invention_title}\n\n"
        patent_str += "【出願人】\n"
        for applicant in self.parties.applicants:
            patent_str += f"- {applicant.name}\n"
        patent_str += "\n"
        patent_str += "【発明者】\n"
        for inventor in self.parties.inventors:
            patent_str += f"- {inventor.name}\n"
        patent_str += "\n"
        patent_str += f"【要約】\n{self.abstract}\n\n"
        patent_str += "【請求項】\n"
        for claim in self.claims:
            patent_str += f"{claim}\n"
        patent_str += "\n"
        patent_str += "【明細書】\n"
        patent_str += "（技術分野）\n"
        for field in self.description.technical_field:
            patent_str += f"{field}\n"
        patent_str += "\n（背景技術）\n"
        for art in self.description.background_art:
            patent_str += f"{art}\n"
        patent_str += "\n（発明の開示）\n"
        patent_str += "（課題）\n"
        for problem in self.description.disclosure.tech_problem:
            patent_str += f"{problem}\n"
        patent_str += "\n（解決手段）\n"
        for solution in self.description.disclosure.tech_solution:
            patent_str += f"{solution}\n"
        patent_str += "\n（効果）\n"
        for effect in self.description.disclosure.advantageous_effects:
            patent_str += f"{effect}\n"
        patent_str += "\n（実施形態）\n"
        for mode in self.description.best_mode:
            patent_str += f"{mode}\n"
    
        return patent_str
    

    def to_doc(self) -> Document:
        """
        Patentを、langchainのDocumentに変換する。
        """
        page_content = ""
        page_content += f"{'\n'.join(self.claims)}\n" # 請求項
        page_content += f"{self.abstract}\n"  # 要約
        # TODO：ベクトル化の対象とするテキストをちゃんと考える。

        doc = Document(
            page_content=page_content,
            metadata={
                # TODO: 必要なメタデータをちゃんと考える。
                # TODO: Listやクラス型が渡せないので、うまく文字列に変換する必要がある。
                "path": self.path,
                "publication_number": self.publication.doc_number,
                "application_number": self.application.doc_number,
                "invention_title": self.invention_title,
                "applicants": ",".join([applicant.name for applicant in self.parties.applicants]),
                "inventors": ",".join([inventor.name for inventor in self.parties.inventors]),
                "ipc_main": self.classifications.ipc_main,
                "ipc_further": ",".join(self.classifications.ipc_further),
                "jp_main": self.classifications.jp_main,
                "jp_further": ",".join(self.classifications.jp_further),
                "theme_codes": ",".join(self.theme_codes),
                "f_terms": ",".join(self.f_terms),
                "claims": "\n\n".join(self.claims),
                "description_technical_field": "\n\n".join(self.description.technical_field),
                "description_background_art": "\n\n".join(self.description.background_art),
                "description_technical_problem": "\n\n".join(self.description.disclosure.tech_problem),
                "description_technical_solution": "\n\n".join(self.description.disclosure.tech_solution),
                "description_advantageous_effects": "\n\n".join(self.description.disclosure.advantageous_effects),
                "description_best_mode": "\n\n".join(self.description.best_mode),
            },
        )
        return doc

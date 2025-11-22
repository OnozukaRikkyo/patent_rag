# ベースイメージ
FROM python:3.11-slim

ENV PIP_NO_CACHE_DIR=1

# 作業ディレクトリ
WORKDIR /app

# 必要ツール
RUN apt-get update && apt-get install -y curl build-essential && rm -rf /var/lib/apt/lists/*

# uv をインストール（最新）
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# uv のパスを通す
ENV PATH="/root/.local/bin:${PATH}"

# プロジェクトの依存定義をコピー
COPY pyproject.toml uv.lock ./

# ★ ここを修正：Python 3.13 を明示して同期
RUN uv sync --python 3.13 --frozen

# ★ uv が作った .venv をデフォルトの Python として使う
ENV VIRTUAL_ENV=/app/.venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"

# アプリ本体をコピー
COPY . .

# Streamlit 設定
ENV PORT=8080
EXPOSE 8080

CMD ["streamlit", "run", "src/gui.py", "--server.port=8080", "--server.address=0.0.0.0"]

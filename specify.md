# KataraiEngine 仕様書

## 1. 概要

**アプリケーション名:** KataraiEngine

本ドキュメントは、複数のLLM（大規模言語モデル）プロバイダーとキャラクター設定を組み合わせて対話を実現するバックエンドエンジン「KataraiEngine」の仕様を定義します。
コアロジックをライブラリとして独立させ、HTTP API経由で利用可能にすることで、再利用性と保守性を高めます。

## 2. アーキテクチャ

### 2.1. 主要コンポーネント

本アプリケーションは、以下の主要な層で構成されます。

*   **コアロジック層 (`katarai_engine.core`):**
    *   **役割:** 設定ファイルの読み込み、パラメータのマージ、プロンプト生成、LLMプロバイダーとの通信、応答の整形など、チャット機能の中核的なロジックを担当します。
    *   **実装:** Pythonのパッケージとして実装され、関数やクラス群を提供します。他の層からライブラリとして利用可能です。
    *   **依存:** `PyYAML`, `python-dotenv`, 各LLMプロバイダーのSDK (`google-generativeai`, `anthropic` など)。

*   **HTTPインターフェース層 (`katarai_engine.interfaces.api`):**
    *   **役割:** 外部からのHTTPリクエストを受け付け、リクエスト内容を解析し、コアロジック層を呼び出します。コアロジック層からの結果（データやストリーム）を適切なHTTPレスポンス（JSON、Server-Sent Events）に変換してクライアントに返却します。
    *   **実装:** Webフレームワーク（例: FastAPI, Flask）を用いて実装されます。（**注:** この層は現時点では未実装です。）
    *   **依存:** `katarai_engine.core`, Webフレームワーク。

### 2.2. フォルダ構成

```
KataraiEngine/
├── .env                 # APIキーなどの機密情報を格納 (Git管理外)
├── .gitignore           # Gitで追跡しないファイルを指定
├── LICENSE              # ライセンスファイル
├── README.md            # プロジェクトの説明
├── requirements.txt     # Python依存ライブラリ一覧
├── specify.md           # ★この仕様書ファイル
│
├── config/              # 設定ファイル (YAML) を格納
│   ├── characters/      # キャラクター定義
│   │   ├── *.yaml
│   │   └── .gitkeep
│   ├── personalities/   # 個性テンプレート
│   │   ├── *.yaml
│   │   └── .gitkeep
│   └── providers/       # LLMプロバイダー設定
│       ├── *.yaml
│       └── .gitkeep
│
├── katarai_engine/      # Pythonソースコードのルートパッケージ
│   ├── __init__.py
│   │
│   ├── core/            # コアロジック層
│   │   ├── __init__.py
│   │   ├── chat.py        # チャット実行の中核関数 (execute_chat_streamなど)
│   │   ├── config.py      # 設定ファイルの読み込み、検証、マージ
│   │   ├── models.py      # データ構造定義 (Pydanticモデルなど)
│   │   ├── prompt.py      # LLMプロンプト生成ロジック
│   │   └── providers/     # LLMプロバイダー通信
│   │       ├── __init__.py
│   │       ├── base.py      # プロバイダ共通インターフェース/基底クラス
│   │       ├── gemini.py    # Geminiクライアント実装
│   │       ├── anthropic.py # Anthropic (Claude) クライアント実装
│   │       └── ollama.py    # (将来用) Ollamaクライアント実装
│   │
│   └── interfaces/      # (将来用) 外部インターフェース層
│       ├── __init__.py
│       └── api/         # (将来用) HTTP API実装
│           └── ...
│
├── tests/               # テストコード
│   ├── __init__.py
│   ├── core/            # コアロジック層のテスト
│   │   ├── __init__.py
│   │   └── .gitkeep     # (例: test_config.py, test_chat.py)
│   └── interfaces/      # (将来用) インターフェース層のテスト
│       └── ...
│
└── # 疎通確認用スクリプト (開発用、将来的には削除またはtests/へ移動)
    ├── test_gemini.py
    └── test_claude.py
```

## 3. API仕様 (HTTPインターフェース層)

**注:** このセクションは将来実装されるHTTPインターフェース層の**設計案**です。

### 3.1. キャラクター一覧取得 API (`GET /api/characters`)

*   **目的:** 利用可能なキャラクターの一覧情報を取得します。
*   **レスポンス (JSON):**
    *   **成功時 (200 OK):** キャラクター情報の配列。
        ```json
        [
          {
            "id": "string", // キャラクターID (config/characters/ のファイル名)
            "name": "string", // キャラクター名
            "description": "string", // キャラクターの説明
            "llm_provider": "string", // 使用するLLMプロバイダー名
            "personality": "string" // 使用する個性テンプレート名
          },
          // ...
        ]
        ```
    *   **失敗時:** 標準的なHTTPエラーレスポンス (例: 500 Internal Server Error)。

### 3.2. チャット実行 API (`POST /api/chat`)

*   **目的:** 指定したキャラクターと対話し、応答をストリーミング形式で取得します。
*   **リクエストボディ (JSON):**
    ```json
    {
      "characterId": "string", // 必須: 対話するキャラクターのID
      "prompt": "string", // 必須: ユーザーからの最新のメッセージ
      "history": [ // オプション: 会話履歴 (古い順)
        { "role": "user", "content": "string" },
        { "role": "assistant", "content": "string" }
      ],
      "requestId": "string | null" // オプション: クライアント側で生成したリクエストID
    }
    ```
*   **レスポンス:**
    *   **成功時 (200 OK):**
        *   `Content-Type: text/event-stream; charset=utf-8`
        *   Server-Sent Events (SSE) 形式で応答チャンクをストリーミング。
        *   **イベント: `request_id`** (接続確立直後)
            ```sse
            event: request_id
            data: {"requestId": "server-generated-or-provided-id"}
            ```
        *   **イベント: `text_chunk`** (LLMからの応答チャンクごと)
            ```sse
            event: text_chunk
            data: {"text": "LLMからの応答の一部", "requestId": "..."}
            ```
        *   **イベント: `error`** (ストリーミング中のエラー発生時)
            ```sse
            event: error
            data: {"error": "エラーメッセージ", "requestId": "..."}
            ```
        *   **イベント: `end`** (ストリーム終了時)
            ```sse
            event: end
            data: {"requestId": "..."}
            ```
    *   **失敗時 (非ストリーミングエラー):**
        *   **400 Bad Request (JSON):** リクエスト形式が不正 (必須パラメータ欠如など)。
            ```json
            { "error": "詳細なエラーメッセージ", "requestId": "..." }
            ```
        *   **404 Not Found (JSON):** 指定された `characterId` が存在しない。
            ```json
            { "error": "キャラクターが見つかりません", "requestId": "..." }
            ```
        *   **500 Internal Server Error (JSON):** サーバー内部で予期せぬエラーが発生。
            ```json
            { "error": "内部サーバーエラーが発生しました", "requestId": "..." }
            ```

## 4. コアロジック層 (`katarai_engine.core`)

### 4.1. 設定ファイル (`config/`)

*   **形式:** YAML
*   **文字コード:** UTF-8
*   **構造:**
    *   `config/providers/{provider_name}.yaml`: LLMプロバイダー固有の設定。
    *   `config/personalities/{personality_name}.yaml`: キャラクターの個性（システムプロンプトなど）を定義。
    *   `config/characters/{character_id}.yaml`: プロバイダーと個性を組み合わせ、最終的なキャラクターを定義。

### 4.2. 設定ファイルのスキーマと詳細

#### 4.2.1. プロバイダー設定 (`config/providers/{provider_name}.yaml`)

```yaml
# 必須: プロバイダー名 (ファイル名と一致させる)
name: string

# 必須: プロバイダーのタイプ ("cloud" または "local")
type: string # "cloud" | "local"

# 必須 (type="cloud"): APIキーを読み込む環境変数名
api_key_env: string | null

# オプション (type="local"): ベースURLを読み込む環境変数名
base_url_env: string | null

# オプション: デフォルトで使用するモデル名
default_model: string | null

# オプション: プロバイダー固有のデフォルトパラメータ
# キー名は各LLM APIの仕様に準拠する
default_parameters:
  temperature: float | null
  max_tokens: int | null # 例: Claude
  maxOutputTokens: int | null # 例: Gemini
  top_p: float | null
  top_k: int | null
  # ... その他のプロバイダー固有パラメータ
```

#### 4.2.2. 個性設定 (`config/personalities/{personality_name}.yaml`)

```yaml
# 必須: 個性名 (ファイル名と一致させる)
name: string

# 必須: LLMに渡すシステムプロンプト (キャラクターの役割、口調、指示など)
system_prompt: string

# オプション: この個性に紐づくデフォルトパラメータ (プロバイダー設定を上書き)
# キー名は各LLM APIの仕様に準拠する
default_parameters:
  temperature: float | null
  max_tokens: int | null
  # ...
```

#### 4.2.3. キャラクター設定 (`config/characters/{character_id}.yaml`)

```yaml
# 必須: キャラクターID (ファイル名と一致させる)
id: string

# 必須: キャラクターの表示名
name: string

# オプション: キャラクターの説明
description: string | null

# 必須: 使用するLLMプロバイダー名 (config/providers/ のファイル名)
llm_provider: string

# 必須: 使用する個性名 (config/personalities/ のファイル名)
personality: string

# オプション: このキャラクター固有のパラメータ (個性、プロバイダー設定を上書き)
# キー名は各LLM APIの仕様に準拠する
parameters:
  model: string | null # 特定のモデルを使用する場合
  temperature: float | null
  max_tokens: int | null
  # ...
```

### 4.3. パラメータのマージルール

LLM呼び出し時の最終的なパラメータは、以下の優先順位でマージされます（後者が優先）。

1.  プロバイダー設定 (`providers/*.yaml`) の `default_parameters`
2.  個性設定 (`personalities/*.yaml`) の `default_parameters`
3.  キャラクター設定 (`characters/*.yaml`) の `parameters`

### 4.4. 主要な関数/クラス (予定)

*   **`katarai_engine.core.config`:**
    *   `load_character_config(character_id: str) -> CharacterConfig`: キャラクター設定を読み込み、関連するプロバイダー/個性設定も解決・マージして返す。
    *   `get_available_characters() -> list[CharacterInfo]`: 利用可能なキャラクター一覧情報を返す。
*   **`katarai_engine.core.models`:**
    *   Pydanticモデルなどを用いて、上記YAMLスキーマに対応するデータクラスを定義。バリデーションも行う。
*   **`katarai_engine.core.prompt`:**
    *   `build_llm_prompt(system_prompt: str, history: list[dict], user_prompt: str, provider_type: str) -> Any`: 各LLMプロバイダーのAPI形式に合わせたプロンプト（メッセージリストなど）を構築する。
*   **`katarai_engine.core.providers.base.LLMProvider`:**
    *   プロバイダー共通の抽象基底クラス。`generate_stream(...)` メソッドなどを定義。
*   **`katarai_engine.core.providers.{gemini|anthropic|...}`:**
    *   各プロバイダー固有の実装クラス。`LLMProvider` を継承。
*   **`katarai_engine.core.chat.execute_chat_stream(...)`:**
    *   チャット実行のエントリーポイント。設定読み込み、プロンプト生成、プロバイダー選択、LLM呼び出し、応答ストリーム生成を行う。

## 5. セットアップと依存関係

### 5.1. 必要なツール

*   Python (バージョン 3.9 以上推奨)
*   pip (Pythonパッケージインストーラ)
*   Git

### 5.2. 依存ライブラリ (`requirements.txt`)

```
PyYAML>=6.0
python-dotenv>=1.0.0
google-generativeai>=0.8.0 # Gemini API用
anthropic>=0.49.0         # Anthropic (Claude) API用
# --- Webフレームワーク (HTTPインターフェース層実装時) ---
# fastapi>=0.100.0
# uvicorn>=0.20.0
# pydantic>=2.0 # データモデル用 (FastAPI依存でもある)
# sse-starlette>=1.0 # Server-Sent Events用
```

### 5.3. 環境変数 (`.env` ファイル)

プロジェクトルートに `.env` ファイルを作成し、必要なAPIキーなどを記述します。このファイルは `.gitignore` によりGit管理対象外です。

```dotenv
# AI API Keys
GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY"
ANTHROPIC_API_KEY="YOUR_ANTHROPIC_API_KEY"

# (オプション) Ollama などローカルLLM用
# NEXT_PUBLIC_OLLAMA_BASE_URL="http://localhost:11434"
```

### 5.4. インストール

```bash
# 1. リポジトリをクローン (既に実施済み)
# git clone <repository_url>
# cd KataraiEngine

# 2. (推奨) 仮想環境を作成してアクティベート
python -m venv .venv
# Windows (PowerShell)
# .\.venv\Scripts\Activate.ps1
# Windows (cmd)
# .\.venv\Scripts\activate.bat
# Linux/macOS
# source .venv/bin/activate

# 3. 依存ライブラリをインストール
pip install -r requirements.txt
```

## 6. LLM疎通確認

開発初期段階で、主要なLLMプロバイダーとの接続を確認するために以下のスクリプトが作成されました。

*   `test_gemini.py`: Gemini APIとの疎通確認。
*   `test_claude.py`: Anthropic (Claude) APIとの疎通確認。

これらのスクリプトは、対応する設定ファイル (`config/providers/`, `config/personalities/`, `config/characters/` 内のテスト用ファイル) と `.env` ファイルのAPIキーが必要です。

**実行方法:**

```bash
# (仮想環境がアクティブな状態で)
python test_gemini.py
python test_claude.py
```

「疎通確認成功！」と表示されれば、接続は正常です。

## 7. 今後の開発タスク (例)

*   コアロジック層 (`katarai_engine.core`) の詳細実装。
    *   `models.py`: Pydanticモデル定義。
    *   `config.py`: 設定読み込み、マージ、バリデーション実装。
    *   `providers/base.py`, `providers/gemini.py`, `providers/anthropic.py`: プロバイダー抽象化と実装。
    *   `prompt.py`: プロンプト構築ロジック。
    *   `chat.py`: `execute_chat_stream` 関数の実装。
*   HTTPインターフェース層 (`katarai_engine.interfaces.api`) の実装 (FastAPI等を使用)。
*   単体テスト、結合テストの作成 (`tests/`)。
*   ロギング機構の導入。
*   エラーハンドリングの強化。
*   Ollama など他のプロバイダーへの対応。

### 新API設計案

#### 1. キャラクター一覧取得 API

*   **エンドポイント:** `/api/characters`
*   **HTTPメソッド:** `GET`
*   **目的:** 利用可能なキャラクターの一覧（名前、ID、簡単な説明など）を取得する。UIでキャラクター選択肢を表示するために使用します。
*   **レスポンス (JSON):**
    ```json
    [
      {
        "id": "hikari",
        "name": "ヒカリ",
        "description": "明るく親切なアシスタント。",
        "llm_provider": "gemini",
        "personality": "明るいアシスタント"
      },
      {
        "id": "kenji",
        "name": "ケンジ",
        "description": "コード分析が得意な専門家。",
        "llm_provider": "ollama",
        "personality": "専門的な分析官"
      },
      // ... 他のキャラクター
    ]
    ```

#### 2. チャット実行 API

*   **エンドポイント:** `/api/chat` （既存の `/api/chat` GET とは別の、新しいエンドポイントとして考えます）
*   **HTTPメソッド:** `POST`
*   **目的:** 指定したキャラクターと対話し、応答をストリーミング形式で受け取る。
*   **リクエストボディ (JSON):**
    ```json
    {
      "characterId": "hikari", // 対話したいキャラクターのID
      "prompt": "今日の天気について教えてください。", // ユーザーからのメッセージ
      "history": [ // (オプション) 会話履歴
        { "role": "user", "content": "こんにちは" },
        { "role": "assistant", "content": "こんにちは！何かお手伝いできることはありますか？" }
      ],
      "requestId": "client-generated-id-123" // (オプション) クライアント生成のリクエストID
    }
    ```
*   **レスポンス:**
    *   **成功時 (ステータスコード 200):**
        *   `Content-Type: text/event-stream`
        *   ストリーミング形式でデータが返される (既存の `/api/chat` GET と同様の形式を想定)。
            *   最初のチャンク: `{ "requestId": "<generated_or_provided_request_id>" }`
            *   後続のチャンク: `{ "text": "<llm_response_chunk>", "requestId": "<generated_or_provided_request_id>" }`
    *   **エラー時 (JSON):**
        *   キャラクターが見つからない (404): `{ "error": "指定されたキャラクターが見つかりません", "requestId": "..." }`
        *   リクエスト形式が不正 (400): `{ "error": "characterIdとpromptは必須です", "requestId": "..." }`
        *   内部サーバーエラー (500): `{ "error": "...", "requestId": "..." }`

---

### 設定ファイル構成案

これらのAPIを実現するために、以下のような設定ファイル構成を考えます (YAML形式を想定)。

1.  **LLMプロバイダー設定 (`config/providers/*.yaml`)**
    *   既存のファイルを流用または拡張し、LLMバックエンドごとの接続情報や基本パラメータを定義します。
    *   例: `config/providers/gemini.yaml`
        ```yaml
        name: "gemini"
        type: "cloud"
        # ... (APIキーの環境変数名など)
        default_model: "gemini-1.5-pro-latest"
        default_parameters:
          temperature: 0.7
          maxTokens: 2048
        ```
    *   例: `config/providers/ollama.yaml`
        ```yaml
        name: "ollama"
        type: "local"
        baseUrlEnv: "NEXT_PUBLIC_OLLAMA_BASE_URL"
        default_model: "phi-4-deepseek-R1K-RL-EZO-GGUF:Q4_K_S" # モデルをファイルで指定
        default_parameters:
          temperature: 0.6
        ```

2.  **個性テンプレート設定 (`config/personalities/*.yaml`)**
    *   キャラクターの性格や口調を定義するファイルを新規に作成します。
    *   例: `config/personalities/明るいアシスタント.yaml`
        ```yaml
        name: "明るいアシスタント"
        system_prompt: |
          あなたは「ヒカリ」という名前の、明るく親切なAIアシスタントです。
          ユーザーの質問には、常に丁寧で前向きな言葉遣いで答えてください。
          専門的な知識も持っていますが、難しい言葉は避けて分かりやすく説明します。
          絵文字を適度に使って、親しみやすい雰囲気を出してください。😄
        default_parameters: # 個性によってデフォルトパラメータを上書き
          temperature: 0.8
        ```
    *   例: `config/personalities/専門的な分析官.yaml`
        ```yaml
        name: "専門的な分析官"
        system_prompt: |
          あなたは「ケンジ」という名前の、冷静沈着な分析官AIです。
          提供された情報に基づいて、客観的かつ論理的に分析し、簡潔に結論を述べてください。
          感情的な表現や冗長な言い回しは避けてください。
          特にコードや技術的な内容に関する分析を得意とします。
        default_parameters:
          temperature: 0.2
        ```

3.  **キャラクター定義 (`config/characters/*.yaml`)**
    *   LLMプロバイダーと個性テンプレートを組み合わせてキャラクターを定義するファイルを新規に作成します。ファイル名がキャラクターID (`hikari.yaml` -> `id: "hikari"`) になります。
    *   例: `config/characters/hikari.yaml`
        ```yaml
        id: "hikari" # ファイル名と一致させる
        name: "ヒカリ"
        description: "明るく親切なアシスタント。"
        llm_provider: "gemini"        # 使用する config/providers/ のファイル名 (拡張子除く)
        personality: "明るいアシスタント" # 使用する config/personalities/ のファイル名 (拡張子除く)
        # 必要であれば、ここでさらにパラメータを上書き
        parameters:
          maxTokens: 1024
        ```
    *   例: `config/characters/kenji.yaml`
        ```yaml
        id: "kenji"
        name: "ケンジ"
        description: "コード分析が得意な専門家。"
        llm_provider: "ollama"
        personality: "専門的な分析官"
        parameters:
          # Ollamaの特定のモデルを使いたい場合はここで指定 (providerのデフォルトを上書き)
          # model: "codellama:7b"
          temperature: 0.1 # personalityのデフォルトをさらに上書き
        ```

---

### チャットAPI (`POST /api/chat`) の処理フロー案

1.  リクエストボディから `characterId`, `prompt`, `history` を受け取る。
2.  `config/characters/` ディレクトリから `{characterId}.yaml` ファイルを探して読み込む。見つからなければ404エラー。
3.  キャラクター定義ファイルから `llm_provider` と `personality` の名前を取得する。
4.  `config/providers/{llm_provider}.yaml` と `config/personalities/{personality}.yaml` を読み込む。
5.  個性テンプレートから `system_prompt` を取得する。
6.  LLMに渡す最終的なプロンプトを作成する。システムプロンプト、会話履歴 (`history`)、ユーザーの最新プロンプト (`prompt`) を組み合わせる。 (組み合わせ方はLLMの作法に合わせる)
7.  LLMのパラメータを決定する。`providers` → `personalities` → `characters` の順で設定をマージ（後から読み込んだもので上書き）し、最終的な `temperature`, `maxTokens` などを決定する。
8.  決定したパラメータとプロンプト、LLMプロバイダー設定（APIキーなど）を使って、対応するLLM APIを呼び出す。
9.  LLMからの応答をストリーミングで受け取り、`text/event-stream` 形式でクライアントに中継する。

---

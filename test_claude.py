import os
from anthropic import Anthropic, APIError, APIStatusError
from dotenv import load_dotenv
import yaml

def load_yaml(filepath):
    """YAMLファイルを読み込むヘルパー関数"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"エラー: 設定ファイルが見つかりません: {filepath}")
        return None
    except yaml.YAMLError as e:
        print(f"エラー: YAMLファイルの解析に失敗しました: {filepath}\n{e}")
        return None
    except Exception as e:
        print(f"エラー: 設定ファイルの読み込み中に予期せぬエラーが発生しました: {filepath}\n{e}")
        return None

def main():
    # 1. 環境変数の読み込み
    load_dotenv()
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        print("エラー: 環境変数 'ANTHROPIC_API_KEY' が設定されていません。")
        print(".env ファイルを確認してください。")
        return

    # 2. Anthropic クライアントの初期化
    try:
        client = Anthropic(
            # Defaults to os.environ.get("ANTHROPIC_API_KEY")
            api_key=api_key,
        )
    except Exception as e:
        print(f"エラー: Anthropic クライアントの初期化に失敗しました: {e}")
        return

    # 3. 設定ファイルの読み込み
    provider_config_path = "config/providers/anthropic.yaml"
    personality_config_path = "config/personalities/test_personality.yaml"

    provider_config = load_yaml(provider_config_path)
    personality_config = load_yaml(personality_config_path)

    if not provider_config or not personality_config:
        return

    model_name = provider_config.get("default_model", "claude-3-sonnet-20240229")
    system_prompt = personality_config.get("system_prompt", "あなたはAIです。")
    default_params = provider_config.get("default_parameters", {})

    # Claude API 用のパラメータ名に合わせる
    max_tokens = default_params.get("max_tokens", 1024)
    temperature = default_params.get("temperature")
    top_p = default_params.get("top_p")
    top_k = default_params.get("top_k")

    # 必須ではないパラメータは None でない場合のみ渡す
    claude_params = {
        "max_tokens": max_tokens,
    }
    if temperature is not None:
        claude_params["temperature"] = temperature
    if top_p is not None:
        claude_params["top_p"] = top_p
    if top_k is not None:
        claude_params["top_k"] = top_k


    # 4. Claude API の呼び出し (Messages API を使用)
    try:
        print(f"使用モデル: {model_name}")
        print(f"システムプロンプト: {system_prompt[:50]}...")
        print(f"生成パラメータ: {claude_params}")
        print("Claude API を呼び出しています...")

        user_message = "こんにちは！元気ですか？"

        # Claude Messages API の形式に合わせる
        messages = [
            {"role": "user", "content": "こんにちは"},
            {"role": "assistant", "content": "こんにちは！受け取ったメッセージをそのまま繰り返します。こんにちは"}, # 個性設定に合わせた応答例
            {"role": "user", "content": user_message}
        ]

        print(f"\n送信するプロンプト（最終）: {user_message}")

        response = client.messages.create(
            model=model_name,
            system=system_prompt, # Messages API では system パラメータで指定
            messages=messages,
            **claude_params # max_tokens, temperature など
        )

        # 5. 応答の表示
        print("\n--- Claude からの応答 ---")
        # response.content はブロックのリスト (通常は text ブロックが1つ)
        if response.content and response.content[0].type == "text":
            print(response.content[0].text)
        else:
            print("(応答にテキストコンテンツが含まれていませんでした)")
            print(f"Raw response: {response}")

        print("------------------------")
        print("疎通確認成功！")

    except APIStatusError as e:
        print(f"\nエラー: Claude API からステータスエラーが返されました: {e.status_code}")
        print(f"Response: {e.response}")
        print("疎通確認失敗。APIキー、モデル名、ネットワーク接続などを確認してください。")
    except APIError as e:
        print(f"\nエラー: Claude API 呼び出し中にエラーが発生しました: {e}")
        print("疎通確認失敗。APIキー、モデル名、ネットワーク接続などを確認してください。")
    except Exception as e:
        print(f"\nエラー: 予期せぬエラーが発生しました: {e}")
        print("疎通確認失敗。")

if __name__ == "__main__":
    main() 
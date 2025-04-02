import os
import google.generativeai as genai
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
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        print("エラー: 環境変数 'GOOGLE_API_KEY' が設定されていません。")
        print(".env ファイルを確認してください。")
        return

    # 2. Gemini クライアントの初期化
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        print(f"エラー: Gemini クライアントの初期化に失敗しました: {e}")
        return

    # 3. 設定ファイルの読み込み
    provider_config_path = "config/providers/gemini.yaml"
    personality_config_path = "config/personalities/test_personality.yaml"

    provider_config = load_yaml(provider_config_path)
    personality_config = load_yaml(personality_config_path)

    if not provider_config or not personality_config:
        return # エラーメッセージは load_yaml 内で表示される

    model_name = provider_config.get("default_model", "gemini-1.5-pro-latest")
    system_prompt = personality_config.get("system_prompt", "あなたはAIです。") # デフォルト値
    generation_config = provider_config.get("default_parameters", {})
    # Gemini API の GenerationConfig に合わせる (名前が異なる場合があるため)
    gemini_generation_config = {
        "temperature": generation_config.get("temperature"),
        "max_output_tokens": generation_config.get("maxOutputTokens"), # 名前合わせ
        "top_p": generation_config.get("topP"),
        "top_k": generation_config.get("topK")
    }
    # None の値を除去
    gemini_generation_config = {k: v for k, v in gemini_generation_config.items() if v is not None}


    # 4. Gemini API の呼び出し
    try:
        print(f"使用モデル: {model_name}")
        print(f"システムプロンプト: {system_prompt[:50]}...") # 長い場合は省略
        print(f"生成パラメータ: {gemini_generation_config}")
        print("Gemini API を呼び出しています...")

        # system_instruction パラメータがあるモデルか確認 (例: gemini-1.5-pro)
        # 単純化のため、ここでは system_prompt を直接使うモデルを想定
        # 正式版ではモデルによって使い分ける必要がある
        model = genai.GenerativeModel(
            model_name,
            # system_instruction=system_prompt # Gemini 1.5 Pro など用
            generation_config=genai.types.GenerationConfig(**gemini_generation_config) if gemini_generation_config else None
        )

        # system_prompt を最初のユーザーメッセージとして扱う（代替策）
        # 正式版のコアロジックでは、モデルに応じて適切な方法を選択する
        user_message = "こんにちは！調子はどうですか？"
        chat_history = [
             {'role':'user', 'parts': [system_prompt]},
             {'role':'model', 'parts': ["はい、承知いたしました。テスト用のAIです。"]}, # ダミーの応答履歴
             {'role':'user', 'parts': [user_message]}
        ]
        # 履歴がない場合は単純な generate_content を使う
        # response = model.generate_content(system_prompt + "\n\nUser: こんにちは！")

        # ChatSession を使う方法（履歴を考慮）- system_promptの扱いがモデルによる
        # chat = model.start_chat(history=chat_history[:-1]) # 最後のユーザーメッセージは除く
        # response = chat.send_message(chat_history[-1]['parts'])


        # generate_content に直接履歴を含める方法 (推奨されることが多い)
        # system_promptの扱いはモデルによって異なるので注意が必要
        # 1.5 Proなどでは system_instruction で指定すべき
        # 他のモデルでは、最初のユーザー/モデルターンでコンテキストとして含めることが多い
        prompt_content = []
        if system_prompt:
             # 1.5系以外の場合、システムプロンプトを履歴の最初に入れることが多い
            prompt_content.append({'role':'user', 'parts': [system_prompt]})
            prompt_content.append({'role':'model', 'parts': ['承知しました。その指示に従います。']}) # 暗黙の了解応答

        # 実際の会話履歴を追加 (今回はテストなので固定)
        prompt_content.append({'role':'user', 'parts': ["こんにちは"]})
        prompt_content.append({'role':'model', 'parts': ["こんにちは！受け取ったメッセージをそのまま繰り返します。こんにちは"]}) # 個性設定に合わせた応答例
        prompt_content.append({'role':'user', 'parts': [user_message]})

        print(f"\n送信するプロンプト（最終）: {user_message}")

        response = model.generate_content(prompt_content) # prompt_content にシステムプロンプトと履歴を含む

        # 5. 応答の表示
        print("\n--- Geminiからの応答 ---")
        print(response.text)
        print("-------------------------")
        print("疎通確認成功！")

    except Exception as e:
        print(f"\nエラー: Gemini API の呼び出し中にエラーが発生しました: {e}")
        if hasattr(e, 'response'):
             print(f"API Response: {e.response}")
        print("疎通確認失敗。APIキー、モデル名、設定ファイル、ネットワーク接続などを確認してください。")

if __name__ == "__main__":
    main() 
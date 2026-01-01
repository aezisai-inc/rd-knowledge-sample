"""
Knowledge Sample E2E テスト

ローカル環境と AWS 環境の両方で同一テストケースを実行可能。
pytest + localstack を使用。

Usage:
    # ローカル環境でテスト
    ENVIRONMENT=local pytest tests/ -v
    
    # AWS 環境でテスト
    ENVIRONMENT=aws pytest tests/ -v
"""

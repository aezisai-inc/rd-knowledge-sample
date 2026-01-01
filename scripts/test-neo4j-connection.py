#!/usr/bin/env python3
"""
Neo4j AuraDB 接続テストスクリプト

使用方法:
    # 環境変数から
    export NEO4J_URI="neo4j+s://xxx.databases.neo4j.io"
    export NEO4J_USER="neo4j"
    export NEO4J_PASSWORD="your-password"
    python scripts/test-neo4j-connection.py

    # コマンドライン引数で
    python scripts/test-neo4j-connection.py \
        --uri "neo4j+s://xxx.databases.neo4j.io" \
        --user "neo4j" \
        --password "your-password"

    # AWS Secrets Manager から
    python scripts/test-neo4j-connection.py --from-secrets --secret-id "rd-knowledge-neo4j-dev"
"""

import argparse
import json
import os
import sys
from datetime import datetime


def get_credentials_from_env():
    """環境変数から認証情報を取得"""
    return {
        "uri": os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        "user": os.environ.get("NEO4J_USER", "neo4j"),
        "password": os.environ.get("NEO4J_PASSWORD", "password"),
        "database": os.environ.get("NEO4J_DATABASE", "neo4j"),
    }


def get_credentials_from_secrets(secret_id: str, region: str = "ap-northeast-1"):
    """AWS Secrets Manager から認証情報を取得"""
    try:
        import boto3

        client = boto3.client("secretsmanager", region_name=region)
        response = client.get_secret_value(SecretId=secret_id)
        return json.loads(response["SecretString"])
    except ImportError:
        print("❌ boto3 がインストールされていません: pip install boto3")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Secrets Manager エラー: {e}")
        sys.exit(1)


def test_connection(credentials: dict):
    """Neo4j への接続をテスト"""
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("❌ neo4j がインストールされていません: pip install neo4j")
        sys.exit(1)

    uri = credentials["uri"]
    user = credentials["user"]
    password = credentials["password"]
    database = credentials.get("database", "neo4j")

    print(f"\n🔗 接続先: {uri}")
    print(f"👤 ユーザー: {user}")
    print(f"📁 データベース: {database}")
    print()

    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))

        with driver.session(database=database) as session:
            # 接続テスト
            result = session.run("RETURN 'Hello, Neo4j!' AS message")
            message = result.single()["message"]
            print(f"✅ 接続成功: {message}")

            # バージョン情報
            result = session.run("CALL dbms.components() YIELD versions RETURN versions[0] AS version")
            version = result.single()["version"]
            print(f"📊 Neo4j バージョン: {version}")

            # ノード・リレーション数
            result = session.run("MATCH (n) RETURN count(n) AS nodeCount")
            node_count = result.single()["nodeCount"]
            result = session.run("MATCH ()-[r]->() RETURN count(r) AS relCount")
            rel_count = result.single()["relCount"]
            print(f"📈 統計: {node_count} ノード, {rel_count} リレーションシップ")

        driver.close()
        print("\n✅ 接続テスト完了\n")
        return True

    except Exception as e:
        print(f"\n❌ 接続失敗: {e}\n")
        return False


def run_sample_operations(credentials: dict):
    """サンプル操作を実行"""
    from neo4j import GraphDatabase

    driver = GraphDatabase.driver(
        credentials["uri"],
        auth=(credentials["user"], credentials["password"]),
    )
    database = credentials.get("database", "neo4j")

    print("🧪 サンプル操作を実行中...\n")

    with driver.session(database=database) as session:
        # テストノード作成
        test_id = f"test-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        session.run(
            "CREATE (n:TestNode {id: $id, name: $name, created_at: $created_at})",
            id=test_id,
            name="Connection Test Node",
            created_at=datetime.now().isoformat(),
        )
        print(f"  ✅ ノード作成: {test_id}")

        # ノード取得
        result = session.run(
            "MATCH (n:TestNode {id: $id}) RETURN n",
            id=test_id,
        )
        node = result.single()["n"]
        print(f"  ✅ ノード取得: {dict(node)}")

        # テストノード削除
        session.run(
            "MATCH (n:TestNode {id: $id}) DELETE n",
            id=test_id,
        )
        print(f"  ✅ ノード削除: {test_id}")

    driver.close()
    print("\n✅ サンプル操作完了\n")


def main():
    parser = argparse.ArgumentParser(description="Neo4j AuraDB 接続テスト")
    parser.add_argument("--uri", help="Neo4j URI")
    parser.add_argument("--user", help="ユーザー名")
    parser.add_argument("--password", help="パスワード")
    parser.add_argument("--database", default="neo4j", help="データベース名")
    parser.add_argument("--from-secrets", action="store_true", help="Secrets Manager から取得")
    parser.add_argument("--secret-id", help="Secrets Manager シークレット ID")
    parser.add_argument("--region", default="ap-northeast-1", help="AWS リージョン")
    parser.add_argument("--run-sample", action="store_true", help="サンプル操作を実行")

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("       Neo4j AuraDB 接続テスト")
    print("=" * 60)

    # 認証情報取得
    if args.from_secrets:
        if not args.secret_id:
            print("❌ --from-secrets には --secret-id が必要です")
            sys.exit(1)
        credentials = get_credentials_from_secrets(args.secret_id, args.region)
    elif args.uri and args.user and args.password:
        credentials = {
            "uri": args.uri,
            "user": args.user,
            "password": args.password,
            "database": args.database,
        }
    else:
        credentials = get_credentials_from_env()

    # 接続テスト
    success = test_connection(credentials)

    # サンプル操作
    if success and args.run_sample:
        run_sample_operations(credentials)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()


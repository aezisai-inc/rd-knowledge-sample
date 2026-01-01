#!/bin/bash
# =============================================================================
# Neo4j AuraDB セットアップスクリプト
# =============================================================================
#
# このスクリプトは Neo4j AuraDB のセットアップを支援します。
#
# 前提条件:
#   - AWS CLI がインストール・設定済み
#   - jq がインストール済み
#   - Neo4j AuraDB インスタンスが作成済み
#
# 使用方法:
#   ./scripts/setup-neo4j-auradb.sh
#
# =============================================================================

set -e

# 色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 環境変数
ENV=${ENV:-dev}
SECRET_NAME="rd-knowledge-neo4j-${ENV}"
REGION=${AWS_REGION:-ap-northeast-1}

echo -e "${BLUE}==============================================================================${NC}"
echo -e "${BLUE}           Neo4j AuraDB セットアップスクリプト${NC}"
echo -e "${BLUE}==============================================================================${NC}"
echo ""

# =============================================================================
# Step 1: Neo4j AuraDB インスタンス作成手順
# =============================================================================
echo -e "${YELLOW}📌 Step 1: Neo4j AuraDB インスタンス作成${NC}"
echo ""
echo "以下の手順で Neo4j AuraDB インスタンスを作成してください："
echo ""
echo "  1. https://console.neo4j.io/ にアクセス"
echo "  2. Google または GitHub アカウントでログイン"
echo "  3. 「New Instance」をクリック"
echo "  4. 以下の設定でインスタンスを作成："
echo ""
echo "     ┌─────────────────────────────────────────┐"
echo "     │ Instance Name: rd-knowledge-${ENV}       │"
echo "     │ Type: AuraDB Free (開発) / Professional (本番) │"
echo "     │ Region: Asia Pacific (Tokyo) 推奨      │"
echo "     │ Size: Default                          │"
echo "     └─────────────────────────────────────────┘"
echo ""
echo "  5. 作成完了後、以下の情報をメモしてください："
echo "     - Connection URI (neo4j+s://xxxxx.databases.neo4j.io)"
echo "     - Username (通常は 'neo4j')"
echo "     - Password (自動生成)"
echo ""

# =============================================================================
# Step 2: 接続情報入力
# =============================================================================
echo -e "${YELLOW}📌 Step 2: 接続情報の入力${NC}"
echo ""

# 接続URI
read -p "Neo4j Connection URI (neo4j+s://xxx.databases.neo4j.io): " NEO4J_URI
if [[ -z "$NEO4J_URI" ]]; then
    echo -e "${RED}エラー: Connection URI は必須です${NC}"
    exit 1
fi

# ユーザー名
read -p "Neo4j Username [neo4j]: " NEO4J_USER
NEO4J_USER=${NEO4J_USER:-neo4j}

# パスワード
read -sp "Neo4j Password: " NEO4J_PASSWORD
echo ""
if [[ -z "$NEO4J_PASSWORD" ]]; then
    echo -e "${RED}エラー: Password は必須です${NC}"
    exit 1
fi

# データベース名
read -p "Database Name [neo4j]: " NEO4J_DATABASE
NEO4J_DATABASE=${NEO4J_DATABASE:-neo4j}

# =============================================================================
# Step 3: Secrets Manager に保存
# =============================================================================
echo ""
echo -e "${YELLOW}📌 Step 3: AWS Secrets Manager に保存${NC}"
echo ""

# シークレット JSON 作成
SECRET_JSON=$(cat <<EOF
{
    "uri": "${NEO4J_URI}",
    "user": "${NEO4J_USER}",
    "password": "${NEO4J_PASSWORD}",
    "database": "${NEO4J_DATABASE}"
}
EOF
)

# シークレットの存在確認
if aws secretsmanager describe-secret --secret-id "${SECRET_NAME}" --region "${REGION}" >/dev/null 2>&1; then
    echo "既存のシークレットを更新します: ${SECRET_NAME}"
    aws secretsmanager put-secret-value \
        --secret-id "${SECRET_NAME}" \
        --secret-string "${SECRET_JSON}" \
        --region "${REGION}"
else
    echo "新規シークレットを作成します: ${SECRET_NAME}"
    aws secretsmanager create-secret \
        --name "${SECRET_NAME}" \
        --description "Neo4j AuraDB connection credentials for rd-knowledge-sample (${ENV})" \
        --secret-string "${SECRET_JSON}" \
        --region "${REGION}"
fi

echo ""
echo -e "${GREEN}✅ Secrets Manager への保存が完了しました${NC}"

# =============================================================================
# Step 4: 接続テスト
# =============================================================================
echo ""
echo -e "${YELLOW}📌 Step 4: 接続テスト${NC}"
echo ""

# Python 接続テスト
if command -v python3 &> /dev/null; then
    echo "Python で接続テストを実行中..."
    python3 - <<PYTHON
import sys
try:
    from neo4j import GraphDatabase
    
    uri = "${NEO4J_URI}"
    user = "${NEO4J_USER}"
    password = "${NEO4J_PASSWORD}"
    
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    with driver.session() as session:
        result = session.run("RETURN 'Hello, Neo4j!' AS message")
        message = result.single()["message"]
        print(f"✅ 接続成功: {message}")
    
    driver.close()
    sys.exit(0)
except ImportError:
    print("⚠️ neo4j パッケージがインストールされていません")
    print("   pip install neo4j を実行してください")
    sys.exit(0)
except Exception as e:
    print(f"❌ 接続失敗: {e}")
    sys.exit(1)
PYTHON
else
    echo "⚠️ Python3 がインストールされていないため、接続テストをスキップします"
fi

# =============================================================================
# 完了メッセージ
# =============================================================================
echo ""
echo -e "${GREEN}==============================================================================${NC}"
echo -e "${GREEN}                      セットアップ完了！${NC}"
echo -e "${GREEN}==============================================================================${NC}"
echo ""
echo "次のステップ:"
echo ""
echo "  1. CDK を再デプロイ:"
echo "     cd infra && cdk deploy --context env=${ENV} --all"
echo ""
echo "  2. API エンドポイントをテスト:"
echo "     curl -X POST https://xxx.execute-api.ap-northeast-1.amazonaws.com/${ENV}/v1/graph/nodes \\"
echo "       -H 'Content-Type: application/json' \\"
echo "       -d '{\"type\": \"TestNode\", \"properties\": {\"name\": \"Hello Neo4j\"}}'"
echo ""


#!/bin/bash
# =============================================================================
# Lambda Layer ビルドスクリプト (uv 使用)
# =============================================================================
#
# 使用方法:
#   ./build.sh
#
# 前提条件:
#   - uv がインストール済み (pip install uv または brew install uv)
#
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Lambda Layer ビルド開始 (uv)"
echo ""

# 既存の python ディレクトリを削除
if [ -d "python" ]; then
    echo "📦 既存の python/ ディレクトリを削除中..."
    rm -rf python
fi

# python ディレクトリを作成
mkdir -p python

# uv でパッケージをインストール
echo "📥 uv でパッケージをインストール中..."
uv pip install \
    -r requirements.txt \
    --target python/ \
    --python-platform aarch64-manylinux_2_17 \
    --python-version 3.12

# 不要なファイルを削除（サイズ削減）
echo "🧹 不要なファイルを削除中..."
find python -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find python -type d -name "*.dist-info" -exec rm -rf {} + 2>/dev/null || true
find python -type f -name "*.pyc" -delete 2>/dev/null || true
find python -type f -name "*.pyo" -delete 2>/dev/null || true

# サイズ確認
LAYER_SIZE=$(du -sh python | cut -f1)
echo ""
echo "✅ ビルド完了"
echo "📊 Layer サイズ: $LAYER_SIZE"
echo ""
echo "次のステップ:"
echo "  cd ../../../ && npx cdk deploy RdKnowledge-Compute-dev --context env=dev"


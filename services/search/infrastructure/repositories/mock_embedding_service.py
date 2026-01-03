"""
Mock Embedding Service

テスト・開発用のモック埋め込みサービス。
本番では Bedrock Titan Embeddings に置き換え。
"""

import hashlib

from shared.domain.value_objects.entity_id import VectorEmbedding


class MockEmbeddingService:
    """
    埋め込み生成のモック実装
    
    テスト用。テキストのハッシュから擬似ベクトルを生成。
    """
    
    def __init__(self, dimensions: int = 384):
        self._dimensions = dimensions
    
    async def embed(self, text: str) -> VectorEmbedding:
        """テキストを埋め込みベクトルに変換"""
        # テキストのハッシュから擬似ベクトルを生成
        hash_bytes = hashlib.sha256(text.encode()).digest()
        
        # ハッシュを拡張してベクトルを生成
        values = []
        for i in range(self._dimensions):
            byte_index = i % len(hash_bytes)
            # -1.0 から 1.0 の範囲に正規化
            value = (hash_bytes[byte_index] / 255.0) * 2 - 1
            values.append(value)
        
        # 正規化
        norm = sum(v ** 2 for v in values) ** 0.5
        if norm > 0:
            values = [v / norm for v in values]
        
        return VectorEmbedding.from_list(values)
    
    async def embed_batch(self, texts: list[str]) -> list[VectorEmbedding]:
        """複数テキストをバッチで埋め込み"""
        return [await self.embed(text) for text in texts]

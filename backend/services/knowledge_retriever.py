"""
知识检索服务 - 高级RAG架构
支持: 混合检索、重排序、查询改写、多路召回
使用FAISS向量数据库
"""
from typing import List, Dict, Optional, Any, Tuple
import uuid
import logging
import os
import json
import pickle
import numpy as np
from pathlib import Path
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from config import settings, init_chat_model

logger = logging.getLogger(__name__)

try:
    import faiss
except ImportError:
    faiss = None
    logger.warning("FAISS not available. Install with: pip install faiss-cpu")

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None
    logger.warning("BM25Okapi not available.")


class FAISSCollection:
    """模拟ChromaDB Collection接口的FAISS封装"""

    def __init__(self, name: str, persist_dir: str, dimension: int = 1024):
        self.name = name
        self.dimension = dimension
        self.persist_dir = Path(persist_dir) / name
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        self.index = None
        self.documents: List[str] = []
        self.ids: List[str] = []
        self.metadatas: List[Dict] = []
        self.metadata = {"description": f"{name} collection"}

        self._load()

    def _index_path(self) -> Path:
        return self.persist_dir / "index.faiss"

    def _data_path(self) -> Path:
        return self.persist_dir / "data.pkl"

    def _load(self):
        """从磁盘加载索引和数据"""
        idx_path = self._index_path()
        data_path = self._data_path()
        if idx_path.exists() and data_path.exists():
            try:
                self.index = faiss.read_index(str(idx_path))
                with open(data_path, "rb") as f:
                    data = pickle.load(f)
                self.documents = data.get("documents", [])
                self.ids = data.get("ids", [])
                self.metadatas = data.get("metadatas", [])
                self.dimension = self.index.d
                logger.info(f"FAISS集合 '{self.name}' 加载成功: {len(self.ids)} 个文档")
            except Exception as e:
                logger.error(f"加载FAISS集合失败: {e}")
                self._init_empty()
        else:
            self._init_empty()

    def _init_empty(self):
        self.index = faiss.IndexFlatIP(self.dimension)  # 内积相似度
        self.documents = []
        self.ids = []
        self.metadatas = []

    def _save(self):
        """持久化到磁盘"""
        try:
            faiss.write_index(self.index, str(self._index_path()))
            with open(self._data_path(), "wb") as f:
                pickle.dump({
                    "documents": self.documents,
                    "ids": self.ids,
                    "metadatas": self.metadatas,
                }, f)
        except Exception as e:
            logger.error(f"保存FAISS集合失败: {e}")

    def count(self) -> int:
        return len(self.ids)

    def add(self, ids: List[str], documents: List[str],
            embeddings: List[List[float]], metadatas: Optional[List[Dict]] = None):
        """添加文档"""
        if not ids:
            return
        vecs = np.array(embeddings, dtype=np.float32)
        # L2归一化后用内积 = 余弦相似度
        faiss.normalize_L2(vecs)
        self.index.add(vecs)
        self.ids.extend(ids)
        self.documents.extend(documents)
        self.metadatas.extend(metadatas or [{} for _ in ids])
        self._save()

    def query(self, query_embeddings: List[List[float]], n_results: int = 3,
              where: Optional[Dict] = None) -> Dict:
        """查询最相似的文档"""
        if self.index.ntotal == 0:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]], "ids": [[]]}

        vec = np.array(query_embeddings, dtype=np.float32)
        faiss.normalize_L2(vec)
        n = min(n_results, self.index.ntotal)
        scores, indices = self.index.search(vec, n)

        docs, metas, dists, result_ids = [], [], [], []
        for i, idx in enumerate(indices[0]):
            if idx < 0 or idx >= len(self.ids):
                continue
            # where 过滤
            if where:
                meta = self.metadatas[idx]
                if not all(meta.get(k) == v for k, v in where.items()):
                    continue
            docs.append(self.documents[idx])
            metas.append(self.metadatas[idx])
            # FAISS内积相似度: 1.0=完全相同, 转为距离: distance = 1 - score
            dists.append(float(1.0 - scores[0][i]))
            result_ids.append(self.ids[idx])

        return {"documents": [docs], "metadatas": [metas], "distances": [dists], "ids": [result_ids]}

    def get(self, where: Optional[Dict] = None, limit: Optional[int] = None) -> Dict:
        """获取文档（可按元数据过滤）"""
        docs, metas, result_ids = [], [], []
        for i, doc_id in enumerate(self.ids):
            if where:
                meta = self.metadatas[i]
                if not all(meta.get(k) == v for k, v in where.items()):
                    continue
            docs.append(self.documents[i])
            metas.append(self.metadatas[i])
            result_ids.append(doc_id)
            if limit and len(result_ids) >= limit:
                break
        return {"documents": docs, "metadatas": metas, "ids": result_ids}

    def delete(self, ids: List[str]):
        """删除文档（重建索引）"""
        indices_to_keep = [i for i, did in enumerate(self.ids) if did not in ids]
        if len(indices_to_keep) == len(self.ids):
            return  # 没有要删的

        self.documents = [self.documents[i] for i in indices_to_keep]
        self.metadatas = [self.metadatas[i] for i in indices_to_keep]
        self.ids = [self.ids[i] for i in indices_to_keep]

        # 重建FAISS索引
        if self.documents:
            old_index = self.index
            vecs = np.array([old_index.reconstruct(i) for i in indices_to_keep], dtype=np.float32)
            self.index = faiss.IndexFlatIP(self.dimension)
            self.index.add(vecs)
        else:
            self._init_empty()
        self._save()

    def update(self, ids: List[str], documents: Optional[List[str]] = None,
               embeddings: Optional[List[List[float]]] = None,
               metadatas: Optional[List[Dict]] = None):
        """更新文档（删除后重新添加）"""
        self.delete(ids)
        add_docs = documents or [""] * len(ids)
        add_metas = metadatas or [{} for _ in ids]
        if embeddings:
            self.add(ids=ids, documents=add_docs, embeddings=embeddings, metadatas=add_metas)


class KnowledgeRetriever:
    """高级RAG知识检索器 (FAISS)"""

    def __init__(self):
        self.available = faiss is not None
        self.client = None
        self.embeddings = None
        self.llm = None
        self.knowledge_collection = None
        self.product_collection = None
        self.bm25_index = {}

        if self.available:
            try:
                persist_dir = settings.FAISS_PERSIST_DIRECTORY

                self.embeddings = OpenAIEmbeddings(
                    openai_api_key=settings.SILICONFLOW_API_KEY,
                    openai_api_base=settings.SILICONFLOW_BASE_URL,
                    model=settings.SILICONFLOW_EMBEDDING_MODEL
                )

                self.llm = init_chat_model(temperature=0)
                self.knowledge_collection = FAISSCollection("knowledge_base", persist_dir)
                self.product_collection = FAISSCollection("product_catalog", persist_dir)

                self._build_bm25_index("knowledge_base")
                self._build_bm25_index("product_catalog")
                logger.info("FAISS知识检索器初始化成功")
            except Exception as e:
                logger.error(f"初始化知识检索器失败: {e}")
                self.available = False

    def _build_bm25_index(self, collection_name: str):
        if not BM25Okapi:
            return
        try:
            collection = (
                self.knowledge_collection
                if collection_name == "knowledge_base"
                else self.product_collection
            )
            results = collection.get()
            if results and results['documents']:
                tokenized_docs = [doc.split() for doc in results['documents']]
                self.bm25_index[collection_name] = {
                    'index': BM25Okapi(tokenized_docs),
                    'documents': results['documents'],
                    'ids': results['ids'],
                    'metadatas': results['metadatas']
                }
                logger.info(f"BM25索引构建完成: {collection_name}, 文档数: {len(results['documents'])}")
        except Exception as e:
            logger.error(f"构建BM25索引失败: {e}")

    def _query_rewrite(self, query: str) -> List[str]:
        if not self.llm:
            return [query]
        try:
            prompt = ChatPromptTemplate.from_messages([
                ("system", """你是一个查询优化专家。给定用户的原始问题,生成3个改写后的查询,以提高检索效果。
要求:
1. 保持原意,但使用不同的表达方式
2. 添加相关的同义词或专业术语
3. 扩展或细化问题的关键点
4. 每行一个查询,不要编号"""),
                ("human", "原始问题: {query}\n\n请生成3个改写查询:")
            ])
            response = self.llm.invoke(prompt.format_messages(query=query))
            rewritten = [q.strip() for q in response.content.strip().split('\n') if q.strip()]
            return [query] + rewritten[:3]
        except Exception as e:
            logger.error(f"查询改写失败: {e}")
            return [query]

    def _vector_search(
        self, query: str, collection_name: str, top_k: int,
        filter_metadata: Optional[Dict] = None
    ) -> List[Tuple[Document, float]]:
        try:
            collection = (
                self.knowledge_collection
                if collection_name == "knowledge_base"
                else self.product_collection
            )
            query_embedding = self.embeddings.embed_query(query)
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=filter_metadata
            )
            docs_with_scores = []
            if results and results['documents']:
                for i, doc_text in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    score = 1 - results['distances'][0][i] if results['distances'] else 0
                    doc = Document(page_content=doc_text, metadata=metadata)
                    docs_with_scores.append((doc, score))
            return docs_with_scores
        except Exception as e:
            logger.error(f"向量检索失败: {e}")
            return []

    def _bm25_search(self, query: str, collection_name: str, top_k: int) -> List[Tuple[Document, float]]:
        if not BM25Okapi or collection_name not in self.bm25_index:
            return []
        try:
            index_data = self.bm25_index[collection_name]
            bm25 = index_data['index']
            tokenized_query = query.split()
            scores = bm25.get_scores(tokenized_query)
            top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
            docs_with_scores = []
            for idx in top_indices:
                if scores[idx] > 0:
                    doc = Document(
                        page_content=index_data['documents'][idx],
                        metadata=index_data['metadatas'][idx] if index_data['metadatas'] else {}
                    )
                    docs_with_scores.append((doc, float(scores[idx])))
            return docs_with_scores
        except Exception as e:
            logger.error(f"BM25检索失败: {e}")
            return []

    def _rerank_documents(
        self, query: str, docs_with_scores: List[Tuple[Document, float]], top_k: int
    ) -> List[Document]:
        if not self.llm or not docs_with_scores:
            return [doc for doc, _ in docs_with_scores[:top_k]]
        try:
            docs_text = "\n\n".join([
                f"文档{i+1} (初始分数: {score:.3f}):\n{doc.page_content[:500]}"
                for i, (doc, score) in enumerate(docs_with_scores)
            ])
            prompt = ChatPromptTemplate.from_messages([
                ("system", """你是一个文档相关性评估专家。给定用户问题和候选文档,评估每个文档与问题的相关性。
返回格式: 每行一个文档编号,按相关性从高到低排序,只返回编号,用逗号分隔。"""),
                ("human", "问题: {query}\n\n候选文档:\n{docs}\n\n请返回文档编号(按相关性排序):")
            ])
            response = self.llm.invoke(prompt.format_messages(query=query, docs=docs_text))
            ranking_str = response.content.strip()
            rankings = [int(x.strip()) - 1 for x in ranking_str.split(',') if x.strip().isdigit()]
            reranked_docs = []
            for rank in rankings[:top_k]:
                if 0 <= rank < len(docs_with_scores):
                    doc, original_score = docs_with_scores[rank]
                    doc.metadata['rerank_position'] = len(reranked_docs) + 1
                    doc.metadata['original_score'] = original_score
                    reranked_docs.append(doc)
            if not reranked_docs:
                return [doc for doc, _ in docs_with_scores[:top_k]]
            return reranked_docs
        except Exception as e:
            logger.error(f"重排序失败: {e}")
            return [doc for doc, _ in docs_with_scores[:top_k]]

    def retrieve(
        self, query: str, collection_name: str = "knowledge_base",
        top_k: int = 3, filter_metadata: Optional[Dict] = None,
        use_hybrid: bool = True, use_rerank: bool = True, use_query_rewrite: bool = True
    ) -> List[Document]:
        if not self.available or not self.embeddings:
            return []
        # 知识库为空时直接返回，跳过所有 LLM 调用（query_rewrite、rerank 等）
        collection = (
            self.knowledge_collection
            if collection_name == "knowledge_base"
            else self.product_collection
        )
        if collection.count() == 0:
            logger.info(f"集合 '{collection_name}' 为空，跳过检索")
            return []
        try:
            all_docs_with_scores = []
            queries = [query]
            if use_query_rewrite:
                queries = self._query_rewrite(query)
            for q in queries:
                vector_results = self._vector_search(q, collection_name, top_k * 2, filter_metadata)
                all_docs_with_scores.extend(vector_results)
                if use_hybrid and BM25Okapi:
                    bm25_results = self._bm25_search(q, collection_name, top_k * 2)
                    if bm25_results:
                        max_bm25_score = max(score for _, score in bm25_results)
                        if max_bm25_score > 0:
                            bm25_results = [(doc, score / max_bm25_score) for doc, score in bm25_results]
                    all_docs_with_scores.extend(bm25_results)
            doc_scores = {}
            for doc, score in all_docs_with_scores:
                doc_key = doc.page_content[:100]
                if doc_key in doc_scores:
                    if score > doc_scores[doc_key][1]:
                        doc_scores[doc_key] = (doc, score)
                else:
                    doc_scores[doc_key] = (doc, score)
            sorted_docs = sorted(doc_scores.values(), key=lambda x: x[1], reverse=True)[:top_k * 3]
            if use_rerank and self.llm and len(sorted_docs) > top_k:
                final_docs = self._rerank_documents(query, sorted_docs, top_k)
            else:
                final_docs = [doc for doc, _ in sorted_docs[:top_k]]
            for doc in final_docs:
                doc.metadata['retrieval_method'] = 'advanced_rag'
                doc.metadata['hybrid_search'] = use_hybrid
                doc.metadata['reranked'] = use_rerank
            return final_docs
        except Exception as e:
            logger.error(f"高级检索失败: {e}")
            return []

    def add_documents(
        self, documents: List[Dict[str, Any]], collection_name: str = "knowledge_base"
    ) -> List[str]:
        """添加文档到知识库"""
        if not self.available or not self.embeddings:
            return []
        collection = (
            self.knowledge_collection
            if collection_name == "knowledge_base"
            else self.product_collection
        )

        all_doc_ids = []
        BATCH_SIZE = 10
        for batch_start in range(0, len(documents), BATCH_SIZE):
            batch = documents[batch_start:batch_start + BATCH_SIZE]
            doc_ids = []
            texts = []
            metadatas = []
            for doc in batch:
                doc_id = doc.get("id", str(uuid.uuid4()))
                doc_ids.append(doc_id)
                texts.append(doc["content"])
                metadatas.append(doc.get("metadata", {}))

            try:
                embeddings = self.embeddings.embed_documents(texts)
                collection.add(
                    ids=doc_ids,
                    documents=texts,
                    embeddings=embeddings,
                    metadatas=metadatas
                )
                all_doc_ids.extend(doc_ids)
                logger.info(f"添加批次 {batch_start//BATCH_SIZE + 1}: {len(doc_ids)} 个文档")
            except Exception as e:
                logger.error(f"批次添加失败: {e}")

        self._build_bm25_index(collection_name)
        return all_doc_ids

    def delete_documents(
        self,
        document_ids: List[str],
        collection_name: str = "knowledge_base",
    ) -> int:
        """Delete multiple documents from a collection."""
        if not self.available or not document_ids:
            return 0

        collection = (
            self.knowledge_collection
            if collection_name == "knowledge_base"
            else self.product_collection
        )
        try:
            collection.delete(ids=document_ids)
            self._build_bm25_index(collection_name)
            return len(document_ids)
        except Exception as e:
            logger.error(f"批量删除文档失败: {e}")
            return 0

    def delete_document(self, document_id: str, collection_name: str = "knowledge_base"):
        self.delete_documents([document_id], collection_name)

    def delete_by_metadata(
        self,
        filter_metadata: Dict,
        collection_name: str = "knowledge_base",
        limit: Optional[int] = None,
    ) -> int:
        """Delete all documents whose metadata matches the given filter."""
        if not self.available:
            return 0

        collection = (
            self.knowledge_collection
            if collection_name == "knowledge_base"
            else self.product_collection
        )
        results = collection.get(where=filter_metadata, limit=limit)
        document_ids = results.get("ids", []) if results else []
        if not document_ids:
            return 0
        return self.delete_documents(document_ids, collection_name)

    def update_document(
        self, document_id: str, content: str,
        metadata: Optional[Dict] = None, collection_name: str = "knowledge_base"
    ):
        if not self.available or not self.embeddings:
            return
        collection = (
            self.knowledge_collection
            if collection_name == "knowledge_base"
            else self.product_collection
        )
        embedding = self.embeddings.embed_query(content)
        collection.update(
            ids=[document_id],
            documents=[content],
            embeddings=[embedding],
            metadatas=[metadata] if metadata else None
        )
        self._build_bm25_index(collection_name)

    def search_by_metadata(
        self, filter_metadata: Dict, collection_name: str = "knowledge_base", limit: int = 10
    ) -> List[Document]:
        if not self.available:
            return []
        collection = (
            self.knowledge_collection
            if collection_name == "knowledge_base"
            else self.product_collection
        )
        results = collection.get(where=filter_metadata, limit=limit)
        documents = []
        if results and results['documents']:
            for i, doc_text in enumerate(results['documents']):
                metadata = results['metadatas'][i] if results['metadatas'] else {}
                documents.append(Document(page_content=doc_text, metadata=metadata))
        return documents

    def get_collection_stats(self, collection_name: str = "knowledge_base") -> Dict:
        if not self.available:
            return {"name": collection_name, "count": 0, "metadata": {}}
        collection = (
            self.knowledge_collection
            if collection_name == "knowledge_base"
            else self.product_collection
        )
        return {
            "name": collection.name,
            "count": collection.count(),
            "metadata": collection.metadata
        }


# 全局知识检索器实例
knowledge_retriever = KnowledgeRetriever()

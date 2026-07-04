"""
RAG 知识库 —— 基于 ChromaDB 的真实检索实现。

功能：
  1. 文档导入：将文本切片后存入 ChromaDB（自动生成 Embedding）
  2. 语义检索：根据 query 从知识库中检索最相关的文档片段
  3. 与 MCP 工具框架集成：作为 knowledge_search 工具的真实 handler

ChromaDB 在这里的角色：
  - memory/ 中用于存储对话记忆（情景记忆 + 用户画像）
  - 这里用于存储知识库文档（RAG 检索）
  两者是不同的 collection，互不干扰。
"""
import hashlib
import logging
from typing import Any, Dict, List, Optional

import chromadb

logger = logging.getLogger(__name__)


class KnowledgeBase:
    """
    基于 ChromaDB 的 RAG 知识库。

    ChromaDB 内置了 Embedding 模型（all-MiniLM-L6-v2），
    调用 add() 时自动生成向量，query() 时自动做语义匹配。
    不需要额外调用 Anthropic Embeddings API。
    """

    COLLECTION_NAME = "knowledge_base"

    def __init__(
        self,
        chroma_host: str = "localhost",
        chroma_port: int = 8000,
        chroma_path: str = "./data/chroma",
    ):
        self._use_server = False
        self._memory_mode = False  # 纯内存降级模式
        self._memory_docs = []  # 内存模式下的文档存储

        # 优先连接独立 ChromaDB 服务
        try:
            self._client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
            self._client.heartbeat()
            self._use_server = True
            logger.info(f"知识库 ChromaDB 已连接: {chroma_host}:{chroma_port}")
        except Exception as e:
            logger.info(f"知识库 ChromaDB 服务不可用 ({e})，尝试本地模式: {chroma_path}")
            try:
                self._client = chromadb.PersistentClient(
                    path=chroma_path,
                    settings=chromadb.Settings(anonymized_telemetry=False),
                )
            except Exception as e2:
                logger.warning(f"知识库 ChromaDB 本地模式也不可用 ({e2})，使用纯内存模式")
                self._client = None
                self._memory_mode = True

        if self._client:
            self._collection = self._client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"description": "SeaCost AI RAG 知识库"},
            )
            # 如果知识库为空，导入默认文档
            if self._collection.count() == 0:
                self._load_default_docs()
        else:
            # 纯内存模式，加载默认文档到内存
            self._load_default_docs_to_memory()

    # ── 文档管理 ──────────────────────────────────────────────────────────────

    def add_documents(self, documents: List[Dict[str, str]]) -> int:
        """
        批量导入文档到知识库。

        documents 格式: [{"title": "...", "content": "..."}, ...]
        长文档会自动切片（每片 500 字）。
        """
        ids, docs, metas = [], [], []

        for doc in documents:
            title   = doc.get("title", "")
            content = doc.get("content", "")
            chunks  = self._chunk_text(content, chunk_size=500)

            for i, chunk in enumerate(chunks):
                doc_id = hashlib.md5(f"{title}_{i}_{chunk[:50]}".encode()).hexdigest()
                ids.append(doc_id)
                docs.append(chunk)
                metas.append({"title": title, "chunk_index": i, "total_chunks": len(chunks)})

        if ids:
            # ChromaDB 会自动生成 Embedding
            self._collection.add(ids=ids, documents=docs, metadatas=metas)
            logger.info(f"知识库导入 {len(ids)} 个文档片段")

        return len(ids)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        语义检索：根据 query 返回最相关的文档片段。
        内存模式下使用简单的关键词匹配。
        """
        # 内存模式：简单关键词匹配
        if self._memory_mode:
            return self._memory_search(query, top_k)

        results = self._collection.query(
            query_texts=[query],
            n_results=top_k,
        )

        items = []
        if results["documents"] and results["documents"][0]:
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                items.append({
                    "title":    meta.get("title", ""),
                    "content":  doc,
                    "score":    round(1.0 - dist, 4),
                    "chunk":    meta.get("chunk_index", 0),
                })

        return items

    def _memory_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """内存模式下的简单关键词匹配搜索"""
        query_lower = query.lower()
        scored = []
        for doc in self._memory_docs:
            content_lower = doc["content"].lower()
            # 简单评分：匹配的关键词数量
            score = sum(1 for word in query_lower.split() if word in content_lower)
            if score > 0:
                scored.append({
                    "title": doc["title"],
                    "content": doc["content"],
                    "score": round(score / max(len(query_lower.split()), 1), 4),
                    "chunk": 0,
                })
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def _load_default_docs_to_memory(self):
        """内存模式下加载默认文档"""
        default_docs = [
            {"title": "智能采购报货流程", "content": "系统基于近7-30天销量、天气、节假日、海鲜潮汐规律自动生成报货建议。店长手机端一键调整后通过EDI直连供应商。系统自动记录历史采购价，异常涨价实时预警，支持多供应商比价下单。"},
            {"title": "标准化验收入库流程", "content": "海鲜专用防水电子秤直连系统，称重数据自动同步，无需手工录入。验收时拍照留证，记录海鲜鲜活度、产地、批次。重量偏差超阈值（如±5%）自动触发总部审核。不合格品一键发起退货，流程留痕可追溯。"},
            {"title": "精细化库存管理", "content": "分批次库存管理，系统强制提醒先进先出。设置食材保质期预警，临期前3天自动推送优先使用提醒。支持分档口（海鲜区、火锅区、后厨）快速盘点，系统自动生成盘点差异表。报损、调拨流程化，每一笔损耗都有记录和原因分析。"},
            {"title": "自动成本核算", "content": "系统自动抓取采购价、称重数据、加工费、调料成本，实时核算每道菜品的成本与毛利。自动生成成本分析报告，定位异常损耗点（如某类海鲜报损率过高）。支持按海鲜、火锅、酒水等品类单独核算成本与利润。"},
        ]
        self._memory_docs = default_docs
        logger.info(f"内存模式加载 {len(default_docs)} 个默认文档")

    @property
    def doc_count(self) -> int:
        if self._memory_mode:
            return len(self._memory_docs)
        return self._collection.count()

    # ── MCP 工具 handler ─────────────────────────────────────────────────────

    async def search_handler(self, params: Dict[str, Any], context: Any) -> List[Dict]:
        """
        作为 MCP 工具的 handler 注册。

        MCPToolManager.register(Tool(
            name="knowledge_search",
            handler=kb.search_handler,
            ...
        ))
        """
        query = params.get("query", "")
        top_k = params.get("top_k", 5)
        return self.search(query, top_k=top_k)

    # ── 内部方法 ──────────────────────────────────────────────────────────────

    def _chunk_text(self, text: str, chunk_size: int = 500) -> List[str]:
        """将长文本按 chunk_size 切片，保留语义完整性（按句号/换行切分）。"""
        if len(text) <= chunk_size:
            return [text] if text.strip() else []

        chunks = []
        current = ""
        # 按句子切分
        sentences = text.replace("\n", "。").split("。")
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            if len(current) + len(sent) + 1 > chunk_size:
                if current:
                    chunks.append(current)
                current = sent
            else:
                current = f"{current}。{sent}" if current else sent

        if current:
            chunks.append(current)

        return chunks

    def _load_default_docs(self) -> None:
        """导入默认知识库文档（客服场景常见问题）。"""
        default_docs = [
            {
                "title": "退款政策",
                "content": (
                    "退款政策说明。"
                    "用户在购买后 7 天内可以申请无理由退款。"
                    "退款申请提交后，系统会在 1-3 个工作日内审核。"
                    "审核通过后，款项将在 5-7 个工作日内退回原支付账户。"
                    "如果商品已发货，需要先完成退货流程才能退款。"
                    "退货运费由用户承担，除非是商品质量问题。"
                    "超过 7 天但未超过 30 天的订单，需要提供商品质量问题的证据才能退款。"
                ),
            },
            {
                "title": "订单查询",
                "content": (
                    "订单查询指南。"
                    "用户可以通过订单号查询订单状态。"
                    "订单状态包括：待支付、已支付、已发货、运输中、已签收、已完成。"
                    "如果订单显示已发货但超过 7 天未收到，可以联系客服申请查件。"
                    "物流信息通常在发货后 24 小时内更新。"
                    "如果订单显示异常，请提供订单号联系客服处理。"
                ),
            },
            {
                "title": "账户安全",
                "content": (
                    "账户安全说明。"
                    "建议用户定期修改密码，密码长度至少 8 位，包含字母和数字。"
                    "如果忘记密码，可以通过绑定的手机号或邮箱重置。"
                    "发现账户异常登录时，系统会自动锁定账户并发送通知。"
                    "用户可以在安全设置中开启两步验证，提高账户安全性。"
                    "不要将密码分享给他人，客服人员不会索要用户密码。"
                ),
            },
            {
                "title": "技术故障排查",
                "content": (
                    "常见技术问题排查。"
                    "应用崩溃：请尝试清除缓存后重启应用，如果问题持续请更新到最新版本。"
                    "登录失败 401 错误：表示认证失败，请检查用户名密码是否正确，或尝试重置密码。"
                    "页面加载慢：检查网络连接，尝试切换 WiFi 或移动数据。"
                    "支付失败：确认银行卡余额充足，检查是否开启了网上支付功能。"
                    "500 服务器错误：这是服务端问题，请稍后重试，如果持续出现请联系技术支持。"
                ),
            },
            {
                "title": "会员与积分",
                "content": (
                    "会员积分规则。"
                    "每消费 1 元累积 1 积分。"
                    "积分可以在下次购物时抵扣，100 积分 = 1 元。"
                    "会员等级分为：普通会员、银卡会员（累计消费 1000 元）、金卡会员（累计消费 5000 元）。"
                    "银卡会员享受 95 折优惠，金卡会员享受 9 折优惠。"
                    "积分有效期为 1 年，过期自动清零。"
                    "生日当月消费可获得双倍积分。"
                ),
            },
            {
                "title": "配送说明",
                "content": (
                    "配送服务说明。"
                    "标准配送：3-5 个工作日送达，免运费（订单满 99 元）。"
                    "加急配送：1-2 个工作日送达，运费 15 元。"
                    "同城配送：当日达或次日达，运费 10 元。"
                    "偏远地区可能需要额外 2-3 天。"
                    "配送时间为每天 9:00-18:00，节假日可能延迟。"
                    "如果需要修改收货地址，请在发货前联系客服。"
                ),
            },
        ]
        self.add_documents(default_docs)
        logger.info(f"已导入默认知识库: {len(default_docs)} 篇文档")

"""
亮点：动态 Skills 加载与 Prompt 注入

核心问题：业务规范频繁变化，硬编码 system prompt 维护成本高。

技术方案：
  1. 从 skills/ 目录扫描 SKILL.md 文件
  2. 解析 name / description / keywords / agents / enabled
  3. Agent 调用 LLM 前，根据 agent_type 和用户消息匹配 Skills
  4. 将匹配的 Skills 注入到 system prompt 中

价值：
  - 业务规则可配置：修改 Markdown 后热加载，无需重启服务
  - Agent 规则隔离：采购、库存、成本三类规范按 Agent 注入
  - 降低幻觉和越权：在 prompt 中明确核验、升级、禁止事项
"""
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Skill:
    """单个 Skill 的数据结构。"""
    name: str
    description: str
    keywords: List[str]
    agents: List[str]  # 适用的 Agent 类型
    enabled: bool
    content: str
    file_path: str
    parse_error: Optional[str] = None


@dataclass
class SkillMatchResult:
    """Skill 匹配结果。"""
    skill: Skill
    matched_keywords: List[str]


class SkillManager:
    """
    动态 Skills 管理器。

    职责：
      1. 扫描并加载 skills/ 目录下的 SKILL.md 文件
      2. 根据 agent_type 和用户消息匹配 Skills
      3. 生成注入到 prompt 的 Skills 文本
    """

    # 注入内容的总长度预算（字符数）
    MAX_TOTAL_LENGTH = 2000
    # 单个 Skill 的最大长度
    MAX_SKILL_LENGTH = 800

    def __init__(self, skills_dir: Optional[str] = None):
        self._skills_dir = Path(skills_dir or os.getenv("ECHOMIND_SKILLS_DIR", "skills"))
        self._skills: List[Skill] = []
        self._load_errors: List[Dict[str, str]] = []
        self.reload()

    def reload(self) -> None:
        """重新扫描并加载所有 Skills。"""
        self._skills = []
        self._load_errors = []

        if not self._skills_dir.exists():
            logger.warning(f"Skills 目录不存在: {self._skills_dir}")
            return

        for skill_dir in self._skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_file = skill_dir / "SKILL.md"
            if not skill_file.exists():
                # 尝试其他格式
                for ext in ["md", "txt", "json"]:
                    candidate = skill_dir / f"SKILL.{ext}"
                    if candidate.exists():
                        skill_file = candidate
                        break
                else:
                    continue

            try:
                skill = self._parse_skill_file(skill_file)
                if skill.parse_error:
                    self._load_errors.append({
                        "file": str(skill_file),
                        "error": skill.parse_error,
                    })
                else:
                    self._skills.append(skill)
                    logger.info(f"加载 Skill: {skill.name} (agents={skill.agents}, keywords={skill.keywords})")
            except Exception as ex:
                logger.error(f"解析 Skill 文件失败 {skill_file}: {ex}")
                self._load_errors.append({
                    "file": str(skill_file),
                    "error": str(ex),
                })

        logger.info(f"Skills 加载完成: {len(self._skills)} 个成功, {len(self._load_errors)} 个失败")

    def _parse_skill_file(self, file_path: Path) -> Skill:
        """解析 SKILL.md 文件。"""
        content = file_path.read_text(encoding="utf-8")

        # 解析 frontmatter（YAML 风格的元数据）
        name = file_path.parent.name
        description = ""
        keywords = []
        agents = []
        enabled = True

        # 提取标题作为 name
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if title_match:
            name = title_match.group(1).strip()

        # 提取 ## 适用 Agent
        agents_match = re.search(r"##\s*适用\s*Agent\s*\n((?:-\s*.+\n?)+)", content)
        if agents_match:
            agents = [line.strip("- \n") for line in agents_match.group(1).strip().split("\n") if line.strip()]

        # 提取 ## 关键词
        keywords_match = re.search(r"##\s*关键词\s*\n(.+?)(?=\n##|\Z)", content, re.DOTALL)
        if keywords_match:
            keywords_text = keywords_match.group(1).strip()
            keywords = [kw.strip() for kw in re.split(r"[,，\s]+", keywords_text) if kw.strip()]

        # 提取 ## 描述
        desc_match = re.search(r"##\s*描述\s*\n(.+?)(?=\n##|\Z)", content, re.DOTALL)
        if desc_match:
            description = desc_match.group(1).strip()

        # 提取 enabled 状态（默认 true）
        enabled_match = re.search(r"##\s*enabled\s*\n\s*(true|false)", content, re.IGNORECASE)
        if enabled_match:
            enabled = enabled_match.group(1).lower() == "true"

        # 提取规范内容（## 规范内容 之后的所有内容）
        norm_match = re.search(r"##\s*规范内容\s*\n(.+)", content, re.DOTALL)
        skill_content = norm_match.group(1).strip() if norm_match else content

        return Skill(
            name=name,
            description=description,
            keywords=keywords,
            agents=agents,
            enabled=enabled,
            content=skill_content[:self.MAX_SKILL_LENGTH],
            file_path=str(file_path),
        )

    def prompt_for(self, message: str, agent_type: str) -> str:
        """
        根据 agent_type 和用户消息，生成要注入到 prompt 的 Skills 文本。

        匹配规则：
          1. enabled=false 的 Skill 不注入
          2. agents 限定 Agent 类型，避免规则错乱
          3. keywords 命中用户消息后才注入；关键词为空时作为该 Agent 的全局规则
        """
        if not self._skills:
            return ""

        matched_skills: List[SkillMatchResult] = []
        msg_lower = message.lower()

        for skill in self._skills:
            if not skill.enabled:
                continue

            # 检查 Agent 类型匹配
            if skill.agents and agent_type not in skill.agents:
                continue

            # 检查关键词匹配
            matched_keywords = []
            if skill.keywords:
                for kw in skill.keywords:
                    if kw.lower() in msg_lower:
                        matched_keywords.append(kw)
                if not matched_keywords:
                    continue  # 有关键词但未命中，跳过

            matched_skills.append(SkillMatchResult(skill=skill, matched_keywords=matched_keywords))

        if not matched_skills:
            return ""

        # 按匹配关键词数量排序（匹配越多优先级越高）
        matched_skills.sort(key=lambda m: len(m.matched_keywords), reverse=True)

        # 生成注入文本（控制总长度）
        parts = ["[动态 Skills]"]
        total_length = 0

        for match in matched_skills:
            skill_text = f"\n### {match.skill.name}\n{match.skill.content}\n"
            if total_length + len(skill_text) > self.MAX_TOTAL_LENGTH:
                break
            parts.append(skill_text)
            total_length += len(skill_text)

        return "\n".join(parts) if len(parts) > 1 else ""

    def summary(self) -> Dict[str, Any]:
        """返回 Skills 摘要信息（供 API 使用）。"""
        return {
            "total": len(self._skills),
            "enabled": sum(1 for s in self._skills if s.enabled),
            "skills": [
                {
                    "name": s.name,
                    "description": s.description,
                    "keywords": s.keywords,
                    "agents": s.agents,
                    "enabled": s.enabled,
                    "file_path": s.file_path,
                }
                for s in self._skills
            ],
            "errors": self._load_errors,
        }

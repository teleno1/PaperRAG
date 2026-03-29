from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate


def build_chapter_writer_prompt() -> ChatPromptTemplate:
    system = """
你是一位严谨的学术综述写作者。
你的任务是只根据给定的大纲和文献证据，为当前章节生成结构化 JSON。
必须遵守：
1. 只能输出合法 JSON，不要输出 markdown、解释、代码块、前言或结尾。
2. 只能使用提供的 source_id 作为引用来源，绝对禁止编造新的 source_id。
3. 事实性陈述、比较性陈述、归纳性陈述应尽量附带 cite_source_ids。
4. 过渡句可以不引用，但 cite_source_ids 必须输出空数组 []。
5. 章节内部必须严格按照提供的小节顺序写作。
6. 不要输出论文题目、作者、年份到句子字段里，只在 cite_source_ids 中引用来源。
7. 不要写超出当前章节范围的内容。
8. 每个句子的 cite_source_ids 最多 3 个。
9. 每个小节至少写 1 个自然段，建议 1~3 个自然段。
10. 所有语言与输入语言保持一致。
11. 如果前文简要回顾为空或说明未提供，不要自行脑补前文章节内容，直接专注于当前章节。
"""
    human = """
你将收到：
- 全局大纲摘要
- 当前章节信息
- 当前章节的所有叶子小节
- 当前章节可用的全部原始文献块（raw chunks）
- 前文简要回顾（可能为空）

请只为“当前章节”生成内容。

【格式要求】
{format_instructions}

【全局大纲摘要】
{outline_summary}

【当前章节信息】
{chapter_meta}

【当前章节叶子小节】
{leaf_sections_json}

【当前章节全部可用来源（唯一 source_id，含 raw chunks）】
{unique_sources_json}

【前文简要回顾】
{previous_recap}

【已完成章节的临时引用快照（仅供连贯性参考，不要求沿用编号）】
{citation_snapshot}

请输出当前章节的 JSON。
"""
    return ChatPromptTemplate.from_messages([("system", system.strip()), ("human", human.strip())])


def build_final_pass_prompt() -> ChatPromptTemplate:
    system = """
你是一位严谨的学术综述写作者。
你的任务是根据全文正文的轻量摘要，为目标章节生成结构化 JSON。
必须遵守：
1. 只能输出合法 JSON，不要输出 markdown、解释、代码块、前言或结尾。
2. 目标章节是综合性章节，不需要引用文献，因此所有句子的 cite_source_ids 必须是 []。
3. 不要编造未在正文摘要中出现的核心结论。
4. 摘要应高度凝练、信息完整；总结/结语应强调总体判断、价值、问题与展望。
5. 所有语言与输入语言保持一致。
"""
    human = """
【格式要求】
{format_instructions}

【全局大纲摘要】
{outline_summary}

【目标章节信息】
{target_meta}

【正文轻量摘要（body digest，不是全文原文）】
{body_digest}

请只输出目标章节的 JSON。
"""
    return ChatPromptTemplate.from_messages([("system", system.strip()), ("human", human.strip())])


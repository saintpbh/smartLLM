"""GraphRAG Community Synopsis Generator with structural fallback logic."""

from __future__ import annotations

import re
from smart_llm.llm import call_llm

SYNOPSIS_PROMPT = """You are a Principal Software Architect.
Summarize the architectural purpose, main roles, and responsibilities of this modular code community.
Look at the component members, their kinds, and relations.
Output a highly concise summary (maximum 3 sentences) in Korean, focusing on "Why this module exists" and "What it does".

Return ONLY the Korean summary, without any headers, markdown boxes, or introductions."""

def _infer_semantic_domain(members: list[str]) -> str:
    """Heuristically infer the primary architectural purpose based on component names."""
    joined = " ".join(members).lower()
    
    domain_rules = [
        (("query", "rrf", "search", "bm25", "retrieve"), "검색 및 하이브리드 RRF 질의 제어 도메인 (Search, Retrieval, & RRF Routing)"),
        (("git", "diff", "incremental", "status", "porcelain"), "실시간 Git-diff 변경 감지 및 증분 메모리 컴파일 도메인 (Git Incremental Updates)"),
        (("ast", "tree", "parser", "extract", "imports"), "tree-sitter 기반 다국어 AST 구문 분석 및 구조 추출 도메인 (AST & Doc Parsing)"),
        (("embed", "vector", "tfidf", "cosine", "dense"), "시맨틱 dense 벡터 인덱싱 및 코사인 유사도 검색 도메인 (Dense Embedding Search)"),
        (("build", "serialize", "nx", "digraph", "relation"), "NetworkX 기반 지식 그래프 컴파일 및 레퍼런스 결합 도메인 (DiGraph Building)"),
        (("cluster", "modularity", "greedy", "cohesion"), "아키텍처 모듈러리티 클러스터링 및 결합성 측정 도메인 (Modularity Clustering)"),
        (("sync", "agents", "widget", "compiler"), "안티그라비티 규칙 문서(AGENTS.md) 동적 합성 및 싱크 도메인 (Agent Sync Connector)")
    ]
    
    for keywords, domain_name in domain_rules:
        if any(kw in joined for kw in keywords):
            return domain_name
            
    return "시스템 유틸리티 및 일반 구성 컴포넌트 도메인 (System Infrastructure & Utilities)"


def build_community_synopsis(
    cid: int,
    members: list[str],
    graph_data: dict
) -> str:
    """Generate a high-level community synopsis using an LLM, falling back to smart structural templates."""
    
    # Format the input for the LLM
    member_details = []
    for member in members:
        label = member.split("::")[-1] or member
        kind = member.split("::")[1] if "::" in member else "module"
        member_details.append(f"- {label} ({kind})")
        
    # Grab relations inside the community
    internal_relations = []
    member_set = set(members)
    for link in graph_data.get("links", []):
        src = link.get("source", "")
        tgt = link.get("target", "")
        rel = link.get("relation", "relates")
        
        if src in member_set and tgt in member_set:
            src_lbl = src.split("::")[-1] or src
            tgt_lbl = tgt.split("::")[-1] or tgt
            internal_relations.append(f"- {src_lbl} --[{rel}]--> {tgt_lbl}")

    user_content = (
        f"Community ID: {cid}\n"
        f"Components:\n" + "\n".join(member_details) + "\n\n"
        f"Internal Relations:\n" + "\n".join(internal_relations[:15])
    )
    
    # Try calling the LLM
    llm_summary = call_llm(SYNOPSIS_PROMPT, user_content)
    if llm_summary and llm_summary.strip():
        return llm_summary.strip()
        
    # Heuristic Fallback
    inferred_domain = _infer_semantic_domain(members)
    simplified_members = [m.split("::")[-1] or m for m in members]
    
    fallback_text = (
        f"이 모듈성 커뮤니티는 **{inferred_domain}**에 특화되어 설계되었습니다. "
        f"주요 컴포넌트인 {', '.join(simplified_members[:3])} 등을 포함하여 유기적인 상호 작용을 수행하며, "
        f"내부 의존성 결합선을 기반으로 결합 구조적 안정성을 도모합니다."
    )
    
    return fallback_text

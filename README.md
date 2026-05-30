# SMART LLM 🧠

**SMART LLM (Smart Memory & Architecture-aware Retrieval Tool for LLMs)** is a premium developer tool designed to solve AI context window saturation and session amnesia by building an **Incremental Hierarchical Knowledge Graph, Hybrid Search Index (Dense + Sparse), and Semantic Wiki**.

It builds on top of the concepts of Andrej Karpathy's LLM Wiki pattern, resolving the limitations of previous attempts by introducing semantic synthesis, query routing, and hybrid retrieval.

---

## Key Features

1. **Hybrid Parsing & Semantic Synthesis**:
   - Uses `tree-sitter` for lightning-fast, zero-token AST code structure extraction.
   - Leverages lightweight LLMs or Gen AI APIs incrementally to synthesize "Purpose & Intent" for code blocks and communities.

2. **Dense & Sparse Hybrid Retrieval (RRF)**:
   - Combines traditional keyword matching (**BM25**) with semantic vector embeddings.
   - Ranks results using **RRF (Reciprocal Rank Fusion)** to merge code identifier searches and general conceptual questions.

3. **Query Gateway**:
   - Classifies queries (codebase-specific vs general coding concepts) to prevent injecting irrelevant contexts.
   - Filters out poor matches using a **Relevance Gate** to keep AI context clean.

4. **Hierarchical Knowledge Graph**:
   - Represents the project at three distinct levels of abstraction: **Project -> Module -> Entity (Class/Function)**.
   - Dynamically zooms in or out of codebase details to minimize token consumption.

---

## Installation & Setup

```bash
# Clone the repository and navigate to it
cd /Users/bongpark/.gemini/antigravity/scratch/smart-llm

# Install the package in editable mode
pip install -e .
```

---

## Quick Start

```bash
# Index your current project
smart-llm ingest .

# Query the codebase memory
smart-llm query "How does authentication work in this project?"
```

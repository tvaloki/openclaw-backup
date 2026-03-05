#!/usr/bin/env python3
import argparse
import json
import math
import os
import time
from datetime import datetime, timezone
from urllib import request, error


def post_json(url: str, payload: dict, headers: dict | None = None, timeout: int = 60):
    body = json.dumps(payload).encode("utf-8")
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = request.Request(url, data=body, headers=h, method="POST")
    with request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def mcp_call(tool_name: str, arguments: dict):
    url = os.environ.get("OPENBRAIN_MCP_URL", "http://127.0.0.1:54321/mcp")
    token = os.environ.get("OPENBRAIN_MCP_TOKEN", "")
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload = {
        "jsonrpc": "2.0",
        "id": int(time.time() * 1000),
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }

    try:
        out = post_json(url, payload, headers=headers, timeout=60)
        if "error" in out:
            return {"ok": False, "error": out["error"]}
        return {"ok": True, "result": out.get("result")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def openai_chat(messages: list[dict], model: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required")

    payload = {"model": model, "messages": messages, "temperature": 0.2}
    headers = {"Authorization": f"Bearer {api_key}"}
    out = post_json("https://api.openai.com/v1/chat/completions", payload, headers=headers, timeout=90)
    return out["choices"][0]["message"]["content"].strip()


def openai_embedding(text: str, model: str = "text-embedding-3-small") -> list[float]:
    api_key = os.environ.get("OPENAI_API_KEY")
    payload = {"model": model, "input": text[:8000]}
    headers = {"Authorization": f"Bearer {api_key}"}
    out = post_json("https://api.openai.com/v1/embeddings", payload, headers=headers, timeout=90)
    return out["data"][0]["embedding"]


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def extract_text(mcp_result) -> str:
    if isinstance(mcp_result, str):
        return mcp_result
    if isinstance(mcp_result, dict):
        if "content" in mcp_result and isinstance(mcp_result["content"], str):
            return mcp_result["content"]
        return json.dumps(mcp_result)[:6000]
    if isinstance(mcp_result, list):
        return "\n".join(extract_text(x) for x in mcp_result)[:6000]
    return str(mcp_result)


def main():
    p = argparse.ArgumentParser(description="DualAgentDebate: ChatGPT + Open Brain MCP debate loop")
    p.add_argument("--query", required=True, help="User query to debate")
    p.add_argument("--thoughts", default="", help="Optional explicit thoughts text")
    p.add_argument("--rounds", type=int, default=3)
    p.add_argument("--agreement-threshold", type=float, default=0.90)
    p.add_argument("--model", default=os.environ.get("DEBATE_MODEL", "gpt-4o-mini"))
    args = p.parse_args()

    context_tool = os.environ.get("OPENBRAIN_CONTEXT_TOOL", "search_docs")
    sql_tool = os.environ.get("OPENBRAIN_SQL_TOOL", "execute_sql")

    context = ""
    q_gql = args.query.replace('\\', '\\\\').replace('"', '\\"')
    gql = (
        'query { searchDocs(query: "' + q_gql + '", limit: 5) '
        '{ nodes { ... on Guide { title href content } '
        '... on TroubleshootingGuide { title href content } '
        '... on CLICommandReference { title href content } } } }'
    )
    c = mcp_call(context_tool, {"graphql_query": gql})
    if c.get("ok"):
        context = extract_text(c.get("result"))

    thoughts = args.thoughts.strip()
    if not thoughts:
        q_esc = args.query.replace("'", "''")
        thoughts_sql = f"""
        select coalesce(string_agg(content, E'\\n\\n---\\n\\n' order by created_at desc), '') as text
        from public.thoughts
        where lower(content) like '%' || lower('{q_esc}') || '%'
        limit 8;
        """
        t = mcp_call(sql_tool, {"query": thoughts_sql})
        if t.get("ok"):
            thoughts = extract_text(t.get("result"))

    if not thoughts:
        thoughts = "No prior thoughts found in Open Brain."

    rounds = []
    final_similarity = 0.0
    agreed = False

    system = (
        "You are Debate Agent A (ChatGPT). Use supplied Open Brain context. "
        "Provide concise reasoning, then a final stance."
    )

    prior = ""
    for i in range(1, args.rounds + 1):
        user_prompt = (
            f"Round {i}. Query: {args.query}\n\n"
            f"Open Brain Context:\n{context[:6000]}\n\n"
            f"My thoughts (Agent B):\n{thoughts[:6000]}\n\n"
            f"Prior round summary:\n{prior}\n\n"
            "Respond with:\n"
            "1) Claim\n2) Evidence\n3) Counterpoint to my thoughts\n4) Revised stance"
        )
        reply = openai_chat([
            {"role": "system", "content": system},
            {"role": "user", "content": user_prompt},
        ], args.model)

        emb_reply = openai_embedding(reply)
        emb_thoughts = openai_embedding(thoughts)
        sim = cosine(emb_reply, emb_thoughts)
        final_similarity = sim
        prior = f"Similarity to my thoughts: {sim:.3f}. Key points: {reply[:1200]}"

        rounds.append({"round": i, "similarity": sim, "reply": reply})
        if sim >= args.agreement_threshold:
            agreed = True
            break

    outcome = {
        "query": args.query,
        "agreed": agreed,
        "final_similarity": round(final_similarity, 4),
        "rounds_executed": len(rounds),
        "rounds": rounds,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
    }

    key = f"dual-agent-debate:{int(time.time())}"
    content_json = json.dumps(outcome, ensure_ascii=False).replace("'", "''")
    key_esc = key.replace("'", "''")
    insert_sql = f"""
    insert into public.memories (key, content, category, importance)
    values ('{key_esc}', '{content_json}', 'decision', 2)
    returning key, created_at;
    """
    saved = mcp_call(sql_tool, {"query": insert_sql})

    print(json.dumps({
        "outcome": outcome,
        "store": saved,
        "store_tool": sql_tool,
        "context_tool": context_tool,
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

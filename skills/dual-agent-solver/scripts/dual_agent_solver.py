#!/usr/bin/env python3
import argparse
import json
import os
import random
import subprocess
import time
from datetime import datetime, timezone
from typing import Optional
from urllib import request


def sleep_backoff(i: int):
    time.sleep(0.8 * (2 ** i) + random.uniform(0, 0.2))


def post_json(url: str, payload: dict, headers: Optional[dict] = None, timeout: int = 60):
    h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    if headers:
        h.update(headers)
    req = request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=h, method="POST")
    with request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def mcp_call(tool: str, arguments: dict, retries: int = 2):
    url = os.environ.get("OPENBRAIN_MCP_URL", "http://127.0.0.1:54321/mcp")
    tok = os.environ.get("OPENBRAIN_MCP_TOKEN", "")
    headers = {"Authorization": f"Bearer {tok}"} if tok else {}
    payload = {"jsonrpc": "2.0", "id": int(time.time() * 1000), "method": "tools/call", "params": {"name": tool, "arguments": arguments}}
    for i in range(retries + 1):
        try:
            out = post_json(url, payload, headers=headers, timeout=60)
            if "error" in out:
                if i < retries:
                    sleep_backoff(i)
                    continue
                return {"ok": False, "error": out["error"]}
            return {"ok": True, "result": out.get("result")}
        except Exception as e:
            if i < retries:
                sleep_backoff(i)
                continue
            return {"ok": False, "error": str(e)}


def extract_text(x) -> str:
    if isinstance(x, str):
        return x
    if isinstance(x, dict):
        if isinstance(x.get("content"), str):
            return x["content"]
        if isinstance(x.get("content"), list):
            return "\n".join(str(i.get("text", i)) if isinstance(i, dict) else str(i) for i in x["content"])
        return json.dumps(x)[:12000]
    if isinstance(x, list):
        return "\n".join(extract_text(i) for i in x)[:12000]
    return str(x)


def safe_sql_str(v: str) -> str:
    tag = "q"
    while f"${tag}$" in v:
        tag += "q"
    return f"${tag}${v}${tag}$"


def parse_openclaw_json(out: str) -> dict:
    try:
        return json.loads(out)
    except Exception:
        i = out.rfind("{")
        while i != -1:
            try:
                return json.loads(out[i:])
            except Exception:
                i = out.rfind("{", 0, i)
    raise RuntimeError("Could not parse openclaw agent output")


def openclaw_agent_turn(system_role: str, prompt: str, model: str = None) -> str:
    msg = f"SYSTEM ROLE:\n{system_role}\n\nTASK:\n{prompt}"
    cmd = ["openclaw", "agent", "--json", "--agent", "main", "--thinking", "low", "--message", msg]
    if model:
        cmd.extend(["--model", model])
    out = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)
    data = parse_openclaw_json(out)
    payloads = data.get("payloads", [])
    if not payloads:
        raise RuntimeError("No payload text returned")
    return (payloads[0].get("text") or "").strip()


def maybe_openai_turn(system_role: str, prompt: str, model: str = None) -> str:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return openclaw_agent_turn(system_role, prompt, model)
    payload = {
        "model": os.environ.get("SOLVER_SECOND_MODEL", "gpt-4o-mini"),
        "messages": [
            {"role": "system", "content": system_role},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    headers = {"Authorization": f"Bearer {key}"}
    out = post_json("https://api.openai.com/v1/chat/completions", payload, headers=headers, timeout=90)
    return out["choices"][0]["message"]["content"].strip()


def ensure_memories_table(sql_tool: str):
    q = """
    create table if not exists public.memories (
      id bigserial primary key,
      key text unique,
      content text,
      category text,
      importance integer,
      source text,
      metadata jsonb,
      created_at timestamptz default now()
    );
    """
    _ = mcp_call(sql_tool, {"query": q})


def get_doug_context(sql_tool: str, query: str) -> str:
    # Extract keywords from query simply
    words = [w.lower() for w in query.split() if len(w) > 4]
    if not words:
        return ""
    
    # Try to find relevant Doug thoughts based on the top 2 words
    search_terms = " and ".join(f"content ilike '%{w}%'" for w in words[:2])
    
    q = f"""
    select 'Thought (' || created_at::date || '): ' || left(content, 1000)
    from public.thoughts 
    where {search_terms}
    order by created_at desc limit 3;
    """
    res = mcp_call(sql_tool, {"query": q})
    context = ""
    if res.get("ok") and res.get("result"):
        context += extract_text(res.get("result")) + "\n"
        
    q_mem = f"""
    select 'Memory (' || key || '): ' || left(content, 1000)
    from public.memories 
    where {search_terms}
    order by created_at desc limit 2;
    """
    res_mem = mcp_call(sql_tool, {"query": q_mem})
    if res_mem.get("ok") and res_mem.get("result"):
        context += extract_text(res_mem.get("result")) + "\n"
        
    return context.strip()


def main():
    ap = argparse.ArgumentParser(description="DualAgentSolver: 2-agent collaborative solver with OpenClaw")
    ap.add_argument("--query", required=True)
    ap.add_argument("--rounds", type=int, default=4)
    ap.add_argument("--model", type=str, help="Model override for the OpenClaw solver agent (e.g. openai-codex/gpt-5.3-codex)")
    args = ap.parse_args()

    sql_tool = os.environ.get("OPENBRAIN_SQL_TOOL", "execute_sql")
    docs_tool = os.environ.get("OPENBRAIN_CONTEXT_TOOL", "search_docs")

    print("[*] Gathering context from Docs...")
    # Optional context pull from docs
    q = args.query.replace('\\', '\\\\').replace('"', '\\"')
    gql = 'query { searchDocs(query: "' + q + '", limit: 3) { nodes { ... on Guide { title content } ... on CLICommandReference { title content } } } }'
    ctx = mcp_call(docs_tool, {"graphql_query": gql})
    context = "SUPABASE DOCS:\n" + extract_text(ctx.get("result"))[:4000] if ctx.get("ok") else ""

    print("[*] Gathering context from Doug (historical memory)...")
    doug_ctx = get_doug_context(sql_tool, args.query)
    if doug_ctx:
        context += "\n\nDOUG HISTORICAL CONTEXT:\n" + doug_ctx[:4000]

    solver_role = (
        "You are Agent A (Primary Solver). Produce practical, bulletproof implementation plans with exact code/commands, "
        "clear steps, tradeoffs, and a rollback strategy. Never provide pseudocode when real code is needed. Tell the user what they need to hear, not what they want to hear. Be ruthlessly objective."
    )
    critic_role = (
        "You are Agent B (Adversarial Reviewer). Find hidden risks, edge cases, missing assumptions, and force stronger plans. "
        "Reject plans that lack exact implementation details or have obvious failure modes. Tell the user what they need to hear, not what they want to hear. Be ruthlessly objective."
    )

    a_plan = ""
    b_crit = ""
    rounds = []

    for i in range(1, max(1, args.rounds) + 1):
        print(f"[*] Executing Round {i} Solver...")
        a_prompt = (
            f"Round {i}. Problem: {args.query}\n\n"
            f"Context:\n{context}\n\n"
        )
        if b_crit:
            a_prompt += f"Previous critique to address:\n{b_crit}\n\n"
            
        a_prompt += "Output:\n1) Proposed solution\n2) Exact Steps (with code)\n3) Risks\n4) Rollback"
        a_plan = openclaw_agent_turn(solver_role, a_prompt, args.model)

        print(f"[*] Executing Round {i} Critic...")
        b_prompt = (
            f"Round {i}. Evaluate this plan strictly:\n\n{a_plan}\n\n"
            "Output:\n1) Critical flaws\n2) Missing assumptions\n3) Better alternative\n4) Acceptance conditions"
        )
        b_crit = maybe_openai_turn(critic_role, b_prompt)

        rounds.append({"round": i, "solver": a_plan[:5000], "critic": b_crit[:5000]})

    print("[*] Generating Final Merged Solution...")
    final_prompt = (
        f"Problem: {args.query}\n\n"
        f"Latest solver plan:\n{a_plan}\n\n"
        f"Latest critic review:\n{b_crit}\n\n"
        "Produce ONE merged, hardened final answer containing:\n"
        "- Decision\n- Why\n- Step-by-step execution plan (with exact code)\n- Risk mitigations\n- Rollback plan\n- Immediate next actions"
    )
    final_solution = openclaw_agent_turn(solver_role, final_prompt, args.model)

    outcome = {
        "run_id": f"das-{int(time.time())}",
        "query": args.query,
        "rounds_executed": len(rounds),
        "rounds": rounds,
        "final_solution": final_solution,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    ensure_memories_table(sql_tool)
    key = f"dual-agent-solver:{int(time.time())}"
    ins = (
        "insert into public.memories (key, content, category, importance, source, metadata) values ("
        f"{safe_sql_str(key)}, {safe_sql_str(json.dumps(outcome, ensure_ascii=False)[:14000])}, "
        f"{safe_sql_str('solution')}, 3, {safe_sql_str('DualAgentSolver')}, {safe_sql_str(json.dumps({'query': args.query, 'run_id': outcome['run_id']}, ensure_ascii=False))}::jsonb"
        ") returning key, created_at;"
    )
    saved = mcp_call(sql_tool, {"query": ins})

    print(json.dumps({"outcome": outcome, "store": saved, "memory_key": key}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

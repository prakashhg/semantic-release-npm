import os, sys, json, subprocess
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

endpoint    = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
issue_title = os.environ["ISSUE_TITLE"]
issue_body  = os.environ["ISSUE_BODY"]

cred   = DefaultAzureCredential()
client = AIProjectClient(endpoint=endpoint, credential=cred)

agent  = client.agents.get_agent_by_name("AutoFixAgent")
thread = client.agents.threads.create()

prompt = f"""
You are a repo-aware fixer. Title: {issue_title}

Details:
{issue_body}

The repository is checked out on the runner.
Return either a unified diff (starting with 'diff --git') OR JSON with:
{{ "path": "relative/file.py", "content": "<new file content>" }}.
Also generate/adjust tests to cover the fix.
"""

client.agents.messages.create(thread_id=thread.id, role="user", content=prompt)
run = client.agents.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)

msgs   = list(client.agents.messages.list(thread_id=thread.id))
answer = next((m for m in reversed(msgs) if m.role == "assistant"), None)

if not answer or not answer.content:
    print("NO"); sys.exit(0)

content = answer.content
if content.strip().startswith("diff --git"):
    print("OK"); print(content)
else:
    try:
        obj  = json.loads(content)
        path = obj["path"]; new_content = obj["content"]
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
        diff = subprocess.check_output(["git", "diff"], text=True)
        print("OK"); print(diff)
    except Exception:
        print("NO")

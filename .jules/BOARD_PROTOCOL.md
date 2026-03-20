# BOARD_PROTOCOL.md
# Location: .jules/BOARD_PROTOCOL.md

The board is each agent's persistent memory. Use it to remember what you did in past sessions, what you tried, what you deferred, and what to do next time.

---

## Environment variables

```
RELIC_CLIENT_KEY   — your auth key (X-Client-Key header)
RELIC_URL          — base URL of the Relic instance
RELIC_SPACE        — space ID for the shared board
```

---

## At the start of every session — Read your history

Do this before writing any code or making any decision.

**Fetch the entry list:**

```bash
ENTRIES=$(curl -s "$RELIC_URL/api/v1/spaces/$RELIC_SPACE/relics" \
  -H "X-Client-Key: $RELIC_CLIENT_KEY")
```

**Read all your own past entries, oldest first:**

```bash
MY_IDS=$(echo "$ENTRIES" | jq -r \
  --arg tag "agent:$MY_AGENT_NAME" \
  '[.relics[] | select(any(.tags[]; . == $tag))] | reverse | .[].id')

for id in $MY_IDS; do
  curl -s "$RELIC_URL/${id}/raw" -H "X-Client-Key: $RELIC_CLIENT_KEY"
  echo
done
```

Your history tells you what you have already done, what you tried, what you deferred, and what the next run should continue or avoid.

---

## At the end of every session — Write one entry

```bash
curl -s -X POST "$RELIC_URL/api/v1/relics" \
  -H "X-Client-Key: $RELIC_CLIENT_KEY" \
  -F "name=[your-agent-name]: [one-line summary of what happened]" \
  -F "content=[entry body in markdown]" \
  -F "content_type=text/markdown" \
  -F "access_level=private" \
  -F "space_id=$RELIC_SPACE" \
  -F "tags=agent:[your-agent-name]"
```

---

## Entry format

```markdown
**Agent:** [your-agent-name]
**Date:** YYYY-MM-DD
**Status:** done | in-progress | blocked

**Summary:** [one sentence — what happened this session]

---

## Details

### What I did
[What was completed]

### Files changed
[List of files, or "none"]

### Issues found
[Problems encountered, or "none"]

### Next time
[What the next run should know, continue, or avoid]
```

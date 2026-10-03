# OpenCode chat archives

This folder holds exported transcripts of opencode chats that exceeded the
local request-body size limit.

## Why

When a chat session's accumulated token history exceeds the request body
limit of the underlying HTTP server / LLM provider, every new message fails
with:

    failed to read request body (ref: <uuid>)

Known opencode bug (see [anomalyco/opencode#43119](https://github.com/anomalyco/opencode/issues/43119))
that triggers when many images have been pasted into the chat, or when the
chat has thousands of message turns.

## What's here

| file | size | description |
|---|---|---|
| `chat_20260902-160331Z_ip-availability-check.md` | 5.3 MB | Full transcript of `ses_fe14e23a4ffeGrZUMmrf90tls1` — 7,479 messages, every part (user, assistant, tool calls, reasoning). Last updated 2026-09-02. |

The session was **restored** from a pre-edit DB backup on 2026-09-02, so
this markdown is now a redundant read-only copy of the live chat. Kept here
just in case the chat ever gets corrupted again.

## Future prevention

- Use `/compact` (or `ctrl+x c`) periodically on long sessions.
- For IP-camera work that touches many images, prefer running scripts in
  PowerShell directly and pasting summaries into chat, rather than pasting
  large result blobs.
- The DB at `~/.local/share/opencode/opencode.db` grows without bound —
  consider vacuuming it occasionally after archiving old sessions.

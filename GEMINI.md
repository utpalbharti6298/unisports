# Workspace Slash Commands & Agent Customizations

## Supported Slash Commands

The following slash commands are registered and active in this workspace:

1. **/caveman [lite | full | ultra | off]**:
   - Compresses agent output tokens by cutting conversational fluff, filler words, and unnecessary pleasantries while preserving all code, commands, and links.
   - `full` (default): Terse technical fragments, skips articles (a/an/the).
   - `lite`: Short bullet points, concise sentences.
   - `ultra`: Pure code and minimal status updates.
   - `off`: Resets to standard detailed explanation mode.

2. **/graphify [report | view]**:
   - Triggers the Graphify skill to scan repository structure, build dependency maps, generate `graphify-out/GRAPH_REPORT.md` and `graphify-out/graph.html`.

Whenever the user starts a prompt with `/caveman` or `/graphify`, immediately execute the corresponding skill behavior.

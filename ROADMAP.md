# Roadmap

## Future Work

### Cross-Platform Agent Transformation

Claude Code and VSCode/Copilot use incompatible frontmatter formats. Cross-platform installation is currently blocked.

**Platform differences:**

| Field | Claude Code | VSCode/Copilot |
|-------|-------------|----------------|
| name | Required | Optional (defaults to filename) |
| description | Required | Optional |
| model | Short names (haiku, sonnet, opus) | Full names |
| tools | N/A | Optional list |
| File extension | `.md` | `.agent.md` |

**Documentation sources:**

- Claude Code agents: https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/agents
- GitHub Copilot custom agents: https://docs.github.com/en/copilot/reference/custom-agents-configuration
- VSCode custom agents: https://code.visualstudio.com/docs/copilot/customization/custom-agents
- VSCode prompt files: https://code.visualstudio.com/docs/copilot/customization/prompt-files

**Future implementation:**

1. Add `--transform` flag to enable experimental cross-platform transforms
2. Map model names between platforms
3. Generate required fields (name, description) from filename/content
4. Warn users about potential incompatibilities
5. Consider bidirectional sync for agent authors targeting multiple platforms

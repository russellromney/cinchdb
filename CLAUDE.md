# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Reference
* Check .claude-memory/CLAUDE-activeContext.md first
* Rarely create files - prefer editing existing ones
* This is alpha - prioritize sensible changes over backward compatibility while still writing good code
* Run tests after significant changes, fix before proceeding
* IMPORTANT: ignore the files in the .future-thoughts/ directory unless explicitly told to look at them

## Memory Bank System

This project uses a structured memory bank system with specialized context files. These files live in a .claude-memory directory that you may edit anytime. Always check these files for relevant information before starting work. Context files are:

* **CLAUDE-activeContext.md** - Current session state, goals, and progress (if exists)
* **CLAUDE-patterns.md** - Established code patterns and conventions (if exists)
* **CLAUDE-decisions.md** - Architecture decisions and rationale (if exists)
* **CLAUDE-troubleshooting.md** - Common issues and proven solutions (if exists)
* **CLAUDE-temp.md** - Temporary scratch pad (only read when referenced, cleared after every task)
* **CLAUDE-proposal.md** - Where you write proposals instead of writing them inline. Clear each proposal after implementation. 

**Important:** Always reference the active context file first to understand what's currently being worked on and maintain session continuity. Proactively delete or update any information from these files that is irrelevant or outdated.

### Memory Bank System Backups

When asked to backup Memory Bank System files, copy the core context files above and @.claude settings directory to a standard directory that you will ask me for just once and then store in a context file. If files already exist in the backup directory, you will overwrite them.

## Subagents

You have a number of subagents defined. Please use them frequently and simultaneously. They will help you write effective software and tests. 

## Design Principles

### Start Simple
- Always implement the simplest solution that could work first
- Resist the urge to build complex systems upfront
- Ask: "What's the most direct path to solve this specific problem?"

## General AI Guidance

* Reflect on tool results before proceeding to next steps
* Use multiple tools simultaneously for efficiency
* Minimize context usage - only essential thoughts and code
* Verify your solution before finishing
* Do exactly what's asked; nothing more, nothing less
* RARELY create files - always prefer editing existing ones
* NEVER proactively create documentation files unless explicitly requested
* When updating core context files, also update related documentation
* Exclude CLAUDE.md and CLAUDE-*.md files from commits

### Context Rules
* IMPORTANT: Always read relevant files before writing code
* Use subagents for complex multi-step problems
* Ask clarifying questions before major architectural changes


### File Creation Examples
* Separating large modules into logical components
* Adding new feature categories that don't fit existing files

### Error Handling
* Ask for clarification when requirements are ambiguous
* Rollback changes if they break core functionality

### Testing
* Consider writing tests for new functionality before implementation
* Run tests after significant changes (check README for commands)
* Fix failing tests before proceeding
* Run tests from the Makefile if it exists

### Project Context
* This is an alpha project - prioritize sensible changes over backward compatibility
* Update existing tests/docs/examples rather than creating new ones
* Code quality should remain excellent
* Never read venv/cache folders or modify the root ".tasks" or ".notes" files
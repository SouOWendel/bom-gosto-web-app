# Agent Directives & Code Conventions

## Git & Commit Guidelines
When generating, suggesting, or writing git commit messages, always adhere to the following rules:

1. **Language:** Write the commit title and body strictly in Brazilian Portuguese (pt-BR). Keep Conventional Commit prefixes in English (e.g., `feat`, `fix`).
2. **Format:** Use the *Conventional Commits* specification: `<type>[optional scope]: <description>`.
   - Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`.
3. **Tone:** Use the imperative mood for descriptions (e.g., "adiciona funcionalidade", not "adicionado" or "adicionei").
4. **Scope:** Base the message strictly on staged changes (`git diff --cached`).
5. **Formatting:** Capitalize appropriately, do not add a trailing period to the commit title, and keep the title under 50-72 characters.
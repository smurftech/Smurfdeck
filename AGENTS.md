# SmurfDeck project guardrails

- The canonical local project directory is `/home/smurftech/GIT_REPOS/Smurfdeck`.
- Use the user's existing GitHub account. Do not create a new account or invent
  Git author names, email addresses, credentials, or repository ownership.
- Before creating a GitHub repository, confirm its owner and visibility with the
  user. Personal/private is the default project posture unless the user says
  otherwise.
- Do not overwrite or delete content in the canonical project directory. Inspect
  it first and preserve unrelated user files.
- Keep `main` runnable. Use focused feature branches for larger changes and run
  lint and tests before proposing a merge.
- Do not copy GPL application code. SmurfDeck application code is original and
  MIT-licensed; dependencies are consumed through their published APIs.
- Do not commit secrets, tokens, device identifiers, local virtual environments,
  caches, generated builds, or machine-specific configuration.

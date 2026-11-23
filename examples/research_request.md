Read /skills/proxy-harness/SKILL.md, /skills/mixer-contract/SKILL.md and
/skills/feedback/SKILL.md with the file tool. Write exactly one vectorized
causal PyTorch mixer to candidate.py. A direct Transformer-equivalent
mixer is acceptable for the initial integration trial.

Use the shell tool to run:

```sh
evo-proxy eval candidate.py --profile smoke --out runs/candidate
```

Read the generated feedback.md from the path printed by the shell. Quote
the profile, comparable-performance value and stop reason from the file.
The purpose here is to prove the connection. Keep the evaluation budget fixed.

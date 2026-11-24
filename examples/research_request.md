File tools start at this workspace's virtual /. Shell commands already
run in this workspace. The evo-proxy command and prepared data are ready.

Make your first tool action read_file on each of these three files,
in one group: /skills/proxy-harness/SKILL.md,
/skills/mixer-contract/SKILL.md, /skills/feedback/SKILL.md.

After these reads your next tool action is write_file to /candidate_mixer.py.
Use pure PyTorch and Class CandidateMixer with the documented signature.
A dense implementation can use a bias-free d->3d QKV projection and a
bias-free d->d output projection, with causal SDPA. This is enough to
calculate the block budget without discovering implementation files.
Use vectorized forward, preserve causality, and keep the frozen checks.
Do not use ls, pwd, import probes, source discovery, or help commands.

Then run exactly:
evo-proxy check ./candidate_mixer.py --out ./runs/check

If check fails, read its feedback path and fix the candidate using
write_file, within the 3 revision cap. After check passes, run exactly:
evo-proxy eval ./candidate_mixer.py --profile smoke --out ./runs/candidate

Use read_file on /runs/candidate/feedback.md, or the actual path
printed by eval if it differs. Then use write_file to create
/candidate_next.py and /feedback_evidence.md. In evidence, quote the
actual feedback path, profile, stop reason and one measured CPU
time or resource value. State the specific implementation change
you made in candidate_next.py in response to a measured observation.
The smoke result has no measured performance. Stop after the two writes.

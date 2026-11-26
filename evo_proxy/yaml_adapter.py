"""External btyaml adapter; executor authored by the lab beyond_transformer contributors.

No executor code is vendored. See docs/YAML_CANDIDATES.md for attribution.
"""
from hashlib import sha256
import json
import os
from pathlib import Path
import sys


def sources(folder, workspace):
    folder, workspace = Path(folder).resolve(), Path(workspace).resolve()
    for name in ('representation.yaml', 'relation.yaml'):
        if not (folder/name).is_file():
            raise ValueError(f'YAML candidate requires {name}')
    executor = workspace/'btyaml'
    if not (executor/'executor.py').is_file():
        raise ValueError('EVO_PROXY_BTYAML must point to a beyond_transformer checkout')
    # Record both the external engine and candidate inputs in the plugin identity.
    files = [*folder.rglob('*.yaml'), *executor.rglob('*.py'), *executor.rglob('*.yaml')]
    return {str(p): sha256(p.read_bytes()).hexdigest() for p in sorted(set(files))}


def materialize(candidate, output):
    candidate = Path(candidate).resolve()
    if not candidate.is_dir():
        return candidate
    workspace = os.environ.get('EVO_PROXY_BTYAML')
    if not workspace:
        raise ValueError('Set EVO_PROXY_BTYAML to the external beyond_transformer checkout')
    workspace = str(Path(workspace).expanduser().resolve())
    manifest = sources(candidate, workspace)
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    target = output/'yaml_candidate.py'
    body = ('from evo_proxy.yaml_adapter import ExternalYamlMixer\n'
            'class CandidateMixer(ExternalYamlMixer):\n'
            f'    candidate_folder = {str(candidate)!r}\n'
            f'    external_workspace = {workspace!r}\n'
            f'    expected_sources = {manifest!r}\n')
    target.write_text(body)
    (output/'yaml_provenance.json').write_text(json.dumps(dict(candidate=str(candidate),workspace=workspace,sources=manifest),indent=2)+'\n')
    return target


# Import torch only in the configured harness interpreter.
import torch
from torch import nn


class ExternalYamlMixer(nn.Module):
    def __init__(self, d_model, num_heads, l_max):
        super().__init__()
        if sources(self.candidate_folder, self.external_workspace) != self.expected_sources:
            raise ValueError('External YAML or executor changed; regenerate the candidate adapter')
        sys.path.insert(0, self.external_workspace)
        from btyaml.executor import YamlModule, load_spec
        import btyaml.executor as executor
        if not Path(executor.__file__).resolve().is_relative_to(Path(self.external_workspace).resolve()):
            raise ValueError('A different btyaml is already imported')
        spec = load_spec(Path(self.candidate_folder)/'representation.yaml')
        if spec.get('contract') != 'sequence_mixer':
            raise ValueError('YAML contract must be sequence_mixer')
        config = spec.get('config') or {}
        given = {k:v for k,v in dict(D=d_model,H=num_heads,L=l_max).items() if k in config}
        # Frozen parameter probes may create a block under the meta device;
        # btyaml initialization regions require actual CPU tensors.
        with torch.device('cpu'):
            self.mixer = YamlModule(spec, **given)

    def forward(self, x):
        return self.mixer(x)

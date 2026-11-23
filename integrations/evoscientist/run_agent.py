"""Run one bounded EvoScientist request from a prepared release workspace."""
import argparse
import json
from pathlib import Path
import os
import re
import shutil
import subprocess
import time

from adapter import limited_gateway

QUIET = ('memory_workers_enabled', 'memory_observations_enabled', 'memory_skill_synthesis_enabled',
         'memory_profile_enabled', 'enable_scheduler', 'enable_async_subagents')


def run_engine(command, env, workspace, runtime):
    budget = runtime/'budget.json'
    deadline = time.monotonic()+1200
    with (runtime/'events.jsonl').open('w',encoding='utf-8') as output:
        engine = subprocess.Popen(command,cwd=workspace,env=env,stdout=output,stderr=subprocess.STDOUT)
        try:
            while True:
                try:
                    return engine.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    if budget.is_file() and json.loads(budget.read_text()).get('rejected',0):
                        print('EvoScientist stopped after the gateway rejected an over-cap request.')
                        return 3
                    if time.monotonic() >= deadline:
                        print('EvoScientist stopped at the wall-clock limit.')
                        return 3
        finally:
            if engine.poll() is None:
                engine.terminate()
                try:
                    engine.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    engine.kill()
                    engine.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--prompt',type=Path,required=True)
    parser.add_argument('--env-file',type=Path,required=True)
    parser.add_argument('--model',required=True)
    parser.add_argument('--llm-cap',type=int,default=20)
    parser.add_argument('--max-attempts',type=int,default=3,help='Maximum distinct prechecked candidate revisions')
    args=parser.parse_args()
    executable=shutil.which('EvoSci')
    if not executable or min(args.llm_cap,args.max_attempts)<1:
        parser.error('Install EvoScientist 0.4.1 and supply positive limits')
    fields={}
    for line in args.env_file.read_text(encoding='utf-8').splitlines():
        match=re.fullmatch(r'\s*(?:export\s+)?(CUSTOM_OPENAI_API_KEY|CUSTOM_OPENAI_BASE_URL|LLM_API_KEY|LLM_BASE_URL)\s*=\s*(.*)',line)
        if match:
            fields[match[1]]=match[2].strip().strip('"\'')
    key=fields.get('CUSTOM_OPENAI_API_KEY') or fields.get('LLM_API_KEY')
    endpoint=fields.get('CUSTOM_OPENAI_BASE_URL') or fields.get('LLM_BASE_URL')
    if not key or key.startswith('<'):
        print('EvoScientist not run: no gateway credential in the specified file')
        return 2
    if not endpoint:
        parser.error('Specify the OpenAI-compatible endpoint in the same env file')
    from urllib.parse import urlsplit
    target=urlsplit(endpoint)
    if target.scheme!='https' or not target.hostname or target.path.rstrip('/')!='/v1' or target.username or target.query or target.fragment:
        parser.error('Expected an HTTPS OpenAI-compatible endpoint ending in /v1')
    workspace=args.workspace.resolve()
    runtime=workspace/('.agent-'+str(time.time_ns()))
    runtime.mkdir(parents=True)
    env={k:v for k,v in os.environ.items() if not re.search(r'(API_KEY|ACCESS_TOKEN|PASSWORD)$',k)}
    env.update(XDG_CONFIG_HOME=str(runtime/'config'),EVOSCIENTIST_DATA_DIR=str(runtime/'state'),
               EVOSCIENTIST_WORKSPACE_DIR=str(workspace),PYTHONDONTWRITEBYTECODE='1',
               EVO_PROXY_ATTEMPT_LOG=str(runtime/'attempts.json'),EVO_PROXY_MAX_ATTEMPTS=str(args.max_attempts))
    with limited_gateway(endpoint.rstrip('/'),key,runtime/'budget.json',args.llm_cap,force_model=args.model) as gateway:
        env.update(CUSTOM_OPENAI_BASE_URL=gateway,CUSTOM_OPENAI_API_KEY='local-gateway')
        for name,value in (('provider','custom-openai'),('model',args.model),*((k,'false') for k in QUIET)):
            configured=subprocess.run([executable,'config','set',name,value],cwd=workspace,env=env,capture_output=True,timeout=45)
            if configured.returncode:
                print(f'EvoScientist configuration did not accept {name}')
                return 1
        command = [executable,'--workdir',str(workspace),'--ui','cli','--auto-mode',
                   '--output-format','stream-json','-p',args.prompt.read_text(encoding='utf-8')]
        result = run_engine(command,env,workspace,runtime)
    print(f'Agent evidence: {runtime}')
    return result


if __name__=='__main__':
    raise SystemExit(main())

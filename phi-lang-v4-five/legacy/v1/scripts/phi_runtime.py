"""φ-lang v4 Runtime — Execute φ-code as shell commands.
Zero-LLM execution engine. Tier 1 (shell only).

Parses φ-expressions with grammar operators and executes them:
  SEQ:   a b c      → run sequentially
  RETRY: a*3        → retry up to 3 times on failure
  COND:  a?b:c      → if a passes: run b; else c
  PIPE:  a|b        → pipe a stdout → b stdin
  PAR:   a,b,c      → run in parallel
  NOTIFY: a>tg      → run a then send Telegram notification
  NODE:  a::Oracle  → run on remote node via SSH

Usage:
    from phi_runtime import Runtime
    r = Runtime()
    r.execute("dwg*3>tg ::Oracle")
"""

import os
import re
import sys
import time
import shlex
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Union

from phi_codec_v4 import Codec, CODE_RE, CHARS

# Node SSH aliases
NODE_HOSTS = {
    'a0': 'ubuntu@84.8.159.123',       # Oracle
    'a1': 'localhost',                   # Jarvis (Mac)
    'a2': 'shivansh@35.206.121.170',   # GCP
    'Oracle': 'ubuntu@84.8.159.123',
    'Jarvis': 'localhost',
    'GCP': 'shivansh@35.206.121.170',
}

# Action script search paths
ACTION_PATHS = [
    os.path.expanduser("~/installations/language/v1/actions"),
    os.path.expanduser("~/.hermes/skills"),
]


class Runtime:
    """Zero-LLM φ-code execution engine."""
    
    def __init__(self, dict_path: Optional[str] = None):
        self.codec = Codec(dict_path)
    
    def execute(self, expression: str, verbose: bool = False) -> dict:
        """Execute a φ-expression and return results.
        
        Returns: {status, steps[], overall, errors[]}
        """
        steps = self._parse(expression)
        results = []
        errors = []
        overall = 's7'
        
        for i, step in enumerate(steps):
            if verbose:
                print(f"[{i+1}/{len(steps)}] {step.get('op')}: {step.get('action', '')}")
            
            try:
                result = self._execute_step(step)
                results.append(result)
                
                if not result.get('ok'):
                    errors.append(result.get('error', f'Step {i+1} failed'))
                    
                    # Conditional: on failure, try else branch
                    if step.get('op') == 'COND' and step.get('else_action'):
                        if verbose:
                            print(f"  → else: {step['else_action']}")
                        fallback = {'op': 'SEQ', 'action': step['else_action'], 'node': step.get('node', 'a1')}
                        result = self._execute_step(fallback)
                        results.append(result)
                        if not result.get('ok'):
                            overall = 's6'
                            break
                elif step.get('op') == 'COND' and step.get('then_action'):
                    # Success: run then branch
                    if verbose:
                        print(f"  → then: {step['then_action']}")
                    follow = {'op': 'SEQ', 'action': step['then_action'], 'node': step.get('node', 'a1')}
                    self._execute_step(follow)
                
                # Notify after step
                if step.get('notify'):
                    self._notify(step['notify'], step.get('action', ''), result.get('ok', False))
                    
            except Exception as e:
                errors.append(str(e))
                results.append({'ok': False, 'error': str(e)})
                overall = 's6'
                break
        
        return {
            'status': overall,
            'steps': results,
            'overall': overall,
            'errors': errors,
            'steps_total': len(steps),
            'steps_ok': sum(1 for r in results if r.get('ok')),
        }
    
    def _parse(self, expression: str) -> list:
        """Parse φ-expression into step dicts.
        
        Example: "dwg*3?r01>tg ::Oracle" →
        [{op: RETRY, action: deploy, count: 3, notify: tg, cond: r01, node: Oracle}]
        """
        steps = []
        tokens = re.split(r'\s+', expression.strip())
        current_node = 'a1'
        
        for token in tokens:
            if not token:
                continue
            
            step = {'op': 'SEQ'}
            
            # ---- Node target: token::NodeName ----
            if '::' in token:
                parts = token.split('::')
                token = parts[0]
                current_node = parts[1]
            step['node'] = current_node
            
            # ---- Retry: action*N ----
            if '*' in token:
                parts = token.split('*')
                token = parts[0]
                step['op'] = 'RETRY'
                retry_part = parts[1] if len(parts) > 1 else '3'
                num = re.match(r'\d+', retry_part)
                step['count'] = int(num.group()) if num else 3
                remaining = retry_part[num.end():] if num else ''
                if remaining:
                    token = token + remaining
            
            # ---- Notify: >tg ----
            if '>' in token:
                parts = token.split('>')
                token = parts[0]
                step['notify'] = parts[1] if len(parts) > 1 else 'tg'
            
            # ---- Timeout: @30s ----
            if '@' in token:
                parts = token.split('@')
                token = parts[0]
                timeout_part = parts[1] if len(parts) > 1 else '30s'
                num = re.match(r'(\d+)s?', timeout_part)
                step['timeout'] = int(num.group(1)) if num else 30
            
            # ---- Mode: /bg or /fg ----
            if '/' in token:
                parts = token.split('/')
                token = parts[0]
                step['mode'] = parts[1] if len(parts) > 1 else 'fg'
            
            # ---- Conditional: action?then:else ----
            if '?' in token:
                parts = token.split('?')
                token = parts[0]
                step['op'] = 'COND'
                cond_part = parts[1] if len(parts) > 1 else ''
                if ':' in cond_part:
                    then_else = cond_part.split(':')
                    step['then_action'] = self.codec.decode(then_else[0]) if CODE_RE.match(then_else[0]) else then_else[0]
                    step['else_action'] = self.codec.decode(then_else[1]) if len(then_else) > 1 and CODE_RE.match(then_else[1]) else then_else[1] if len(then_else) > 1 else None
            
            # ---- Pipe: a|b|c ----
            if '|' in token and '?' not in token:
                parts = token.split('|')
                token = parts[0]
                step['op'] = 'PIPE'
                step['pipe_actions'] = [
                    self.codec.decode(p) if CODE_RE.match(p) else p
                    for p in parts[1:]
                ]
            
            # ---- Parallel: a,b,c ----
            if ',' in token:
                parts = token.split(',')
                token = parts[0]
                step['op'] = 'PAR'
                step['par_actions'] = [
                    self.codec.decode(p) if CODE_RE.match(p) else p
                    for p in parts[1:]
                ]
            
            # Decode action
            if CODE_RE.match(token):
                step['action'] = self.codec.decode(token)
            else:
                step['action'] = token
            
            steps.append(step)
        
        return steps
    
    def _execute_step(self, step: dict) -> dict:
        """Execute a single step and return result."""
        op = step.get('op', 'SEQ')
        
        if op == 'RETRY':
            return self._retry(step)
        elif op == 'PIPE':
            return self._pipeline(step)
        elif op == 'PAR':
            return self._parallel(step)
        else:  # SEQ, COND
            return self._run_action(step)
    
    def _run_action(self, step: dict) -> dict:
        """Run a single action on the target node."""
        action = step.get('action', '')
        node = step.get('node', 'a1')
        mode = step.get('mode', 'fg')
        timeout = step.get('timeout', 60)
        
        cmd = self._build_command(action, node)
        
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                timeout=timeout, cwd=os.path.expanduser("~/installations/language/v1")
            )
            ok = result.returncode == 0
            return {
                'ok': ok,
                'action': action,
                'node': node,
                'stdout': result.stdout.strip()[-500:],  # last 500 chars
                'stderr': result.stderr.strip()[-200:],
                'exit_code': result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {'ok': False, 'action': action, 'error': f'Timeout ({timeout}s)'}
        except Exception as e:
            return {'ok': False, 'action': action, 'error': str(e)}
    
    def _retry(self, step: dict) -> dict:
        """Retry an action up to N times."""
        count = step.get('count', 3)
        action = step.get('action', '')
        
        for attempt in range(1, count + 1):
            result = self._run_action(step)
            if result.get('ok'):
                result['attempts'] = attempt
                return result
            time.sleep(1)  # wait 1s between retries
        
        return {'ok': False, 'action': action, 'error': f'Failed after {count} attempts'}
    
    def _pipeline(self, step: dict) -> dict:
        """Pipe stdout of one command to stdin of next."""
        actions = [step.get('action', '')] + step.get('pipe_actions', [])
        node = step.get('node', 'a1')
        
        cmds = [self._build_command(a, node) for a in actions]
        pipe_cmd = ' | '.join(cmds)
        
        try:
            result = subprocess.run(
                pipe_cmd, shell=True, capture_output=True, text=True,
                cwd=os.path.expanduser("~/installations/language/v1")
            )
            return {
                'ok': result.returncode == 0,
                'action': ' | '.join(actions),
                'stdout': result.stdout.strip()[-300:],
            }
        except Exception as e:
            return {'ok': False, 'error': str(e)}
    
    def _parallel(self, step: dict) -> dict:
        """Run actions in parallel."""
        actions = [step.get('action', '')] + step.get('par_actions', [])
        step_copy = dict(step)
        
        results = []
        with ThreadPoolExecutor(max_workers=min(len(actions), 4)) as executor:
            futures = {}
            for a in actions:
                sc = dict(step_copy)
                sc['action'] = a
                futures[executor.submit(self._run_action, sc)] = a
            
            for future in as_completed(futures):
                results.append(future.result())
        
        all_ok = all(r.get('ok') for r in results)
        return {
            'ok': all_ok,
            'action': f"PAR({', '.join(actions)})",
            'parallel_results': results,
        }
    
    def _build_command(self, action: str, node: str) -> str:
        """Build shell command for an action on a node."""
        # Resolve node to SSH command if remote
        if node in NODE_HOSTS and node not in ('a1', 'Jarvis', 'localhost'):
            host = NODE_HOSTS[node]
            ssh_cmd = f'ssh -o ConnectTimeout=5 -o BatchMode=yes {shlex.quote(host)}'
            return f'{ssh_cmd} "{action}"'
        
        # Local execution: find action script
        script = self._find_script(action)
        if script:
            return script
        return action  # fallback: execute as raw command
    
    def _find_script(self, action: str) -> Optional[str]:
        """Find a shell script matching the action name."""
        action_clean = action.strip().lower().replace(' ', '_')
        
        # Check known shortcuts
        shortcuts = {
            'deploy': '~/installations/language/v1/actions/deploy.sh',
            'restart': '~/installations/language/v1/actions/r9_restart.sh',
            'notify_tg': 'bash ~/installations/language/v1/actions/v5_notify_tg.sh',
            'health': '~/installations/language/v1/scripts/heartbeat.py',
            'guard': '~/installations/language/v1/scripts/guard.py',
            'beacon': '~/installations/language/v1/scripts/cloud_chat.py',
        }
        
        if action_clean in shortcuts:
            return os.path.expanduser(shortcuts[action_clean])
        
        # Search action paths
        for path in ACTION_PATHS:
            candidate = os.path.expanduser(f'{path}/{action_clean}')
            if os.path.isfile(candidate):
                return candidate
            # Also check .sh extension
            candidate_sh = os.path.expanduser(f'{path}/{action_clean}.sh')
            if os.path.isfile(candidate_sh):
                return f'bash {candidate_sh}'
        
        return None
    
    def _notify(self, channel: str, action: str, ok: bool):
        """Send notification after step execution."""
        status = 's7' if ok else 's6'
        msg = f'φ:{action},{status}'
        
        if channel == 'tg':
            tg_script = os.path.expanduser(
                "~/installations/language/v1/actions/v5_notify_tg.sh"
            )
            if os.path.isfile(tg_script):
                subprocess.run(
                    ['bash', tg_script, msg],
                    capture_output=True, timeout=5
                )
        elif channel == 'log':
            print(f"[φ-log] {msg}")
        else:
            print(f"[{channel}] {msg}")


# ---- CLI ----
if __name__ == '__main__':
    import sys
    
    r = Runtime()
    
    if len(sys.argv) < 2:
        print("φ-lang v4 Runtime")
        print("Usage:")
        print("  python phi_runtime.py 'dwg*3 ::Oracle'")
        print("  python phi_runtime.py 'c04|r01>tg ::all'")
        print("  python phi_runtime.py --verbose 'b03>tg ::a0,a2'")
        sys.exit(1)
    
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    expression = sys.argv[-1]
    
    result = r.execute(expression, verbose=verbose)
    
    print(f"\n{'='*50}")
    print(f"Expression: {expression}")
    print(f"Overall:    {result['overall']} ({result['steps_ok']}/{result['steps_total']} ok)")
    if result['errors']:
        print(f"Errors:     {len(result['errors'])}")
        for e in result['errors'][:3]:
            print(f"  - {e}")

"""φ-lang v4 Skill Converter v2 — SKILL.md → compact φ_skill.md
Structural compression: keep the essence, drop the noise.
Target: 80% file size reduction, LLM-readable.

Format:
  # skill-name
  cat: category
  act: [c04]deploy [b02]build [r01]test    ← verbs as φ-codes
  dsc: One-line description (all English)    ← LLM still understands
  use: Quick usage example
  pit: Common pitfall
  fal: Fallback method
"""

import os
import re
import sys, argparse, re, os

# Add phi_codec_v4 to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from phi_codec_v4 import Codec


# Use the FULL dictionary for verb encoding — not just 50 hardcoded words
_codec_instance = None

def _get_codec():
    global _codec_instance
    if _codec_instance is None:
        _codec_instance = Codec()
    return _codec_instance


# Stopwords to skip during encoding
_STOPWORDS = {'the','of','and','to','in','a','is','for','on','with','as','at','by','or',
    'an','be','it','no','if','so','we','he','do','go','up','all','but','not',
    'are','was','has','had','can','may','its','new','use','set','get','run',
    'this','that','from','they','have','been','will','also','when','your',
    'each','only','some','more','than','then','them','what','into','over',
    'make','like','just','work','see','way','out','one','two','any','how',
    'about','which','after','other','being','there','these','their','would',
    'could','should','through','between','example','using','such','does',
    'based','default','available','support','include','current','you','i',
    'me','my','our','us','we','here','now','very','too','just','well','need',
    'must','may','also','still','already','always','never','often','much'}


def verb_encode(codec: Codec, text: str) -> str:
    """Encode text to comma-separated φ-codes only, skip stopwords."""
    words = re.findall(r'[a-z0-9]+', text.lower())
    codes = []
    for w in words:
        if w not in _STOPWORDS:
            code = codec.look_up(w)
            if code:
                codes.append(code)
    return ','.join(codes[:20]) if codes else '?'


def extract_yaml(skill_text: str) -> dict:
    """Extract frontmatter: name, description, category."""
    yaml = {}
    in_frontmatter = False
    for line in skill_text.split('\n')[:50]:
        s = line.strip()
        if s == '---':
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter and ':' in s:
            key, val = s.split(':', 1)
            key = key.strip().lower()
            val = val.strip().strip('"').strip("'")
            if key in ('name', 'description', 'category', 'source_repo'):
                if key == 'source_repo': key = 'source'
                yaml[key] = val
    
    # Fallback: scan all YAML blocks for description (vault skills have multiple blocks)
    if not yaml.get('description'):
        in_second = False
        for line in skill_text.split('\n'):
            s = line.strip()
            if s == '---':
                in_second = not in_second
                if not in_second and yaml.get('description'):
                    break
                continue
            if in_second and s.startswith('description:') or s.startswith('"description":'):
                val = s.split(':', 1)[1].strip().strip('"').strip("'")
                yaml['description'] = val
                break
            if in_second and s.startswith('name:'):
                yaml['name'] = s.split(':', 1)[1].strip().strip('"').strip("'")
            if in_second and s.startswith('category:'):
                yaml['category'] = s.split(':', 1)[1].strip().strip('"').strip("'")
    
    # Fallback: body paragraph
    if not yaml.get('description'):
        for line in skill_text.split('\n'):
            s = line.strip()
            if s and not s.startswith('#') and not s.startswith('---') and not s.startswith('```'):
                yaml['description'] = s[:200]
                break
    return yaml


def extract_pitfall(skill_text: str) -> str:
    """Extract first pitfall/warning line."""
    for line in skill_text.split('\n'):
        if re.search(r'(pitfall|warning|caution|⚠️|limitation|known issue)', line, re.IGNORECASE):
            return line.strip()[:120]
    return ''


def extract_fallback(skill_text: str) -> str:
    """Extract fallback/tier2 mention."""
    for line in skill_text.split('\n'):
        if re.search(r'(fallback|tier\s*2|alternative|backup method)', line, re.IGNORECASE):
            return line.strip()[:120]
    return ''


def extract_usage(skill_text: str) -> str:
    """Extract a usage example (code block or inline)."""
    in_block = False
    for line in skill_text.split('\n'):
        if line.strip().startswith('```') or line.strip().startswith('`'):
            in_block = not in_block
        elif in_block and line.strip():
            return line.strip()[:200]
    # Try to find a CLI command line
    for line in skill_text.split('\n'):
        if re.match(r'^\s*\$\s+', line) or re.match(r'^\s*python\s', line):
            return line.strip()[:200]
    return ''


def convert_skill(skill_path: str, codec: Codec, output_dir: str, skill_num: int) -> str:
    """Convert one SKILL.md to compact φ_skill.md."""
    with open(skill_path, encoding='utf-8', errors='replace') as f:
        text = f.read()
    
    skill_name = os.path.basename(os.path.dirname(skill_path))
    yaml = extract_yaml(text)
    
    category = yaml.get('category', '?')
    source = yaml.get('source', '?')
    description = yaml.get('description', '')
    
    # Smart-encode description
    desc_phi = verb_encode(codec, description)
    
    # Extract actionable words from description
    verbs_found = [w for w in re.findall(r'[a-z]+', description.lower()) if codec.look_up(w) and w not in _STOPWORDS]
    action_line = ','.join(codec.look_up(v) for v in verbs_found[:8] if codec.look_up(v)) or '?'
    
    usage = extract_usage(text)
    pitfall = extract_pitfall(text)
    fallback = extract_fallback(text)
    
    # Build compressed skill
    lines = [f'# {skill_name}']
    if category:
        lines.append(f'cat: {category}')
    lines.append(f'act: {action_line if action_line else "?"}')
    lines.append(f'dsc: {desc_phi[:200]}')
    if usage:
        lines.append(f'use: {verb_encode(codec, usage)[:80]}')
    if pitfall:
        lines.append(f'pit: {verb_encode(codec, pitfall)[:80]}')
    if fallback:
        lines.append(f'fal: {verb_encode(codec, fallback)[:80]}')
    
    phi_skill = '\n'.join(lines) + '\n'
    
    # Create output
    num_str = f'{skill_num:04d}'
    out_skill_dir = os.path.join(output_dir, f'{num_str}-{skill_name}')
    os.makedirs(out_skill_dir, exist_ok=True)
    
    out_path = os.path.join(out_skill_dir, 'phi_skill.md')
    with open(out_path, 'w') as f:
        f.write(phi_skill)
    
    return out_path


def batch_convert(
    codec: Codec,
    source_dirs: list,
    output_base: str,
    max_skills: int = None,
    range_size: int = 900
):
    """Batch convert all skills."""
    all_skills = []
    for src_dir in source_dirs:
        for root, dirs, files in os.walk(src_dir):
            if 'SKILL.md' in files:
                all_skills.append((os.path.basename(root), os.path.join(root, 'SKILL.md')))
    
    total = len(all_skills)
    if max_skills:
        all_skills = all_skills[:max_skills]
    
    print(f"Converting {len(all_skills)} of {total} skills...")
    
    for i, (name, path) in enumerate(all_skills):
        skill_num = i + 1
        range_start = ((skill_num - 1) // range_size) * range_size + 1
        range_end = range_start + range_size - 1
        range_dir = os.path.join(output_base, f'{range_start}-{range_end}')
        
        out_path = convert_skill(path, codec, range_dir, skill_num)
        
        if (i + 1) % 100 == 0:
            print(f"  {i+1}/{len(all_skills)} — {name}")
        
        # Copy scripts/references
        skill_dir = os.path.dirname(path)
        for subdir in ['scripts', 'references', 'templates', 'assets']:
            src_sub = os.path.join(skill_dir, subdir)
            if os.path.isdir(src_sub):
                dst_sub = os.path.join(os.path.dirname(out_path), subdir)
                if not os.path.exists(dst_sub):
                    os.system(f'cp -r "{src_sub}" "{dst_sub}" 2>/dev/null')
    
    print(f"Done. {len(all_skills)} skills converted to {output_base}")


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Convert SKILL.md to compact φ-skill')
    p.add_argument('--skill', help='Single skill name')
    p.add_argument('--batch', type=int, help='Convert N skills')
    p.add_argument('--all', action='store_true', help='Convert all')
    p.add_argument('--sample', action='store_true', help='Convert 5 samples')
    p.add_argument('--expand-dict', action='store_true', help='Find missing words, codify (longest first), update dict, reconvert')
    args = p.parse_args()
    
    codec = Codec()
    output_base = os.path.expanduser("~/Hermes v3/v4/home/a/all skills/v2")
    source_dirs = [os.path.expanduser("~/.hermes/skills")]
    
    if args.skill:
        for src in source_dirs:
            for root, dirs, files in os.walk(src):
                if 'SKILL.md' in files and os.path.basename(root) == args.skill:
                    out = convert_skill(os.path.join(root, 'SKILL.md'), codec, output_base, 1)
                    print(f"Converted: {out}")
                    with open(out) as f:
                        print(f.read())
                    sys.exit(0)
        print(f"Not found: {args.skill}")
    
    elif args.sample:
        batch_convert(codec, source_dirs, output_base, max_skills=5)
    
    elif args.all:
        batch_convert(codec, source_dirs, output_base)
    
    elif args.expand_dict:
        # Scan all v1 skills for unrecognized words ≥3 chars
        print("Scanning all v1 skills for missing words...")
        src = os.path.expanduser("~/Hermes v3/v4/home/a/all skills/v1")
        new_words = set()
        all_text = ""
        for root, dirs, files in os.walk(src):
            if 'SKILL.md' in files:
                try:
                    with open(os.path.join(root, 'SKILL.md'), encoding='utf-8', errors='replace') as f:
                        all_text += f.read() + "\n"
                except:
                    continue
        
        # Extract words, find unrecognized ones
        for w in re.findall(r'[a-z]{3,}', all_text.lower()):
            if not codec.look_up(w) and w not in _STOPWORDS:
                new_words.add(w)
        
        # Sort by length descending (longest first)
        new_sorted = sorted(new_words, key=lambda x: (-len(x), x))
        
        print(f"Found {len(new_sorted)} unrecognized words ({len(new_sorted)}\u22653 chars)")
        
        if not new_sorted:
            print("Dictionary is complete — nothing to add.")
        else:
            # Load existing codes
            dict_path = os.path.expanduser("~/Hermes v3/v4/home/a/installations/v1/phi-lang/v4/v4.dict")
            existing = set()
            with open(dict_path) as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        existing.add(line.strip().split('=', 1)[1])
            
            # Assign next available codes
            chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
            used_codes = set()
            with open(dict_path) as f:
                for line in f:
                    if '=' in line and not line.startswith('#'):
                        used_codes.add(line.strip().split('=', 1)[0])
            
            # Precompute next available code index
            next_idx = max(
                [chars.index(c[0]) * 1296 + chars.index(c[1]) * 36 + chars.index(c[2])
                 for c in used_codes if len(c) == 3 and all(x in chars for x in c)]
            ) + 1 if used_codes else 0
            
            added = 0
            with open(dict_path, 'a') as f:
                for w in new_sorted:
                    if w in existing:
                        continue
                    # Walk forward to next unused code
                    while next_idx < 46656:
                        c1 = next_idx // 1296; c2 = (next_idx % 1296) // 36; c3 = next_idx % 36
                        code = chars[c1] + chars[c2] + chars[c3]
                        next_idx += 1
                        if code not in used_codes:
                            f.write(f"{code}={w}\n")
                            used_codes.add(code)
                            existing.add(w)
                            added += 1
                            break
            
            print(f"Added {added} new words to dictionary")
            
            # Reload codec with expanded dict
            codec = Codec(dict_path)
            print(f"Dictionary now: {len(codec.code_to_word)} words")
            
            # Reconvert all (both local + archive)
            print("Reconverting all skills with expanded dictionary...")
            all_srcs = [os.path.expanduser("~/.hermes/skills"),
                        os.path.expanduser("~/Hermes v3/v4/home/a/all skills/v1")]
            batch_convert(codec, all_srcs, output_base)
    
    elif args.batch:
        batch_convert(codec, source_dirs, output_base, max_skills=args.batch)
    
    else:
        p.print_help()

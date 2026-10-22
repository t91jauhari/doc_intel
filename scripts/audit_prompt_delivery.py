"""Read-only active-profile compilation audit; no provider requests or credentials."""
import argparse,json,sys
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from sqlalchemy import select
from app.db import SessionLocal,SpiderConnector
from app.domain import latest_config
from app.extraction_prompts import system_instruction,reading_instructions,prompt_manifest,llama_extract_instructions
from app.spider_provider import field_guidance,BASE_URL,MODEL

def audit(org):
    with SessionLocal() as db:
        cfg=latest_config(db,org)
        connector=db.scalar(select(SpiderConnector).where(SpiderConnector.org==org))
        options=connector.options if connector else {}
        url=urlsplit(options.get('base_url',BASE_URL))
        endpoint=urlunsplit((url.scheme,(url.hostname or '')+(':'+str(url.port) if url.port else ''),url.path.rstrip('/')+'/chat/completions','',''))
        profiles=[]
        for name,p in cfg.payload['profiles'].items():
            schema=p['schema'];reading=reading_instructions(p);llama=llama_extract_instructions(p)
            checks={'system_instruction':system_instruction(p) in llama,
                    'parse_prompt':bool(p.get('parse_prompt')) and p['parse_prompt'] in reading and p['parse_prompt'] in llama,
                    'system_prompt':bool(p.get('system_prompt')) and p['system_prompt'] in reading and p['system_prompt'] in llama}
            profiles.append({'profile':name,'checks':checks,'field_description_paths':len(field_guidance(schema)),
                             'manifest':prompt_manifest(p,schema)})
        return {'verification_kind':'Active profile compilation; transport delivery is separately covered by mocked HTTP/SDK tests',
                'config_version':cfg.version,'provider':cfg.payload['provider'],
                'spider_endpoint':endpoint,'spider_model':options.get('model_id',MODEL),
                'sequential_page_extraction':cfg.payload.get('sequential_page_extraction',True),
                'profiles':profiles,'all_profile_prompt_checks_passed':all(all(p['checks'].values()) for p in profiles)}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--org',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    result=audit(a.org)
    Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='profiles'}))
    if not result['all_profile_prompt_checks_passed']:raise SystemExit(1)

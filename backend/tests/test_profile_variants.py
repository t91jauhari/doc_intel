import copy
from sqlalchemy import select
from app.domain import default_config, validate_config, latest_config
from app.db import Config, SessionLocal
from app.profile_variants import add_variants, seed_profile_variants
from app.schema_descriptions import contract


def test_all_candidates_preserve_contract_and_active_settings():
    original = default_config()
    original['profiles']['ektp']['parse_prompt'] = 'Custom local instruction'
    result = add_variants(original)
    assert result['profiles'] == original['profiles']
    assert len(result['profile_variants']) == 7
    count = 0
    for name, bank in result['profile_variants'].items():
        enhanced = bank['enhanced-v1']['profile']
        assert contract(enhanced['schema']) == contract(original['profiles'][name]['schema'])
        count += sum(a['description'] != enhanced['schema']['properties'][key]['description'] for key, a in original['profiles'][name]['schema']['properties'].items())
        assert enhanced['parse_prompt'] != original['profiles'][name]['parse_prompt']
    assert count == 43
    validate_config(result)
    assert add_variants(result) == result


def test_startup_seed_is_idempotent_and_preserves_versions(client):
    with SessionLocal() as db:
        previous = latest_config(db, 'sqe')
        before = copy.deepcopy(previous.payload)
        version = previous.version
    seed_profile_variants()
    seed_profile_variants()
    with SessionLocal() as db:
        current = latest_config(db, 'sqe')
        assert current.version == version
        assert current.payload == before
        assert len(current.payload['profile_variants']) == 12


def test_seed_adds_one_version_without_mutating_old_configuration(client):
    with SessionLocal.begin() as db:
        previous = latest_config(db, 'sqe')
        payload = copy.deepcopy(previous.payload)
        payload.pop('profile_variants')
        payload['profiles']['ektp']['parse_prompt'] = 'Bank custom prompt'
        version = previous.version + 1
        db.add(Config(org='sqe', version=version, payload=payload, published_by='test'))
    seed_profile_variants()
    seed_profile_variants()
    with SessionLocal() as db:
        current = latest_config(db, 'sqe')
        old = db.scalar(select(Config).where(Config.org == 'sqe', Config.version == version))
        assert current.version == version + 1
        assert 'profile_variants' not in old.payload
        assert current.payload['profiles'] == payload['profiles']
        assert current.payload['profile_variants']['ektp']['original-v1']['profile']['parse_prompt'] == 'Bank custom prompt'

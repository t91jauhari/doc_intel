import copy

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.configuration.datasets import (
    DatasetRecord, DatasetReference, DatasetIntegrityError, register_dataset, read_dataset, dataset_catalog,
)


def reference():
    return {'id': 'synthetic-v1', 'source_name': 'Synthetic reference', 'sha256': '0' * 64,
            'samples': [{'id': '1', 'name': 'Synthetic customer'}],
            'rows': [{'id': 'row-1', 'section': 'Identity', 'document_type': 'synthetic', 'label': 'Name',
                      'field': 'name', 'kind': 'text', 'values': {'1': 'Synthetic customer'}}]}


@pytest.fixture
def session():
    engine = create_engine('sqlite://')
    DatasetRecord.__table__.create(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_dataset_ids_are_immutable_and_organization_scoped(session):
    payload = reference()
    first = register_dataset(session, 'one', payload)
    assert register_dataset(session, 'one', copy.deepcopy(payload)) is first
    payload['rows'][0]['values']['1'] = 'Replacement'
    with pytest.raises(DatasetIntegrityError, match='immutable'):
        register_dataset(session, 'one', payload)
    register_dataset(session, 'two', payload)
    assert read_dataset(session, 'one', 'synthetic-v1')['rows'][0]['values']['1'] == 'Synthetic customer'
    assert read_dataset(session, 'two', 'synthetic-v1')['rows'][0]['values']['1'] == 'Replacement'
    with pytest.raises(DatasetIntegrityError, match='not registered'):
        read_dataset(session, 'three', 'synthetic-v1')
    assert 'rows' not in dataset_catalog(session, 'one')[0]


def test_dataset_reads_copy_and_verify_content(session):
    record = register_dataset(session, 'one', reference())
    result = read_dataset(session, 'one', 'synthetic-v1')
    result['samples'].clear()
    assert len(read_dataset(session, 'one', 'synthetic-v1')['samples']) == 1
    record.payload = {**record.payload, 'source_name': 'Tampered'}
    with pytest.raises(DatasetIntegrityError, match='integrity'):
        read_dataset(session, 'one', 'synthetic-v1')


def test_registry_rollout_verifies_baseline_without_fallback(session):
    from app.configuration.dataset_sources import bundled_datasets, import_bundled, resolve_dataset
    from app.configuration.codec import fingerprint
    source = bundled_datasets()
    import_bundled(session, 'one')
    for dataset_id, payload in source.items():
        assert fingerprint(resolve_dataset(session, 'one', dataset_id, mode='verify')) == fingerprint(payload)
        assert fingerprint(resolve_dataset(session, 'one', dataset_id, mode='registry')) == fingerprint(payload)
    for mode in ['bundled', 'verify', 'registry']:
        with pytest.raises(DatasetIntegrityError):
            resolve_dataset(session, 'one', 'unregistered', mode=mode)
    assert resolve_dataset(session, 'one', None, mode='registry')['samples'] == []


def test_dataset_catalog_endpoint_and_immutable_import(signed, monkeypatch):
    from dataclasses import replace
    from app.configuration import dataset_routes, dataset_sources
    from app.db import engine
    assert len(signed.get('/api/reference-datasets').json()) == 2
    assert signed.post('/api/reference-datasets', json=reference()).status_code == 409
    DatasetRecord.__table__.create(engine, checkfirst=True)
    monkeypatch.setattr(dataset_routes, 'settings', replace(dataset_routes.settings, dataset_read_mode='registry'))
    from app import settings as settings_module
    monkeypatch.setattr(settings_module, 'settings', replace(settings_module.settings, dataset_read_mode='registry'))
    assert signed.post('/api/reference-datasets', json=reference()).status_code == 201
    assert signed.get('/api/reference-datasets').json()[0]['id'] == 'synthetic-v1'
    changed = reference()
    changed['source_name'] = 'Replacement'
    assert signed.post('/api/reference-datasets', json=changed).status_code == 409


@pytest.mark.parametrize('change', ['duplicate_sample', 'duplicate_row', 'unknown_sample', 'nonfinite'])
def test_invalid_reference_bindings_are_rejected(change):
    payload = reference()
    if change == 'duplicate_sample':
        payload['samples'] *= 2
    elif change == 'duplicate_row':
        payload['rows'] *= 2
    elif change == 'unknown_sample':
        payload['rows'][0]['values']['other'] = 'Unknown'
    else:
        payload['rows'][0]['values']['1'] = float('nan')
    with pytest.raises((ValidationError, ValueError)):
        DatasetReference.model_validate(payload)

"""Configuration writer and startup boundaries, using synthetic data only."""
import ast
import copy
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.configuration import publication
from app.configuration.service import StaleConfiguration
from app.configuration.store import ConfigurationBase, Publication, compile_publication
from app.db import Config, SessionLocal, engine
from app.domain import latest_config
from app.main import app


def test_all_config_inserts_use_persistence_boundary():
    root = Path(__file__).parents[1] / "app"
    violations = []
    for path in root.rglob("*.py"):
        if path.name == "publication.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add":
                if any(isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == "Config"
                       for arg in node.args):
                    violations.append(str(path.relative_to(root)))
    assert violations == []


def test_api_startup_does_not_publish_business_upgrades(signed):
    with SessionLocal() as db:
        before = db.scalar(select(func.count()).select_from(Config))
    # A missing release would previously trigger a startup publication.
    with SessionLocal.begin() as db:
        current = latest_config(db, "sqe")
        draft = copy.deepcopy(current.payload)
        draft.pop("extraction_quality_release", None)
        publication.persist_revision(db, Config(org="sqe", version=current.version + 1,
            payload=draft, published_by="synthetic"))
    with TestClient(app):
        pass
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(Config)) == before + 1
        assert "extraction_quality_release" not in latest_config(db, "sqe").payload


def test_shared_boundary_rejects_stale_writers_and_rolls_back(signed):
    ConfigurationBase.metadata.create_all(engine)
    try:
        with SessionLocal() as db:
            current = latest_config(db, "sqe")
            version, payload = current.version, copy.deepcopy(current.payload)
        with pytest.raises(RuntimeError, match="rollback"):
            with SessionLocal.begin() as db:
                saved = Config(org="sqe", version=version + 1, payload=payload, published_by="synthetic")
                normalized = publication.persist_revision(db, saved, storage_mode="dual")
                assert compile_publication(db, normalized) == payload
                raise RuntimeError("rollback")
        with SessionLocal() as db:
            assert latest_config(db, "sqe").version == version
            assert db.scalar(select(func.count()).select_from(Publication)) == 0
        with SessionLocal.begin() as db:
            with pytest.raises(StaleConfiguration):
                publication.persist_revision(db, Config(org="sqe", version=version,
                    payload=payload, published_by="synthetic"), storage_mode="dual")
    finally:
        ConfigurationBase.metadata.drop_all(engine)


def test_reprocessing_guidance_uses_dual_storage(signed, monkeypatch):
    from app import settings as settings_module
    from test_profile_guidance import test_guidance_publishes_only_target_profile_and_reaches_future_uploads
    ConfigurationBase.metadata.create_all(engine)
    monkeypatch.setattr(settings_module, "settings", replace(settings_module.settings, configuration_storage_mode="dual"))
    try:
        test_guidance_publishes_only_target_profile_and_reaches_future_uploads(signed, monkeypatch)
        with SessionLocal() as db:
            current = latest_config(db, "sqe")
            normalized = db.scalar(select(Publication).where(Publication.source_config_id == current.id))
            assert normalized is not None
            assert compile_publication(db, normalized) == current.payload
    finally:
        ConfigurationBase.metadata.drop_all(engine)

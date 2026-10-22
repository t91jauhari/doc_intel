from app.db import Inbox, SessionLocal


def test_inbox_pagination_preserves_scope_and_read_is_not_resolution(signed):
    branch = signed.get('/api/branches').json()[0]['id']
    with SessionLocal.begin() as db:
        for i in range(105):
            db.add(Inbox(org='sqe', branch_id=branch, case_id='review-case', key=f'page-{i}', title='Review evidence', body='Source needs review', severity='REVIEW', created_at=1000 + i))
        db.add(Inbox(org='other', branch_id=branch, case_id='foreign', key='foreign-item', title='Private', body='Private', severity='REVIEW', created_at=9999))
        db.add(Inbox(org='sqe', branch_id=branch, case_id='resolved', key='resolved-item', title='Done', body='Done', severity='INFO', resolved=True, created_at=9999))
    first = signed.get('/api/inbox').json()
    second = signed.get('/api/inbox?offset=100').json()
    assert len(first) == 100 and len(second) == 5
    assert not set(x['id'] for x in first) & set(x['id'] for x in second)
    assert all(x['case_id'] == 'review-case' for x in first + second)
    assert signed.get('/api/inbox?offset=-1').status_code == 422
    assert signed.post(f"/api/inbox/{first[0]['id']}/read").status_code == 200
    updated = signed.get('/api/inbox').json()
    assert len(updated) == 100 and updated[0]['read']
    with SessionLocal() as db:
        assert not db.get(Inbox, first[0]['id']).resolved

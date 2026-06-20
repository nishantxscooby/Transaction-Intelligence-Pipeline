import json
from datetime import datetime
from .db import init_db
try:
    from .db import SessionLocal
    from .db import text
    SQLALCHEMY = True
except Exception:
    SQLALCHEMY = False
    import sqlite3
    from .db import get_sqlite_conn


def create_job(job_id, filename, status='PENDING'):
    init_db()
    if SQLALCHEMY:
        with SessionLocal() as session:
            session.execute(
                text("INSERT INTO jobs(job_id,filename,status,created_at) VALUES (:job_id,:filename,:status,:created_at)"),
                {'job_id': job_id, 'filename': filename, 'status': status, 'created_at': datetime.utcnow().isoformat()}
            )
            session.commit()
    else:
        conn = get_sqlite_conn()
        conn.execute('INSERT INTO jobs(job_id,filename,status,created_at) VALUES (?,?,?,?)', (job_id, filename, status, datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()


def list_jobs(status=None):
    init_db()
    if SQLALCHEMY:
        with SessionLocal() as session:
            if status:
                rows = session.execute(text("SELECT job_id,filename,status,created_at FROM jobs WHERE status=:status"), {'status': status}).all()
            else:
                rows = session.execute(text("SELECT job_id,filename,status,created_at FROM jobs")).all()
            return [{'job_id': r[0], 'filename': r[1], 'status': r[2], 'created_at': r[3]} for r in rows]
    else:
        conn = get_sqlite_conn()
        cur = conn.cursor()
        if status:
            cur.execute('SELECT job_id,filename,status,created_at FROM jobs WHERE status=?', (status,))
        else:
            cur.execute('SELECT job_id,filename,status,created_at FROM jobs')
        rows = cur.fetchall()
        conn.close()
        return [{'job_id': r[0], 'filename': r[1], 'status': r[2], 'created_at': r[3]} for r in rows]


def get_job(job_id):
    init_db()
    if SQLALCHEMY:
        with SessionLocal() as session:
            r = session.execute(text("SELECT job_id,filename,status,row_count,created_at,results FROM jobs WHERE job_id=:job_id"), {'job_id': job_id}).first()
            if not r:
                return None
            res = r[5]
            parsed = None
            if res:
                try:
                    parsed = json.loads(res)
                except Exception:
                    # don't raise from malformed DB value; return raw string in 'results_raw' and log
                    import logging
                    logging.getLogger('app.crud').warning('Failed to parse results JSON for job %s', job_id)
                    parsed = None
            return {'job_id': r[0], 'filename': r[1], 'status': r[2], 'row_count': r[3], 'created_at': r[4], 'results': parsed}
    else:
        conn = get_sqlite_conn()
        cur = conn.cursor()
        cur.execute('SELECT job_id,filename,status,row_count,created_at,results FROM jobs WHERE job_id=?', (job_id,))
        r = cur.fetchone()
        conn.close()
        if not r:
            return None
        res = r[5]
        parsed = None
        if res:
            try:
                parsed = json.loads(res)
            except Exception:
                import logging
                logging.getLogger('app.crud').warning('Failed to parse results JSON for job %s', job_id)
                parsed = None
        return {'job_id': r[0], 'filename': r[1], 'status': r[2], 'row_count': r[3], 'created_at': r[4], 'results': parsed}


def set_job_status(job_id, status):
    init_db()
    if SQLALCHEMY:
        with SessionLocal() as session:
            session.execute(text("UPDATE jobs SET status=:status WHERE job_id=:job_id"), {'status': status, 'job_id': job_id})
            session.commit()
    else:
        conn = get_sqlite_conn()
        conn.execute('UPDATE jobs SET status=? WHERE job_id=?', (status, job_id))
        conn.commit()
        conn.close()


def set_job_results(job_id, results, row_count=None):
    init_db()
    if SQLALCHEMY:
        with SessionLocal() as session:
            session.execute(text("UPDATE jobs SET results=:results, row_count=:row_count WHERE job_id=:job_id"), {'results': json.dumps(results), 'row_count': row_count, 'job_id': job_id})
            session.commit()
    else:
        conn = get_sqlite_conn()
        conn.execute('UPDATE jobs SET results=?, row_count=? WHERE job_id=?', (json.dumps(results), row_count, job_id))
        conn.commit()
        conn.close()


def get_results(job_id):
    job = get_job(job_id)
    return job.get('results')


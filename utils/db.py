import sqlite3
import pandas as pd
import json
import os
from typing import Dict, List, Tuple, Optional, Any
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

DEFAULT_DB_NAME = "grc.db"

# =============================================================================
# DATABASE PATH & CONNECTION
# =============================================================================

def get_db_path() -> str:
    return os.environ.get("GRC_DB_PATH", DEFAULT_DB_NAME)


def db_exists(db_path: str = None) -> bool:
    path = db_path or get_db_path()
    return os.path.exists(path)


def init_db(db_path: str = None) -> bool:
    """Initialize the database if it doesn't exist."""
    path = db_path or get_db_path()
    if os.path.exists(path):
        return True
    return False


@contextmanager
def get_connection(db_path: str = None):
    path = db_path or get_db_path()
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
    finally:
        conn.close()


# =============================================================================
# COMPLIANCE SOURCE MANAGEMENT
# =============================================================================

def get_all_compliance_sources(db_path: str = None) -> List[Dict]:
    """Get all compliance sources/frameworks."""
    if not db_exists(db_path):
        return []
    
    with get_connection(db_path) as conn:
        # Check if table exists
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='compliance_sources'
        """)
        if not cursor.fetchone():
            return []
        
        rows = conn.execute("""
            SELECT 
                id, name, short_name, description, version,
                source_file, control_count, evidence_count,
                is_active, color, created_at
            FROM compliance_sources
            ORDER BY name
        """).fetchall()
        
        return [dict(row) for row in rows]


def get_active_compliance_sources(db_path: str = None) -> List[Dict]:
    """Get only active compliance sources."""
    if not db_exists(db_path):
        return []
    
    with get_connection(db_path) as conn:
        cursor = conn.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='compliance_sources'
        """)
        if not cursor.fetchone():
            return []
        
        rows = conn.execute("""
            SELECT 
                id, name, short_name, description, version,
                source_file, control_count, evidence_count,
                is_active, color, created_at
            FROM compliance_sources
            WHERE is_active = 1
            ORDER BY name
        """).fetchall()
        
        return [dict(row) for row in rows]


def get_compliance_source_by_id(source_id: int, db_path: str = None) -> Optional[Dict]:
    """Get a specific compliance source by ID."""
    if not db_exists(db_path):
        return None
    
    with get_connection(db_path) as conn:
        row = conn.execute("""
            SELECT * FROM compliance_sources WHERE id = ?
        """, (source_id,)).fetchone()
        
        return dict(row) if row else None


def create_compliance_source(
    name: str,
    short_name: str = None,
    description: str = None,
    version: str = None,
    source_file: str = None,
    color: str = '#667eea',
    db_path: str = None
) -> int:
    """Create a new compliance source. Returns the new ID."""
    with get_connection(db_path) as conn:
        cursor = conn.execute("""
            INSERT INTO compliance_sources (name, short_name, description, version, source_file, color)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, short_name or name[:10], description, version, source_file, color))
        conn.commit()
        return cursor.lastrowid


def update_compliance_source(
    source_id: int,
    name: str = None,
    short_name: str = None,
    description: str = None,
    version: str = None,
    is_active: bool = None,
    color: str = None,
    db_path: str = None
) -> bool:
    """Update a compliance source."""
    updates = []
    params = []
    
    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if short_name is not None:
        updates.append("short_name = ?")
        params.append(short_name)
    if description is not None:
        updates.append("description = ?")
        params.append(description)
    if version is not None:
        updates.append("version = ?")
        params.append(version)
    if is_active is not None:
        updates.append("is_active = ?")
        params.append(1 if is_active else 0)
    if color is not None:
        updates.append("color = ?")
        params.append(color)
    
    if not updates:
        return False
    
    updates.append("updated_at = CURRENT_TIMESTAMP")
    params.append(source_id)
    
    with get_connection(db_path) as conn:
        conn.execute(f"""
            UPDATE compliance_sources
            SET {', '.join(updates)}
            WHERE id = ?
        """, params)
        conn.commit()
        return True


def update_compliance_source_counts(source_id: int, db_path: str = None):
    """Update the control and evidence counts for a source."""
    with get_connection(db_path) as conn:
        # Count controls
        control_count = conn.execute("""
            SELECT COUNT(*) FROM controls WHERE source_id = ?
        """, (source_id,)).fetchone()[0]
        
        # Count evidence
        evidence_count = conn.execute("""
            SELECT COUNT(*) FROM evidence WHERE source_id = ?
        """, (source_id,)).fetchone()[0]
        
        # Update
        conn.execute("""
            UPDATE compliance_sources
            SET control_count = ?, evidence_count = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (control_count, evidence_count, source_id))
        conn.commit()


def delete_compliance_source(source_id: int, db_path: str = None) -> bool:
    """Delete a compliance source and all its data."""
    with get_connection(db_path) as conn:
        # Delete control-evidence links first
        conn.execute("""
            DELETE FROM control_evidence 
            WHERE control_id IN (SELECT id FROM controls WHERE source_id = ?)
        """, (source_id,))
        
        # Delete controls
        conn.execute("DELETE FROM controls WHERE source_id = ?", (source_id,))
        
        # Delete evidence
        conn.execute("DELETE FROM evidence WHERE source_id = ?", (source_id,))
        
        # Delete domains
        conn.execute("DELETE FROM domains WHERE source_id = ?", (source_id,))
        
        # Delete import history
        conn.execute("DELETE FROM import_history WHERE source_id = ?", (source_id,))
        
        # Delete the source
        conn.execute("DELETE FROM compliance_sources WHERE id = ?", (source_id,))
        
        conn.commit()
        return True


def toggle_compliance_source(source_id: int, db_path: str = None) -> bool:
    """Toggle active status of a compliance source."""
    with get_connection(db_path) as conn:
        conn.execute("""
            UPDATE compliance_sources
            SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (source_id,))
        conn.commit()
        return True


# =============================================================================
# OVERVIEW STATS (with source filtering)
# =============================================================================

def get_overview_stats(db_path: str = None, source_ids: List[int] = None) -> Dict[str, Any]:
    """Get comprehensive overview statistics, optionally filtered by source."""
    if not db_exists(db_path):
        return {'controls': 0, 'evidence': 0, 'domains': 0, 'frameworks': 0, 'coverage_pct': 0}
    
    with get_connection(db_path) as conn:
        # Check if source_id column exists (for migration compatibility)
        has_source_id = _table_has_column(conn, 'controls', 'source_id')
        
        # Build WHERE clause components
        source_filter = ""
        params = []
        
        if has_source_id and source_ids:
            placeholders = ','.join(['?'] * len(source_ids))
            source_filter = f"source_id IN ({placeholders})"
            params = list(source_ids)
        
        # Count controls
        if source_filter:
            controls = conn.execute(f"""
                SELECT COUNT(*) FROM controls WHERE {source_filter}
            """, params).fetchone()[0]
        else:
            controls = conn.execute("SELECT COUNT(*) FROM controls").fetchone()[0]
        
        # Count evidence
        if source_filter:
            evidence = conn.execute(f"""
                SELECT COUNT(*) FROM evidence WHERE {source_filter}
            """, params).fetchone()[0]
        else:
            evidence = conn.execute("SELECT COUNT(*) FROM evidence").fetchone()[0]
        
        # Count domains
        if source_filter:
            domains = conn.execute(f"""
                SELECT COUNT(*) FROM domains WHERE {source_filter}
            """, params).fetchone()[0]
        else:
            domains = conn.execute("SELECT COUNT(*) FROM domains").fetchone()[0]
        
        # Count unique frameworks from mappings
        # FIX: Properly build the WHERE clause to avoid double WHERE
        if source_filter:
            rows = conn.execute(f"""
                SELECT mappings FROM controls 
                WHERE {source_filter} AND mappings IS NOT NULL
            """, params).fetchall()
        else:
            rows = conn.execute("""
                SELECT mappings FROM controls WHERE mappings IS NOT NULL
            """).fetchall()
        
        frameworks = set()
        for row in rows:
            try:
                mappings = json.loads(row[0])
                frameworks.update(mappings.keys())
            except:
                pass
        
        # Evidence coverage
        if has_source_id and source_ids:
            placeholders = ','.join(['?'] * len(source_ids))
            controls_with_evidence = conn.execute(f"""
                SELECT COUNT(DISTINCT ce.control_id) 
                FROM control_evidence ce
                JOIN controls c ON ce.control_id = c.id
                WHERE c.source_id IN ({placeholders})
            """, params).fetchone()[0]
        else:
            controls_with_evidence = conn.execute("""
                SELECT COUNT(DISTINCT control_id) FROM control_evidence
            """).fetchone()[0]
        
        coverage_pct = (controls_with_evidence / controls * 100) if controls > 0 else 0
        
        return {
            'controls': controls,
            'evidence': evidence,
            'domains': domains,
            'frameworks': len(frameworks),
            'coverage_pct': coverage_pct,
            'controls_with_evidence': controls_with_evidence
        }


def get_quick_insights(db_path: str = None, source_ids: List[int] = None) -> Dict[str, Any]:
    """Get quick insights for dashboard, filtered by source."""
    if not db_exists(db_path):
        return {}
    
    with get_connection(db_path) as conn:
        has_source_id = _table_has_column(conn, 'controls', 'source_id')
        
        # Build filter
        source_filter = ""
        domain_source_filter = ""
        params = []
        
        if has_source_id and source_ids:
            placeholders = ','.join(['?'] * len(source_ids))
            source_filter = f"AND c.source_id IN ({placeholders})"
            domain_source_filter = f"AND d.source_id IN ({placeholders})"
            params = list(source_ids)
        
        # Top domains
        top_domains = conn.execute(f"""
            SELECT d.name, COUNT(c.id) as cnt
            FROM domains d
            LEFT JOIN controls c ON c.domain_id = d.id
            WHERE 1=1 {domain_source_filter}
            GROUP BY d.id
            ORDER BY cnt DESC
            LIMIT 10
        """, params).fetchall()
        
        # Missing guidance
        missing_guidance = conn.execute(f"""
            SELECT COUNT(*) FROM controls c
            WHERE (guidance IS NULL OR TRIM(guidance) = '')
            {source_filter}
        """, params).fetchone()[0]
        
        # Missing evidence
        missing_evidence = conn.execute(f"""
            SELECT COUNT(*) FROM controls c
            WHERE NOT EXISTS (
                SELECT 1 FROM control_evidence ce WHERE ce.control_id = c.id
            )
            {source_filter}
        """, params).fetchone()[0]
        
        # Control types distribution
        type_dist = conn.execute(f"""
            SELECT type, COUNT(*) as cnt
            FROM controls c
            WHERE type IS NOT NULL AND TRIM(type) != ''
            {source_filter}
            GROUP BY type
            ORDER BY cnt DESC
        """, params).fetchall()
        
        return {
            'top_domains': [(r[0], r[1]) for r in top_domains],
            'missing_guidance': missing_guidance,
            'missing_evidence': missing_evidence,
            'type_distribution': [(r[0], r[1]) for r in type_dist]
        }


# =============================================================================
# DATA RETRIEVAL (with source filtering)
# =============================================================================

def get_all_domains(db_path: str = None, source_ids: List[int] = None) -> List[str]:
    """Get all domain names, filtered by source."""
    if not db_exists(db_path):
        return []
    
    with get_connection(db_path) as conn:
        has_source_id = _table_has_column(conn, 'domains', 'source_id')
        
        if has_source_id and source_ids:
            placeholders = ','.join(['?'] * len(source_ids))
            rows = conn.execute(f"""
                SELECT DISTINCT name FROM domains 
                WHERE source_id IN ({placeholders})
                ORDER BY name
            """, source_ids).fetchall()
        else:
            rows = conn.execute("SELECT name FROM domains ORDER BY name").fetchall()
        
        return [r[0] for r in rows]


def get_all_control_types(db_path: str = None, source_ids: List[int] = None) -> List[str]:
    """Get all distinct control types, filtered by source."""
    if not db_exists(db_path):
        return []
    
    with get_connection(db_path) as conn:
        has_source_id = _table_has_column(conn, 'controls', 'source_id')
        
        query = """
            SELECT DISTINCT type FROM controls 
            WHERE type IS NOT NULL AND TRIM(type) != ''
        """
        params = []
        
        if has_source_id and source_ids:
            placeholders = ','.join(['?'] * len(source_ids))
            query += f" AND source_id IN ({placeholders})"
            params = list(source_ids)
        
        query += " ORDER BY type"
        rows = conn.execute(query, params).fetchall()
        return [r[0] for r in rows]


def get_all_themes(db_path: str = None, source_ids: List[int] = None) -> List[str]:
    """Get all distinct themes, filtered by source."""
    if not db_exists(db_path):
        return []
    
    with get_connection(db_path) as conn:
        has_source_id = _table_has_column(conn, 'controls', 'source_id')
        
        query = """
            SELECT DISTINCT theme FROM controls 
            WHERE theme IS NOT NULL AND TRIM(theme) != ''
        """
        params = []
        
        if has_source_id and source_ids:
            placeholders = ','.join(['?'] * len(source_ids))
            query += f" AND source_id IN ({placeholders})"
            params = list(source_ids)
        
        query += " ORDER BY theme"
        rows = conn.execute(query, params).fetchall()
        return [r[0] for r in rows]


def get_all_frameworks(db_path: str = None, source_ids: List[int] = None) -> List[str]:
    """Extract all unique frameworks from mappings, filtered by source."""
    if not db_exists(db_path):
        return []
    
    with get_connection(db_path) as conn:
        has_source_id = _table_has_column(conn, 'controls', 'source_id')
        
        query = "SELECT mappings FROM controls WHERE mappings IS NOT NULL"
        params = []
        
        if has_source_id and source_ids:
            placeholders = ','.join(['?'] * len(source_ids))
            query += f" AND source_id IN ({placeholders})"
            params = list(source_ids)
        
        rows = conn.execute(query, params).fetchall()
        
        frameworks = set()
        for row in rows:
            try:
                mappings = json.loads(row[0])
                frameworks.update(mappings.keys())
            except:
                pass
        return sorted(list(frameworks))


def search_controls(
    db_path: str = None,
    source_ids: List[int] = None,
    search_term: str = None,
    domains: List[str] = None,
    types: List[str] = None,
    themes: List[str] = None,
    frameworks: List[str] = None,
    has_evidence: bool = None,
    has_guidance: bool = None,
    limit: int = 500
) -> pd.DataFrame:
    """Advanced control search with multiple filters."""
    if not db_exists(db_path):
        return pd.DataFrame()
    
    with get_connection(db_path) as conn:
        has_source_id = _table_has_column(conn, 'controls', 'source_id')
        
        query = """
            SELECT 
                c.id,
                c.ccf_id,
                c.title,
                c.description,
                c.type,
                c.theme,
                c.guidance,
                c.testing,
                c.mappings,
                d.name as domain,
                (SELECT COUNT(*) FROM control_evidence ce WHERE ce.control_id = c.id) as evidence_count
        """
        
        # Add source info if available
        if has_source_id:
            query += ", cs.name as source_name, cs.short_name as source_short"
        
        query += """
            FROM controls c
            LEFT JOIN domains d ON c.domain_id = d.id
        """
        
        if has_source_id:
            query += " LEFT JOIN compliance_sources cs ON c.source_id = cs.id"
        
        query += " WHERE 1=1"
        params = []
        
        # Source filter
        if has_source_id and source_ids:
            placeholders = ','.join(['?'] * len(source_ids))
            query += f" AND c.source_id IN ({placeholders})"
            params.extend(source_ids)
        
        # Search term
        if search_term and search_term.strip():
            search = f"%{search_term.strip()}%"
            query += """
                AND (
                    c.ccf_id LIKE ? OR
                    c.title LIKE ? OR
                    c.description LIKE ? OR
                    c.guidance LIKE ? OR
                    c.testing LIKE ?
                )
            """
            params.extend([search] * 5)
        
        # Domain filter
        if domains:
            placeholders = ','.join(['?'] * len(domains))
            query += f" AND d.name IN ({placeholders})"
            params.extend(domains)
        
        # Type filter
        if types:
            placeholders = ','.join(['?'] * len(types))
            query += f" AND c.type IN ({placeholders})"
            params.extend(types)
        
        # Theme filter
        if themes:
            placeholders = ','.join(['?'] * len(themes))
            query += f" AND c.theme IN ({placeholders})"
            params.extend(themes)
        
        # Evidence filter
        if has_evidence is True:
            query += " AND EXISTS (SELECT 1 FROM control_evidence ce WHERE ce.control_id = c.id)"
        elif has_evidence is False:
            query += " AND NOT EXISTS (SELECT 1 FROM control_evidence ce WHERE ce.control_id = c.id)"
        
        # Guidance filter
        if has_guidance is True:
            query += " AND c.guidance IS NOT NULL AND TRIM(c.guidance) != ''"
        elif has_guidance is False:
            query += " AND (c.guidance IS NULL OR TRIM(c.guidance) = '')"
        
        query += f" ORDER BY d.name, c.ccf_id LIMIT {limit}"
        
        df = pd.read_sql(query, conn, params=params)
    
    # Filter by framework if specified
    if frameworks and not df.empty:
        def has_framework(mappings_json):
            if not mappings_json:
                return False
            try:
                mappings = json.loads(mappings_json)
                return any(fw in mappings for fw in frameworks)
            except:
                return False
        
        df = df[df['mappings'].apply(has_framework)]
    
    return df


def get_control_by_id(ccf_id: str, db_path: str = None, source_id: int = None) -> Optional[Dict]:
    """Get full control details by CCF ID."""
    if not db_exists(db_path):
        return None
    
    with get_connection(db_path) as conn:
        has_source_id = _table_has_column(conn, 'controls', 'source_id')
        
        query = """
            SELECT 
                c.*,
                d.name as domain_name
        """
        
        if has_source_id:
            query += ", cs.name as source_name"
        
        query += """
            FROM controls c
            LEFT JOIN domains d ON c.domain_id = d.id
        """
        
        if has_source_id:
            query += " LEFT JOIN compliance_sources cs ON c.source_id = cs.id"
        
        query += " WHERE c.ccf_id = ?"
        params = [ccf_id]
        
        if has_source_id and source_id:
            query += " AND c.source_id = ?"
            params.append(source_id)
        
        row = conn.execute(query, params).fetchone()
        
        if not row:
            return None
        
        control = dict(row)
        
        # Parse mappings
        if control.get('mappings'):
            try:
                control['mappings'] = json.loads(control['mappings'])
            except:
                control['mappings'] = {}
        else:
            control['mappings'] = {}
        
        # Get evidence
        evidence = conn.execute("""
            SELECT e.ref_id, e.title, e.domain
            FROM evidence e
            JOIN control_evidence ce ON e.id = ce.evidence_id
            WHERE ce.control_id = ?
            ORDER BY e.ref_id
        """, (control['id'],)).fetchall()
        
        control['evidence'] = [dict(e) for e in evidence]
        
        # Get related controls (same domain)
        related_query = """
            SELECT ccf_id, title
            FROM controls
            WHERE domain_id = ? AND ccf_id != ?
        """
        related_params = [control['domain_id'], ccf_id]
        
        if has_source_id and source_id:
            related_query += " AND source_id = ?"
            related_params.append(source_id)
        
        related_query += " ORDER BY ccf_id LIMIT 10"
        
        related = conn.execute(related_query, related_params).fetchall()
        control['related_controls'] = [dict(r) for r in related]
        
        return control


def get_all_evidence(db_path: str = None, source_ids: List[int] = None, search: str = None) -> pd.DataFrame:
    """Get all evidence items, filtered by source."""
    if not db_exists(db_path):
        return pd.DataFrame()
    
    with get_connection(db_path) as conn:
        has_source_id = _table_has_column(conn, 'evidence', 'source_id')
        
        query = """
            SELECT 
                e.ref_id,
                e.title,
                e.domain,
                (SELECT COUNT(*) FROM control_evidence ce WHERE ce.evidence_id = e.id) as control_count
        """
        
        if has_source_id:
            query += ", cs.name as source_name, cs.short_name as source_short"
        
        query += " FROM evidence e"
        
        if has_source_id:
            query += " LEFT JOIN compliance_sources cs ON e.source_id = cs.id"
        
        query += " WHERE 1=1"
        params = []
        
        if has_source_id and source_ids:
            placeholders = ','.join(['?'] * len(source_ids))
            query += f" AND e.source_id IN ({placeholders})"
            params.extend(source_ids)
        
        if search and search.strip():
            s = f"%{search.strip()}%"
            query += " AND (e.ref_id LIKE ? OR e.title LIKE ? OR e.domain LIKE ?)"
            params.extend([s, s, s])
        
        query += " ORDER BY e.ref_id"
        
        return pd.read_sql(query, conn, params=params)


def get_framework_coverage(db_path: str = None, source_ids: List[int] = None) -> pd.DataFrame:
    """Get framework coverage matrix, filtered by source."""
    if not db_exists(db_path):
        return pd.DataFrame()
    
    with get_connection(db_path) as conn:
        has_source_id = _table_has_column(conn, 'controls', 'source_id')
        
        query = """
            SELECT c.ccf_id, c.title, c.mappings, d.name as domain
        """
        
        if has_source_id:
            query += ", cs.short_name as source"
        
        query += """
            FROM controls c
            LEFT JOIN domains d ON c.domain_id = d.id
        """
        
        if has_source_id:
            query += " LEFT JOIN compliance_sources cs ON c.source_id = cs.id"
        
        query += " WHERE c.mappings IS NOT NULL"
        params = []
        
        if has_source_id and source_ids:
            placeholders = ','.join(['?'] * len(source_ids))
            query += f" AND c.source_id IN ({placeholders})"
            params.extend(source_ids)
        
        query += " ORDER BY d.name, c.ccf_id"
        
        rows = conn.execute(query, params).fetchall()
    
    data = []
    all_frameworks = set()
    
    for row in rows:
        try:
            mappings = json.loads(row['mappings']) if row['mappings'] else {}
        except:
            mappings = {}
        
        all_frameworks.update(mappings.keys())
        
        entry = {
            'ccf_id': row['ccf_id'],
            'title': row['title'],
            'domain': row['domain']
        }
        
        if 'source' in row.keys():
            entry['source'] = row['source']
        
        for fw, refs in mappings.items():
            if isinstance(refs, list):
                entry[fw] = ', '.join(refs)
            else:
                entry[fw] = str(refs)
        
        data.append(entry)
    
    df = pd.DataFrame(data)
    
    for fw in all_frameworks:
        if fw not in df.columns:
            df[fw] = None
    
    return df


def get_domain_stats(db_path: str = None, source_ids: List[int] = None) -> pd.DataFrame:
    """Get statistics per domain, filtered by source."""
    if not db_exists(db_path):
        return pd.DataFrame()
    
    with get_connection(db_path) as conn:
        has_source_id = _table_has_column(conn, 'controls', 'source_id')
        
        query = """
            SELECT 
                d.name as domain,
                COUNT(c.id) as total_controls,
                SUM(CASE WHEN c.guidance IS NOT NULL AND TRIM(c.guidance) != '' THEN 1 ELSE 0 END) as with_guidance,
                SUM(CASE WHEN c.testing IS NOT NULL AND TRIM(c.testing) != '' THEN 1 ELSE 0 END) as with_testing,
                SUM(CASE WHEN EXISTS (SELECT 1 FROM control_evidence ce WHERE ce.control_id = c.id) THEN 1 ELSE 0 END) as with_evidence
        """
        
        if has_source_id:
            query += ", cs.short_name as source"
        
        query += """
            FROM domains d
            LEFT JOIN controls c ON c.domain_id = d.id
        """
        
        if has_source_id:
            query += " LEFT JOIN compliance_sources cs ON d.source_id = cs.id"
        
        params = []
        
        if has_source_id and source_ids:
            placeholders = ','.join(['?'] * len(source_ids))
            query += f" WHERE d.source_id IN ({placeholders})"
            params.extend(source_ids)
        
        query += " GROUP BY d.id ORDER BY d.name"
        
        return pd.read_sql(query, conn, params=params)


def get_gap_analysis(db_path: str = None, source_ids: List[int] = None) -> Dict[str, pd.DataFrame]:
    """Generate gap analysis data, filtered by source."""
    if not db_exists(db_path):
        return {}
    
    with get_connection(db_path) as conn:
        has_source_id = _table_has_column(conn, 'controls', 'source_id')
        
        source_filter = ""
        evidence_source_filter = ""
        params = []
        
        if has_source_id and source_ids:
            placeholders = ','.join(['?'] * len(source_ids))
            source_filter = f"AND c.source_id IN ({placeholders})"
            evidence_source_filter = f"AND e.source_id IN ({placeholders})"
            params = list(source_ids)
        
        # Controls missing guidance
        missing_guidance = pd.read_sql(f"""
            SELECT c.ccf_id, c.title, d.name as domain
            FROM controls c
            LEFT JOIN domains d ON c.domain_id = d.id
            WHERE (c.guidance IS NULL OR TRIM(c.guidance) = '')
            {source_filter}
            ORDER BY d.name, c.ccf_id
        """, conn, params=params)
        
        # Controls missing testing
        missing_testing = pd.read_sql(f"""
            SELECT c.ccf_id, c.title, d.name as domain
            FROM controls c
            LEFT JOIN domains d ON c.domain_id = d.id
            WHERE (c.testing IS NULL OR TRIM(c.testing) = '')
            {source_filter}
            ORDER BY d.name, c.ccf_id
        """, conn, params=params)
        
        # Controls missing evidence
        missing_evidence = pd.read_sql(f"""
            SELECT c.ccf_id, c.title, d.name as domain
            FROM controls c
            LEFT JOIN domains d ON c.domain_id = d.id
            WHERE NOT EXISTS (SELECT 1 FROM control_evidence ce WHERE ce.control_id = c.id)
            {source_filter}
            ORDER BY d.name, c.ccf_id
        """, conn, params=params)
        
        # Orphan evidence
        orphan_evidence = pd.read_sql(f"""
            SELECT e.ref_id, e.title, e.domain
            FROM evidence e
            WHERE NOT EXISTS (SELECT 1 FROM control_evidence ce WHERE ce.evidence_id = e.id)
            {evidence_source_filter}
            ORDER BY e.ref_id
        """, conn, params=params)
        
        return {
            'missing_guidance': missing_guidance,
            'missing_testing': missing_testing,
            'missing_evidence': missing_evidence,
            'orphan_evidence': orphan_evidence
        }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _table_has_column(conn, table: str, column: str) -> bool:
    """Check if a table has a specific column."""
    try:
        cursor = conn.execute(f"PRAGMA table_info({table})")
        columns = [row[1] for row in cursor.fetchall()]
        return column in columns
    except:
        return False


def _table_exists(conn, table: str) -> bool:
    """Check if a table exists."""
    cursor = conn.execute("""
        SELECT name FROM sqlite_master WHERE type='table' AND name=?
    """, (table,))
    return cursor.fetchone() is not None
# database.py
import aiosqlite
import json
from typing import Optional, List, Dict


class ModuDB:
    def __init__(self, db_path: str = "modu_db.db"):
        self.db_path = db_path

    async def init_db(self):
        """Initialize database with tables"""
        async with aiosqlite.connect(self.db_path) as conn:
            # Projects table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    spec_id TEXT PRIMARY KEY,
                    total_divisions INTEGER,
                    total_sections INTEGER,
                    sections_with_primary INTEGER,
                    sections_reference_only INTEGER,
                    errors INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP,
                    status TEXT DEFAULT 'pending'
                )
            """)

            # Sections table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    spec_id TEXT NOT NULL,
                    division TEXT NOT NULL,
                    section_number TEXT NOT NULL,
                    section_name TEXT,
                    primary_pages TEXT,
                    reference_pages TEXT,
                    summary TEXT,
                    summary_status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP,
                    FOREIGN KEY (spec_id) REFERENCES projects(spec_id),
                    UNIQUE(spec_id, section_number)
                )
            """)

            # Classification results table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS classification_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    section_id INTEGER NOT NULL,
                    is_primary BOOLEAN,
                    confidence REAL,
                    reasoning TEXT,
                    pages_analyzed TEXT,
                    block_type TEXT,
                    full_block TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (section_id) REFERENCES sections(id)
                )
            """)

            await conn.commit()

    async def save_project(self, spec_id: str, status: str = 'in_progress'):
        """Initialize or update project record"""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                INSERT INTO projects (spec_id, status)
                VALUES (?, ?)
                ON CONFLICT(spec_id) DO UPDATE SET
                    status = ?,
                    updated_at = CURRENT_TIMESTAMP
            """, (spec_id, status, status))
            await conn.commit()
        return spec_id

    async def update_project(self,
                             spec_id: str,
                             status: str,
                             total_divisions: int = 0,
                             total_sections: int = 0,
                             sections_with_primary: int = 0,
                             sections_reference_only: int = 0,
                             errors: int = 0
                             ):
        """Update project record"""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                UPDATE projects
                SET status = ?,
                    updated_at = CURRENT_TIMESTAMP,
                    total_divisions = ?,
                    total_sections = ?,
                    sections_with_primary = ?,
                    sections_reference_only = ?,
                    errors = ?
                WHERE spec_id = ?
            """, (status, total_divisions, total_sections, sections_with_primary, sections_reference_only, errors, spec_id))
            await conn.commit()

    async def get_projects(self) -> List[Dict]:
        """Get project data"""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                SELECT * FROM projects
            """)

            rows = await cursor.fetchall()
            projects = []
            for row in rows:
                projects.append({
                    "spec_id": row['spec_id'],
                    "total_divisions": row['total_divisions'],
                    "total_sections": row['total_sections'],
                    "sections_with_primary": row['sections_with_primary'],
                    "sections_reference_only": row['sections_reference_only'],
                    "errors": row['errors'],
                    "created_at": row['created_at'],
                    "updated_at": row['updated_at'],
                    "status": row['status']
                })
            return projects

    async def get_section(self, section_id: int) -> Optional[Dict]:
        """Get section data"""
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute("""
                SELECT * FROM sections WHERE id = ?
            """, (section_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def save_section(self, spec_id: str, division: str, section_number: str,
                           section_name: str, primary_pages: List[int], reference_pages: List[int]) -> int:
        """Save section data and return section_id"""
        async with aiosqlite.connect(self.db_path) as conn:
            # First, try to get existing section
            cursor = await conn.execute("""
                SELECT id FROM sections
                WHERE spec_id = ? AND section_number = ?
            """, (spec_id, section_number))

            existing = await cursor.fetchone()

            if existing:
                await conn.execute("""
                    UPDATE sections
                    SET division = ?,
                        section_name = ?,
                        primary_pages = ?,
                        reference_pages = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (division, section_name,
                      json.dumps(primary_pages), json.dumps(reference_pages),
                      existing[0]))
                section_id = existing[0]
            else:
                await conn.execute("""
                    INSERT INTO sections (spec_id, division, section_number, section_name,
                                         primary_pages, reference_pages)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (spec_id, division, section_number, section_name,
                      json.dumps(primary_pages), json.dumps(reference_pages)))

                cursor = await conn.execute("SELECT last_insert_rowid()")
                section_id = (await cursor.fetchone())[0]

            await conn.commit()
        return section_id

    async def get_all_spec_sections(self, spec_id: str) -> List[Dict]:
        """Get all sections for a spec"""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                SELECT * FROM
                sections WHERE spec_id = ?
                ORDER BY section_number ASC
            """, (spec_id,))

            rows = await cursor.fetchall()
            sections_by_division = {}
            for row in rows:
                division = row['division']

                if division not in sections_by_division:
                    sections_by_division[division] = []

                sections_by_division[division].append({
                    "id": row['id'],
                    "spec_id": row['spec_id'],
                    "division": row['division'],
                    "section_number": row['section_number'],
                    "section_name": row['section_name'],
                    "primary_pages": json.loads(row['primary_pages'] or '[]'),
                    "reference_pages": json.loads(row['reference_pages'] or '[]'),
                    "summary": row['summary'],
                    "summary_status": row['summary_status'],
                    "created_at": row['created_at'],
                    "updated_at": row['updated_at']
                })
            return sections_by_division

    async def get_all_specs_with_primary_pages(self, spec_id: str) -> List[Dict]:
        """Get all sections with primary pages for a spec"""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                SELECT * FROM
                sections WHERE spec_id = ?
                AND primary_pages != '[]'
                ORDER BY section_number ASC
            """, (spec_id,))

            rows = await cursor.fetchall()
            sections_by_division = {}
            for row in rows:
                division = row['division']

                if division not in sections_by_division:
                    sections_by_division[division] = []

                sections_by_division[division].append({
                    "id": row['id'],
                    "spec_id": row['spec_id'],
                    "division": row['division'],
                    "section_number": row['section_number'],
                    "section_name": row['section_name'],
                    "primary_pages": json.loads(row['primary_pages'] or '[]'),
                    "reference_pages": json.loads(row['reference_pages'] or '[]'),
                    "summary": row['summary'],
                    "summary_status": row['summary_status'],
                    "created_at": row['created_at'],
                    "updated_at": row['updated_at']
                })
            return sections_by_division

    async def save_classification_result(self, section_id: int, result: Dict):
        """Save individual classification result"""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                INSERT INTO classification_results
                (section_id, is_primary, confidence, reasoning, pages_analyzed, block_type, full_block)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                section_id,
                result.get('is_primary'),
                result.get('confidence'),
                result.get('reasoning'),
                json.dumps(result.get('pages_analyzed', [])),
                result.get('block_type'),
                json.dumps(result.get('full_block')) if result.get(
                    'full_block') else None
            ))
            await conn.commit()

    async def update_classification_status(self, section_id: int, status: str):
        """Update individual classification result"""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                UPDATE sections
                SET summary_status = ?
                WHERE id = ?
            """, (status, section_id))
            await conn.commit()

    async def update_project_summary(self, spec_id: str):
        """Update project statistics"""
        async with aiosqlite.connect(self.db_path) as conn:
            # Count sections
            cursor = await conn.execute("""
                SELECT COUNT(*) FROM sections WHERE spec_id = ?
            """, (spec_id,))
            total_sections = (await cursor.fetchone())[0]

            # Count sections with primary pages
            cursor = await conn.execute("""
                SELECT COUNT(*) FROM sections
                WHERE spec_id = ? AND primary_pages != '[]'
            """, (spec_id,))
            with_primary = (await cursor.fetchone())[0]

            reference_only = total_sections - with_primary

            await conn.execute("""
                UPDATE projects
                SET total_sections = ?,
                    sections_with_primary = ?,
                    sections_reference_only = ?,
                    status = 'complete',
                    updated_at = CURRENT_TIMESTAMP
                WHERE spec_id = ?
            """, (total_sections, with_primary, reference_only, spec_id))

            await conn.commit()

    async def get_project_status(self, spec_id: str) -> Optional[Dict]:
        """Get project status"""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                SELECT spec_id, total_divisions, total_sections, sections_with_primary,
                       sections_reference_only, errors, status, created_at, updated_at
                FROM projects
                WHERE spec_id = ?
            """, (spec_id,))

            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None


db = ModuDB()

# database.py
import aiosqlite
import json
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


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
                    project_name TEXT,
                    total_divisions INTEGER DEFAULT 0,
                    total_sections INTEGER DEFAULT 0,
                    sections_with_primary INTEGER DEFAULT 0,
                    sections_with_reference INTEGER DEFAULT 0,
                    errors INTEGER DEFAULT 0,
                    classification_status TEXT DEFAULT 'pending',
                    summary_status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP
                )
            """)

            # Divisions table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS divisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    spec_id TEXT NOT NULL,
                    division TEXT NOT NULL,
                    division_title TEXT,
                    total_sections INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP,
                    FOREIGN KEY (spec_id) REFERENCES projects(spec_id) ON DELETE CASCADE,
                    UNIQUE(spec_id, division)
                )
            """)

            # Sections table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    spec_id TEXT NOT NULL,
                    division_id INTEGER NOT NULL,
                    division TEXT NOT NULL,
                    section_number TEXT NOT NULL,
                    section_title TEXT,
                    primary_pages TEXT,
                    reference_pages TEXT,
                    total_pages INTEGER,
                    classification_status TEXT DEFAULT 'pending',
                    summary_status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP,
                    FOREIGN KEY (spec_id) REFERENCES projects(spec_id) ON DELETE CASCADE,
                    FOREIGN KEY (division_id) REFERENCES divisions(id) ON DELETE CASCADE,
                    UNIQUE(spec_id, section_number)
                )
            """)

            # Classification results table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS classification (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    section_id INTEGER NOT NULL,
                    custom_id TEXT NOT NULL,
                    is_primary BOOLEAN NOT NULL,
                    confidence REAL NOT NULL,
                    reasoning TEXT NOT NULL,
                    pages_analyzed TEXT DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (section_id) REFERENCES sections(id) ON DELETE CASCADE
                )
            """)

            # Section summaries table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS section_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    spec_id TEXT NOT NULL,
                    section_id INTEGER NOT NULL,
                    section_number TEXT NOT NULL,
                    section_title TEXT,
                    overview TEXT,
                    key_requirements TEXT DEFAULT '[]',
                    materials TEXT DEFAULT '[]',
                    submittals TEXT DEFAULT '[]',
                    testing TEXT DEFAULT '[]',
                    related_sections TEXT DEFAULT '[]',
                    pages_summarized TEXT DEFAULT '[]',
                    pages_not_summarized TEXT DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (spec_id) REFERENCES projects(spec_id) ON DELETE CASCADE,
                    FOREIGN KEY (section_id) REFERENCES sections(id) ON DELETE CASCADE
                )
            """)

            # Submittal packages table
            # A package belongs to a company/contractor for a given spec
            # division_id is always required
            # section_id is optional — null means the package covers the whole division
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS submittal_packages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    spec_id TEXT NOT NULL,
                    division_id INTEGER NOT NULL,
                    section_id INTEGER,
                    company_name TEXT NOT NULL,
                    submitted_by TEXT,
                    submitted_date TIMESTAMP,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP,
                    FOREIGN KEY (spec_id) REFERENCES projects(spec_id) ON DELETE CASCADE,
                    FOREIGN KEY (division_id) REFERENCES divisions(id) ON DELETE CASCADE,
                    FOREIGN KEY (section_id) REFERENCES sections(id) ON DELETE CASCADE
                )
            """)

            # Submittals table
            # Individual documents within a submittal package
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS submittals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    package_id INTEGER NOT NULL,
                    file_name TEXT NOT NULL,
                    submittal_type TEXT,
                    s3_key TEXT,
                    page_count INTEGER,
                    compliance_score REAL,
                    classification_result TEXT DEFAULT '{}',
                    extraction_result TEXT DEFAULT '{}',
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP,
                    FOREIGN KEY (package_id) REFERENCES submittal_packages(id) ON DELETE CASCADE
                )
            """)

            await conn.commit()

    async def create_project(
        self,
        spec_id: str,
        project_name: str,
        classification_status: str = None,
        summary_status: str = None,
        total_divisions: int = None,
        total_sections: int = None,
        sections_with_primary: int = None,
        sections_with_reference: int = None,
        errors: int = None
    ):
        """Initialize or update project record"""
        fields = {
            "project_name": project_name,
            "classification_status": classification_status,
            "summary_status": summary_status,
            "total_divisions": total_divisions,
            "total_sections": total_sections,
            "sections_with_primary": sections_with_primary,
            "sections_with_reference": sections_with_reference,
            "errors": errors
        }

        updates = {k: v for k, v in fields.items() if v is not None}

        columns = ", ".join(["spec_id"] + list(updates.keys()))
        placeholders = ", ".join(["?"] * (len(updates) + 1))
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = [spec_id] + list(updates.values())

        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(f"""
                INSERT INTO projects ({columns})
                VALUES ({placeholders})
                ON CONFLICT(spec_id) DO UPDATE SET
                    {set_clause},
                    updated_at = CURRENT_TIMESTAMP
            """, values + list(updates.values()))
            await conn.commit()
        return spec_id

    async def update_project(
        self,
        spec_id: str,
        project_name: str = None,
        classification_status: str = None,
        summary_status: str = None,
        total_divisions: int = None,
        total_sections: int = None,
        sections_with_primary: int = None,
        sections_with_reference: int = None,
        errors: int = None
    ):
        """Update project record"""
        fields = {
            "project_name": project_name,
            "classification_status": classification_status,
            "summary_status": summary_status,
            "total_divisions": total_divisions,
            "total_sections": total_sections,
            "sections_with_primary": sections_with_primary,
            "sections_with_reference": sections_with_reference,
            "errors": errors
        }

        updates = {k: v for k, v in fields.items() if v is not None}
        if not updates:
            return

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [spec_id]

        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(f"""
                UPDATE projects
                SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                WHERE spec_id = ?
            """, values)
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
                    "project_name": row['project_name'],
                    "total_divisions": row['total_divisions'],
                    "total_sections": row['total_sections'],
                    "sections_with_primary": row['sections_with_primary'],
                    "sections_with_reference": row['sections_with_reference'],
                    "errors": row['errors'],
                    "created_at": row['created_at'],
                    "updated_at": row['updated_at'],
                    "classification_status": row['classification_status'],
                    "summary_status": row['summary_status']
                })
            return projects

    async def delete_project(self, spec_id: str):
        """Delete project"""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                DELETE FROM projects WHERE spec_id = ?
            """, (spec_id,))
            await conn.commit()

    async def create_division(self, spec_id: str, division: str, division_title: str):
        """Create division or return existing id"""
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute("""
                INSERT INTO divisions (spec_id, division, division_title)
                VALUES (?, ?, ?)
                ON CONFLICT(spec_id, division) DO UPDATE SET
                    division_title = excluded.division_title,
                    updated_at = CURRENT_TIMESTAMP
            """, (spec_id, division, division_title))
            await conn.commit()
            return cursor.lastrowid

    async def get_division(self, spec_id: str, division: str) -> Optional[Dict]:
        """Get division data"""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                SELECT * FROM divisions WHERE spec_id = ? AND division = ?
            """, (spec_id, division))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_all_divisions(self, spec_id: str) -> List[Dict]:
        """Get all divisions for a spec"""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                SELECT * FROM divisions WHERE spec_id = ?
            """, (spec_id,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def update_division(self, spec_id: str, division: str, division_title: str):
        """Update division"""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                UPDATE divisions
                SET division_title = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE spec_id = ? AND division = ?
            """, (division_title, spec_id, division))
            await conn.commit()
            return await self.get_division(spec_id, division)

    async def delete_division(self, spec_id: str, division: str):
        """Delete division"""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                DELETE FROM divisions WHERE spec_id = ? AND division = ?
            """, (spec_id, division))
            await conn.commit()
            return {
                "deleted": True,
                "division": division,
                "spec_id": spec_id
            }

    async def get_section(self, spec_id: str, section_number: str) -> Optional[Dict]:
        """Get section data"""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                SELECT * FROM sections WHERE spec_id = ? AND section_number = ?
            """, (spec_id, section_number))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def create_section(
        self,
        spec_id: str,
        division: str,
        division_id: int,
        section_number: str,
        section_title: str,
        total_pages: int,
        classification_status: str = "pending",
        summary_status: str = "pending"
    ) -> int:
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
                        division_id = ?,
                        section_title = ?,
                        total_pages = ?,
                        classification_status = ?,
                        summary_status = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (division, division_id, section_title,
                      total_pages, classification_status, summary_status, existing[0]))
                section_id = existing[0]
            else:
                await conn.execute("""
                    INSERT INTO sections (spec_id, division, division_id, section_number, section_title,
                                         total_pages, classification_status, summary_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (spec_id, division, division_id, section_number, section_title, total_pages, classification_status, summary_status))

                cursor = await conn.execute("SELECT last_insert_rowid()")
                section_id = (await cursor.fetchone())[0]

            await conn.commit()
        return section_id

    async def update_section_pages(
        self,
        spec_id: str,
        section_number: str,
        primary_pages: list,
        reference_pages: list,
    ) -> dict:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute("""
                    SELECT * FROM sections
                    WHERE spec_id = ? AND section_number = ?
                """, (spec_id, section_number))

                existing = await cursor.fetchone()
                if not existing:
                    return {
                        "error": "Section not found",
                        "section_id": None
                    }

                existing_id = existing['id']
                existing_primary_pages = json.loads(
                    existing['primary_pages'] or '[]')
                existing_reference_pages = json.loads(
                    existing['reference_pages'] or '[]')
                new_primary_pages = existing_primary_pages + primary_pages
                new_reference_pages = existing_reference_pages + reference_pages

                classification_status = "complete" if len(
                    new_primary_pages) + len(new_reference_pages) >= existing['total_pages'] else "pending"

                await conn.execute("""
                    UPDATE sections
                    SET primary_pages = ?,
                        reference_pages = ?,
                        classification_status = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (json.dumps(new_primary_pages), json.dumps(new_reference_pages),
                      classification_status, existing_id))

                await conn.commit()

            return {
                "section_id": existing_id,
                "classification_status": classification_status
            }

        except Exception as e:
            logger.error(f"Error updating section pages: {e}")
            return {
                "error": str(e),
                "section_id": None,
                "classification_status": "error"
            }

    async def update_section_summary_status(
        self,
        spec_id: str,
        section_number: str,
        summary_status: str = 'complete',
    ) -> dict:
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute("""
                    SELECT id FROM sections
                    WHERE spec_id = ? AND section_number = ?
                """, (spec_id, section_number))

                existing = await cursor.fetchone()
                if not existing:
                    return {
                        "error": "Section not found",
                        "section_id": None
                    }

                await conn.execute("""
                    UPDATE sections
                    SET summary_status = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (summary_status, existing['id']))

                await conn.commit()

            return {
                "section_id": existing['id'],
                "summary_status": summary_status
            }

        except Exception as e:
            logger.error(f"Error updating section summary status: {e}")
            return {
                "error": str(e),
                "section_id": None,
                "summary_status": "error"
            }

    async def update_section_title(self, section_id: int, section_title: str):
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("""
                    UPDATE sections
                    SET section_title = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (section_title, section_id))
                await conn.commit()
            return {
                "section_id": section_id,
                "section_title": section_title
            }
        except Exception as e:
            logger.error(f"Error updating section title: {e}")
            return {
                "error": str(e),
                "section_id": None,
                "section_title": None
            }

    async def get_all_sections(self, spec_id: str) -> List[Dict]:
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
                    "section_title": row['section_title'],
                    "primary_pages": json.loads(row['primary_pages'] or '[]'),
                    "reference_pages": json.loads(row['reference_pages'] or '[]'),
                    "classification_status": row['classification_status'],
                    "summary_status": row['summary_status'],
                    "created_at": row['created_at'],
                    "updated_at": row['updated_at']
                })
            return sections_by_division

    async def get_sections_with_primary_pages(self, spec_id: str) -> List[Dict]:
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
                    "section_title": row['section_title'],
                    "primary_pages": json.loads(row['primary_pages'] or '[]'),
                    "reference_pages": json.loads(row['reference_pages'] or '[]'),
                    "classification_status": row['classification_status'],
                    "summary_status": row['summary_status'],
                    "created_at": row['created_at'],
                    "updated_at": row['updated_at']
                })
            return sections_by_division

    async def get_all_sections_without_primary_pages(self, spec_id: str) -> List[Dict]:
        """Get all sections without primary pages for a spec"""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                SELECT * FROM sections WHERE spec_id = ? AND primary_pages = '[]' ORDER BY section_number ASC
            """, (spec_id,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def save_classification_result(self, section_id: int, custom_id: str, result: Dict):
        """Save individual classification result"""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                INSERT INTO classification
                (section_id, custom_id, is_primary, confidence, reasoning, pages_analyzed)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                section_id,
                custom_id,
                result.get('is_primary'),
                result.get('confidence'),
                result.get('reasoning'),
                json.dumps(result.get('pages_analyzed', [])),
            ))
            await conn.commit()

    async def get_project_status(self, spec_id: str) -> Optional[Dict]:
        """Get project status"""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                SELECT spec_id, total_divisions, total_sections, sections_with_primary,
                       sections_with_reference, errors, classification_status, summary_status, created_at, updated_at
                FROM projects
                WHERE spec_id = ?
            """, (spec_id,))

            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

    async def get_section_summary(self, spec_id: str, section_number: str) -> Optional[Dict]:
        """Get section summary"""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                SELECT * FROM section_summaries WHERE spec_id = ? AND section_number = ?
            """, (spec_id, section_number))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def save_section_summary(self, spec_id: str, section_summary: dict):
        """Save section summary"""
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute("""
                INSERT INTO section_summaries (spec_id, section_id, section_number, section_title, overview, key_requirements, materials, submittals, testing, related_sections, pages_summarized, pages_not_summarized)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                spec_id,
                section_summary['section_id'],
                section_summary['section_number'],
                section_summary['section_title'],
                section_summary['overview'],
                json.dumps(section_summary['key_requirements']),
                json.dumps(section_summary['materials']),
                json.dumps(section_summary['submittals']),
                json.dumps(section_summary['testing']),
                json.dumps(section_summary['related_sections']),
                json.dumps(section_summary['pages_summarized']),
                json.dumps(section_summary['pages_not_summarized'])
            ))
            await conn.commit()
        return cursor.lastrowid

    async def update_section_summary(self, spec_id: str, section_summary: dict):
        """Update section summary"""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                UPDATE section_summaries
                SET section_title = ?,
                    overview = ?,
                    key_requirements = ?,
                    materials = ?,
                    submittals = ?,
                    testing = ?,
                    related_sections = ?,
                    pages_summarized = ?,
                    pages_not_summarized = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE spec_id = ? AND section_number = ?
            """, (
                section_summary['section_title'],
                section_summary['overview'],
                json.dumps(section_summary['key_requirements']),
                json.dumps(section_summary['materials']),
                json.dumps(section_summary['submittals']),
                json.dumps(section_summary['testing']),
                json.dumps(section_summary['related_sections']),
                json.dumps(section_summary['pages_summarized']),
                json.dumps(section_summary['pages_not_summarized']),
                spec_id,
                section_summary['section_number']
            ))
            await conn.commit()

    async def delete_section_summary(self, section_id: int):
        """Delete section summary"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("""
                    DELETE FROM section_summaries WHERE id = ?
                """, (section_id,))
                await conn.commit()
            return {
                "section_id": section_id,
                "message": "Section summary deleted successfully"
            }
        except Exception as e:
            logger.error(f"Error deleting section summary: {e}")
            return {
                "error": str(e),
                "section_id": None
            }


db = ModuDB()

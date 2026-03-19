# database.py
import aiosqlite
import json
from typing import Optional, List, Dict
import logging
from classes.s3_buckets import S3Bucket

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

s3 = S3Bucket()


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
                    referenced_sections TEXT DEFAULT '[]',
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
            # A package belongs to a series of submittals from a single source
            # Minimum requirement is a spec_id, section_id, and package_name
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS submittal_packages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    spec_id TEXT NOT NULL,
                    section_id INTEGER NOT NULL,
                    package_name TEXT NOT NULL,
                    company_name TEXT,
                    submitted_by TEXT,
                    submitted_date TIMESTAMP,
                    compliance_score REAL,
                    compliance_result TEXT DEFAULT NULL,
                    checked_submittal_ids TEXT DEFAULT NULL,
                    run_count INTEGER DEFAULT 0,
                    last_checked_at TIMESTAMP DEFAULT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP,
                    FOREIGN KEY (spec_id) REFERENCES projects(spec_id) ON DELETE CASCADE,
                    FOREIGN KEY (section_id) REFERENCES sections(id) ON DELETE CASCADE
                )
            """)

            # Submittals table
            # Individual documents within a submittal package
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS submittals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    package_id INTEGER NOT NULL,
                    spec_id TEXT NOT NULL,
                    submittal_title TEXT NOT NULL,
                    s3_key TEXT DEFAULT NULL,
                    page_count INTEGER DEFAULT NULL,
                    compliance_score REAL DEFAULT NULL,
                    submittal_type_id INTEGER DEFAULT NULL CHECK (submittal_type_id IN (1042, 2187, 3561, 4823, 5394, 6718, 7265)),
                    submittal_type_name TEXT GENERATED ALWAYS AS (
                        CASE submittal_type_id
                            WHEN 1042 THEN 'Shop Drawing'
                            WHEN 2187 THEN 'Product Data'
                            WHEN 3561 THEN 'Material Certification'
                            WHEN 4823 THEN 'Test Report'
                            WHEN 5394 THEN 'Mix Design'
                            WHEN 6718 THEN 'Sample'
                            WHEN 7265 THEN 'Other'
                        END
                    ) STORED,
                    submittal_findings TEXT DEFAULT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP,
                    FOREIGN KEY (package_id) REFERENCES submittal_packages(id) ON DELETE CASCADE
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS compliance_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    package_id INTEGER NOT NULL,
                    spec_id TEXT NOT NULL,
                    section_id INTEGER NOT NULL,
                    submittal_ids TEXT NOT NULL,
                    compliance_result TEXT DEFAULT NULL,
                    compliance_score REAL DEFAULT NULL,
                    is_compliant BOOLEAN DEFAULT NULL,
                    run_type TEXT DEFAULT 'cumulative',
                    prompt_version INTEGER DEFAULT NULL,
                    model TEXT DEFAULT NULL,
                    pipeline TEXT DEFAULT NULL,
                    token_count INTEGER DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (package_id) REFERENCES submittal_packages(id) ON DELETE CASCADE
                )""")

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS compliance_comparisons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    package_id_a INTEGER NOT NULL REFERENCES submittal_packages(id),
                    package_id_b INTEGER NOT NULL REFERENCES submittal_packages(id),
                    section_id INTEGER NOT NULL REFERENCES spec_sections(id),
                    section_number TEXT NOT NULL,
                    overall_winner TEXT NOT NULL CHECK(overall_winner IN ('A', 'B', 'tie')),
                    package_name_a TEXT NOT NULL,
                    package_name_b TEXT NOT NULL,
                    score_a REAL NOT NULL,
                    score_b REAL NOT NULL,
                    score_delta REAL NOT NULL,
                    executive_summary TEXT,
                    recommendation TEXT,
                    comparison_result TEXT,
                    model_version TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )""")

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
        """
        Save individual classification result
        result argument schema: {"is_primary": bool, "confidence": float, "reasoning": str, "referenced_sections": list[str], "pages_analyzed": list[int]}
        """
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute("""
                INSERT INTO classification
                (section_id, custom_id, is_primary, confidence, reasoning, referenced_sections, pages_analyzed)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                section_id,
                custom_id,
                result.get('is_primary'),
                result.get('confidence'),
                result.get('reasoning'),
                json.dumps(result.get('referenced_sections', [])),
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

    async def get_section_summary(self, section_id: int) -> Optional[Dict]:
        """Get section summary"""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                SELECT * FROM section_summaries WHERE section_id = ?
            """, (section_id,))
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

    async def create_submittal_package(
        self,
        spec_id: str,
        section_id: int,
        package_name: str,
        company_name: str = None,
        submitted_by: str = None,
        submitted_date: str = None,
        compliance_score: float = None,
        status: str = "pending"
    ) -> int:
        """Create submittal package"""
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute("""
                INSERT INTO submittal_packages (spec_id, section_id, package_name, company_name, submitted_by, submitted_date, compliance_score, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (spec_id, section_id, package_name, company_name, submitted_by, submitted_date, compliance_score, status))
            await conn.commit()
            return cursor.lastrowid

    async def get_submittal_package(self, submittal_package_id: int) -> Optional[Dict]:
        """Get submittal package"""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                SELECT * FROM submittal_packages WHERE id = ?
            """, (submittal_package_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_packages_for_section(self, section_id: int) -> List[Dict]:
        """Get submittal packages for a section, including their submittals"""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row

            # Fetch packages
            cursor = await conn.execute("""
                SELECT * FROM submittal_packages WHERE section_id = ?
            """, (section_id,))
            packages = [dict(row) for row in await cursor.fetchall()]

            # Fetch submittals for each package
            for pkg in packages:
                cursor = await conn.execute("""
                    SELECT id, submittal_title, submittal_type_id, submittal_type_name,
                           status, page_count
                    FROM submittals
                    WHERE package_id = ?
                    ORDER BY id ASC
                """, (pkg["id"],))
                pkg["submittals"] = [dict(row) for row in await cursor.fetchall()]

            return packages

    async def get_all_submittal_packages(self, spec_id: str) -> List[Dict]:
        """Get all submittal packages"""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                SELECT * FROM submittal_packages WHERE spec_id = ?
            """, (spec_id,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def update_package_after_run(
        self,
        package_id: int,
        compliance_result: dict,
        compliance_score: float,
        checked_submittal_ids: list[int],
    ) -> None:
        async with aiosqlite.connect(self.db_path) as conn:
            # Get all submittal IDs for this package
            async with conn.execute(
                "SELECT id FROM submittals WHERE package_id = ?", (package_id)
            ) as cursor:
                rows = await cursor.fetchall()
                all_submittal_ids = {row[0] for row in rows}

            # Get current checked_submittal_ids from package
            async with conn.execute(
                "SELECT checked_submittal_ids FROM submittal_packages WHERE id = ?", (
                    package_id,)
            ) as cursor:
                row = await cursor.fetchone()
                existing = json.loads(row[0]) if row and row[0] else []

            # Merge
            merged = list(set(existing) | set(checked_submittal_ids))
            all_checked = set(merged) >= all_submittal_ids

            if all_checked:
                await conn.execute("""
                    UPDATE submittal_packages
                    SET compliance_result = ?,
                        compliance_score = ?,
                        checked_submittal_ids = ?,
                        run_count = run_count + 1,
                        last_checked_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    json.dumps(compliance_result),
                    compliance_score,
                    json.dumps(merged),
                    package_id,
                ))
            else:
                await conn.execute("""
                    UPDATE submittal_packages
                    SET checked_submittal_ids = ?,
                        run_count = run_count + 1,
                        last_checked_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    json.dumps(merged),
                    package_id,
                ))

            await conn.commit()

    async def get_package_result(self, package_id: int) -> Optional[Dict]:
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                SELECT id, compliance_result, compliance_score,
                       checked_submittal_ids, run_count, last_checked_at, created_at
                FROM submittal_packages
                WHERE id = ?
            """, (package_id,))
            row = await cursor.fetchone()
            if not row:
                return None
            result = dict(row)
            if result.get("compliance_result"):
                result["compliance_result"] = json.loads(
                    result["compliance_result"])
            if result.get("checked_submittal_ids"):
                result["checked_submittal_ids"] = json.loads(
                    result["checked_submittal_ids"])
            return result

    async def delete_submittal_package(self, submittal_package_id: int):
        """Delete submittal package from db and s3 bucket"""
        try:
            package = await self.get_submittal_package(submittal_package_id)
            if not package:
                return {"error": "Submittal package not found"}, 404

            # delete submittal package from db
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("""
                    DELETE FROM submittal_packages WHERE id = ?
                """, (submittal_package_id,))
                await conn.commit()

            return {
                "message": "Submittal package deleted successfully",
                "submittal_package_id": submittal_package_id
            }
        except Exception as e:
            logger.error(f"Error deleting submittal package: {e}")
            return {
                "error": str(e),
                "submittal_package_id": None
            }

    async def create_submittal(
        self,
        package_id: int,
        spec_id: str,
        submittal_title: str,
        s3_key: str,
        submittal_type_id: int,
        page_count: int = None,
        compliance_score: float = None,
        submittal_findings: str = None
    ) -> int:
        """Create submittal"""
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute("""
                INSERT INTO submittals (package_id, spec_id, submittal_title, s3_key, page_count, compliance_score, submittal_type_id, submittal_findings)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (package_id, spec_id, submittal_title, s3_key, page_count, compliance_score, submittal_type_id, submittal_findings))
            await conn.commit()
            return cursor.lastrowid

    async def get_all_submittals(self, spec_id: str) -> List[Dict]:
        """Get all submittals by spec_id"""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                SELECT * FROM submittals WHERE spec_id = ?
            """, (spec_id,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_submittal(self, submittal_id: int) -> Optional[Dict]:
        """Get submittal"""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                SELECT * FROM submittals WHERE id = ?
            """, (submittal_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_submittals_by_ids(self, package_id: int, submittal_ids: List[int]) -> List[Dict]:
        """Get submittals by ids"""
        placeholders = ", ".join("?" * len(submittal_ids))
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                SELECT * FROM submittals WHERE package_id = ? AND id IN ({placeholders})
            """.format(placeholders=placeholders),
                (package_id, *submittal_ids))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_submittals_by_type(self, package_id: int, submittal_type_ids: List[int]) -> List[Dict]:
        """Get submittals by submittal_type_ids"""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            placeholders = ", ".join("?" * len(submittal_type_ids))
            cursor = await conn.execute(f"""
                SELECT * FROM submittals WHERE package_id = ? AND submittal_type_id IN ({placeholders})
            """, (package_id, *submittal_type_ids))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_submittals_by_package(self, package_id: int) -> List[Dict]:
        """Get all submittals by package"""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                SELECT * FROM submittals WHERE package_id = ?
            """, (package_id,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def update_submittal(
        self,
        submittal_id: int,
        submittal_title: str = None,
        s3_key: str = None,
        page_count: int = None,
        compliance_score: float = None,
        submittal_type: str = None,
        submittal_findings: str = None,
        status: str = None
    ) -> int:
        """Update submittal"""
        async with aiosqlite.connect(self.db_path) as conn:
            fields = {
                "submittal_title": submittal_title,
                "s3_key": s3_key,
                "page_count": page_count,
                "compliance_score": compliance_score,
                "submittal_type": submittal_type,
                "submittal_findings": submittal_findings,
                "status": status
            }
            updates = {k: v for k, v in fields.items() if v is not None}
            if not updates:
                return

            set_clause = ", ".join(f"{k} = ?" for k in updates)
            values = list(updates.values()) + [submittal_id]

            await conn.execute(f"""
                UPDATE submittals
                SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, values)
            await conn.commit()
            return submittal_id

    async def delete_submittal(self, submittal_id: int):
        """Delete submittal from db and s3 bucket"""
        try:
            submittal = await self.get_submittal(submittal_id)
            if not submittal:
                return {"error": "Submittal not found"}, 404

            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("""
                    DELETE FROM submittals WHERE id = ?
                """, (submittal_id,))
                await conn.commit()

            async with s3.s3_client() as s3_client:
                deleted_from_s3 = await s3.delete_submittal_with_client(submittal.get("s3_key"), s3_client)
                if deleted_from_s3.get("status_code") != 200:
                    return {"error": deleted_from_s3.get("message")}, deleted_from_s3.get("status_code")

            return {
                "message": "Submittal deleted successfully",
                "submittal_id": submittal_id
            }
        except Exception as e:
            logger.error(f"Error deleting submittal: {e}")
            return {"error": str(e), "submittal_id": None}

    async def create_compliance_run(
        self,
        package_id: int,
        spec_id: str,
        section_id: int,
        submittal_ids: list[int],
        compliance_result: dict,
        compliance_score: float,
        is_compliant: bool,
        pipeline: str,
        run_type: str = "cumulative",
        model: str = "claude-sonnet-4-6",
        prompt_version: int = 1,
        token_count: int = None,
    ) -> int:
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute("""
                INSERT INTO compliance_runs (
                    package_id, spec_id, section_id, submittal_ids,
                    compliance_result, compliance_score, is_compliant,
                    pipeline, run_type, model, prompt_version, token_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                package_id,
                spec_id,
                section_id,
                json.dumps(submittal_ids),
                json.dumps(compliance_result),
                compliance_score,
                is_compliant,
                pipeline,
                run_type,
                model,
                prompt_version,
                token_count,
            ))
            await conn.commit()
            return cursor.lastrowid

    async def update_compliance_run(
        self,
        compliance_run_id: int,
        submittal_ids: list[int],
        compliance_result: dict,
        compliance_score: float,
        is_compliant: bool,
        pipeline: str,
        run_type: str = "cumulative",
        model: str = "claude-sonnet-4-6",
        prompt_version: int = None,
        token_count: int = None,
    ) -> int:
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute("""
                UPDATE compliance_runs
                SET submittal_ids = ?,
                    compliance_result = ?,
                    compliance_score = ?,
                    is_compliant = ?,
                    pipeline = ?,
                    run_type = ?,
                    model = ?,
                    prompt_version = ?,
                    token_count = ?
                WHERE id = ?
            """, (json.dumps(submittal_ids), json.dumps(compliance_result), compliance_score, is_compliant, pipeline, run_type, model, prompt_version, token_count, compliance_run_id))
            await conn.commit()
            return cursor.lastrowid

    async def get_compliance_runs(
        self,
        package_id: int,
        submittal_id: Optional[int] = None,
        run_type: Optional[str] = None,
    ) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            if submittal_id:
                cursor = await conn.execute("""
                    SELECT * FROM compliance_runs
                    WHERE package_id = ?
                    AND json_array_length(submittal_ids) = 1
                    AND json_extract(submittal_ids, '$[0]') = ?
                    ORDER BY created_at DESC
                """, (package_id, int(submittal_id)))
            elif run_type:
                cursor = await conn.execute("""
                    SELECT * FROM compliance_runs
                    WHERE package_id = ?
                    AND run_type = ?
                    ORDER BY created_at DESC
                """, (package_id, run_type))
            else:
                cursor = await conn.execute("""
                    SELECT * FROM compliance_runs
                    WHERE package_id = ?
                    ORDER BY created_at DESC
                """, (package_id,))
            rows = await cursor.fetchall()
            runs = [dict(row) for row in rows]
            for run in runs:
                if run.get("compliance_result"):
                    run["compliance_result"] = json.loads(
                        run["compliance_result"])
                if run.get("submittal_ids"):
                    run["submittal_ids"] = json.loads(run["submittal_ids"])
            return runs

    async def get_compliance_run(self, compliance_run_id: int) -> Optional[Dict]:
        """Get compliance run"""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                SELECT * FROM compliance_runs WHERE id = ?
            """, (compliance_run_id))
            row: dict = await cursor.fetchone()
            if not row:
                return None

            run = dict(row)
            if run.get("compliance_result"):
                run["compliance_result"] = json.loads(run["compliance_result"])
            if run.get("submittal_ids"):
                run["submittal_ids"] = json.loads(run["submittal_ids"])
            return run

    async def create_compliance_comparison(
        self,
        package_id_a: int,
        package_id_b: int,
        section_id: int,
        section_number: str,
        overall_winner: str,
        package_name_a: str,
        package_name_b: str,
        score_a: float,
        score_b: float,
        score_delta: float,
        executive_summary: str,
        recommendation: str,
        comparison_result: str,
        model_version: str,
    ) -> int:
        async with aiosqlite.connect(self.db_path) as conn:
            cursor = await conn.execute("""
                INSERT INTO compliance_comparisons (
                    package_id_a, package_id_b, section_id, section_number,
                    overall_winner, package_name_a, package_name_b,
                    score_a, score_b, score_delta,
                    executive_summary, recommendation, comparison_result,
                    model_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                package_id_a, package_id_b, section_id, section_number,
                overall_winner, package_name_a, package_name_b,
                score_a, score_b, score_delta,
                executive_summary, recommendation, comparison_result,
                model_version
            ))
            await conn.commit()
            return cursor.lastrowid

    async def get_compliance_comparisons(self, id: int = None, section_id: int = None) -> List[Dict]:
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            if id:
                cursor = await conn.execute("""
                    SELECT * FROM compliance_comparisons WHERE id = ?
                """, (id,))
            elif section_id:
                cursor = await conn.execute("""
                    SELECT * FROM compliance_comparisons WHERE section_id = ?
                """, (section_id,))
            else:
                return []
            rows = await cursor.fetchall()
            comparisons = [dict(row) for row in rows]
            for comparison in comparisons:
                if comparison.get("comparison_result"):
                    comparison["comparison_result"] = json.loads(
                        comparison["comparison_result"])
            if id:
                return comparisons[0]
            elif section_id:
                return comparisons
            else:
                return []

    async def get_compliance_comparisons_list(self, section_id: int) -> list[int]:
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
            SELECT id, package_name_a, package_name_b, score_a, score_b, overall_winner
                FROM compliance_comparisons WHERE section_id = ?
            """, (section_id,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


db = ModuDB()

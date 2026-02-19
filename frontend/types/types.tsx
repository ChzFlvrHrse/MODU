export interface Project {
    id: number;
    spec_id: string;
    project_name: string;
    total_divisions: number;
    total_sections: number;
    sections_with_primary: number;
    sections_reference_only: number;
    status: string;
    errors: number;
    created_at: string;
    updated_at: string;
}

export interface Section {
    id: number;
    spec_id: string;
    division: string;
    section_number: string;
    section_name: string;
    primary_pages: number[];
    reference_pages: number[];
    summary: string | null;
    status: string | null;
    created_at: string;
    updated_at: string | null;
}

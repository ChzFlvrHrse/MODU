export interface Project {
    id: number;
    spec_id: string;
    project_name: string;
    total_divisions: number;
    total_sections: number;
    sections_with_primary: number;
    sections_with_reference: number;
    classification_status: string;
    summary_status: string;
    project_completion_score: number | null;
    errors: number;
    created_at: string;
    updated_at: string;
}

export interface Section {
    id: number;
    spec_id: string;
    division: string;
    section_number: string;
    section_title: string;
    primary_pages: number[];
    reference_pages: number[];
    classification_status: string;
    summary_status: string;
    created_at: string;
    updated_at: string | null;
}

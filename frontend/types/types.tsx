export interface Project {
    spec_id: string;
    total_divisions: number;
    total_sections: number;
    sections_with_primary: number;
    sections_reference_only: number;
    errors: number;
    created_at: string;
    updated_at: string;
    status: string;
}

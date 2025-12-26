# MODU
<!-- Start up directions -->
cd into backend folder

CLI Commands:
pip install -r requirements.txt
python app.py (ran locally)

<!-- Ran on Python 3.9.4 -->
<!-- There is a test folder with the regex section detection code. Not currently implemented -->

## API Endpoints

### Upload Routes (`/api/upload`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/upload_to_s3` | Upload an original PDF file to S3 bucket. Returns a unique `spec_id` for the uploaded file. |
| POST | `/text_and_rasterize` | Convert an existing PDF (by `spec_id`) to text or rasterize pages. Supports optional parameters: `start_index`, `end_index`, `rasterize_all`, `dpi`, `grayscale`. |
| POST | `/upload_and_convert_pdf` | Combines upload and conversion in one step. Uploads a PDF to S3 and then converts it to text/rasterized images. |
| GET | `/get_original_pdf/<spec_id>` | Retrieve the original PDF by its `spec_id`. |

### Division Breakdown Routes (`/api/division_breakdown`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/table_of_contents` | Detect and extract table of contents from a spec. Requires `spec_id`. Returns `toc_indices`. |
| POST | `/divisions_and_sections` | Parse and return division/section breakdown. Requires `spec_id` and `toc_indices`. Supports optional `start_index` and `end_index`. |

### Section Specs Routes (`/api/section_specs`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/section_spec_pages` | Detect pages for specific sections. Requires `spec_id` and `section_numbers`. Also performs primary/context classification. |
| POST | `/section_spec_requirements` | Extract requirements from section spec pages. Requires `spec_id`, `division_section_pages`, and `section_number`. |

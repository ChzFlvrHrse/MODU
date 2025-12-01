import asyncio
from dotenv import load_dotenv
from division_detection import all_divisions
from section_spec_detection import analyze_section, analyze_all_sections

load_dotenv()

__all__ = ["all_divisions", "analyze_section", "analyze_all_sections"]

# divisions = asyncio.run(all_divisions(start_page=0, end_page=15))
# print(divisions)

# analyzed_section = asyncio.run(analyze_section(pdf_path="example_spec.pdf", section_number=divisions["divisions_detected"][0]["section"][1]["section_number"], section_title=divisions["divisions_detected"][0]["section"][1]["title"]))
# print(analyzed_section)

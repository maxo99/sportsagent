import re
from pathlib import Path


def get_reports():
    reports = []
    outputs_dir = Path("data/outputs")
    if not outputs_dir.exists():
        return reports

    for report_dir in outputs_dir.iterdir():
        if report_dir.is_dir():
            report_file = report_dir / "report.md"
            if report_file.exists():
                # Extract a readable name from the directory name
                # Format: YYYYMMDD_HHMMSS_Query_Text
                dir_name = report_dir.name
                parts = dir_name.split("_", 2)
                if len(parts) >= 3:
                    date_str = parts[0]
                    time_str = parts[1]
                    query_slug = parts[2]
                    readable_name = f"{date_str}-{time_str}: {query_slug.replace('_', ' ')}"
                else:
                    readable_name = dir_name

                reports.append({"name": readable_name, "path": str(report_file)})

    # Sort reports by name (which includes timestamp) descending
    reports.sort(key=lambda x: x["name"], reverse=True)
    return reports


def update_readme():
    readme_path = Path("README.md")
    if not readme_path.exists():
        print("README.md not found.")
        return

    content = readme_path.read_text()

    start_marker = "<!-- REPORTS-START -->"
    end_marker = "<!-- REPORTS-END -->"

    reports = get_reports()

    new_section_content = f"{start_marker}\n## Generated Reports\n\n"
    if not reports:
        new_section_content += "No reports generated yet.\n"
    else:
        for report in reports:
            # Create a relative link
            link_path = report["path"]
            new_section_content += f"- [{report['name']}]({link_path})\n"
    new_section_content += f"{end_marker}"

    pattern = re.compile(f"{re.escape(start_marker)}.*?{re.escape(end_marker)}", re.DOTALL)

    if pattern.search(content):
        new_content = pattern.sub(new_section_content, content)
        print("Updated existing reports section.")
    else:
        new_content = content + "\n\n" + new_section_content
        print("Appended reports section to README.md.")

    readme_path.write_text(new_content)


if __name__ == "__main__":
    update_readme()

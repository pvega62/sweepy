import yaml
import os
import questionary
from pathlib import Path

def run_wizard():
    print("╔══════════════════════════════════════════════════╗")
    print("║     Career Sweep Engine — Profile Setup Wizard   ║")
    print("╚══════════════════════════════════════════════════╝\n")

    name = questionary.text("What is your name?").ask()
    
    titles_str = questionary.text(
        "What job titles are you looking for? (Separate multiple titles with a comma)"
    ).ask()
    titles = [t.strip() for t in titles_str.split(",") if t.strip()]

    location = questionary.text("Where do you want to work? (City, State):").ask()
    
    remote_only = questionary.confirm("Do you want to include remote roles only?").ask()
    
    resume_path = questionary.path("What is the absolute path to your resume PDF?").ask()
    
    min_salary_str = questionary.text("What is your minimum target salary? (Leave blank to skip):").ask()
    min_salary = int(min_salary_str) if min_salary_str.isdigit() else 0

    skills_str = questionary.text(
        "What are your top 5 must-have skills? (Comma separated, e.g., React, Figma, Contract Law)"
    ).ask()
    must_have_skills = [s.strip() for s in skills_str.split(",") if s.strip()]

    formats = questionary.checkbox(
        "What export formats do you want?",
        choices=[
            questionary.Choice("PDF Report", value="pdf", checked=True),
            questionary.Choice("CSV Spreadsheet", value="csv", checked=True),
            questionary.Choice("JSON Data", value="json")
        ]
    ).ask()

    profile_data = {
        "name": name,
        "search": {
            "titles": titles,
            "location": location,
            "remote_only": remote_only,
            "min_salary": min_salary
        },
        "resume": {
            "path": resume_path.replace("\\", "/"),
            "must_have_skills": must_have_skills,
            "keywords_weight": 1.5
        },
        "export": {
            "format": ",".join(formats) if formats else "pdf",
            "output_dir": "results"
        }
    }

    # Save to a generic custom name, or specific name
    safe_name = name.lower().replace(" ", "_") if name else "custom"
    file_path = f"profiles/{safe_name}_profile.yaml"
    
    os.makedirs("profiles", exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        yaml.dump(profile_data, f, sort_keys=False, default_flow_style=False)
    
    print(f"\n✅ Profile saved to: {file_path}")
    return file_path

def load_config(config_path):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

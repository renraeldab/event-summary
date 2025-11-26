from pathlib import Path
import json
import argparse

from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path(__file__).resolve().parent
DATA_DIR = TEMPLATE_DIR.parent / "data"


def sort_entities(entities: list[dict]) -> list[dict]:
    """Group and sort entities."""
    entity_types = ("Person", "Creature", "Organization", "Location", "Event", "Concept", "Method", "Artifact")
    sorted_entities = []
    for entity_type in entity_types:
        _entities = [entity for entity in entities if entity["type"] == entity_type]
        if entity_type == "Event":
            _entities.sort(key=lambda e: e["time"])
        sorted_entities.extend(_entities)
    return sorted_entities


def load_json_data() -> list:
    """Load all JSON files from the data directory."""
    data = []
    if not DATA_DIR.exists():
        return data
    data = []
    for json_file in sorted(DATA_DIR.iterdir()):
        if not json_file.is_file() or json_file.suffix.lower() != ".json":
            continue
        with json_file.open(encoding="utf-8") as f:
            data.append({
                "query": json_file.stem,
                "output": json.load(f)
            })
        data[-1]["output"]["entities"] = sort_entities(data[-1]["output"]["entities"])
    return data


def generate_html(data: list, output_file: str) -> None:
    """Generate HTML using Jinja2 template."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=True)
    template = env.get_template("template.html")
    html_content = template.render(data=data)
    with open(output_file, 'w', encoding="utf-8") as f:
        f.write(html_content)
    print(f"Generated {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output_file", type=str, help="Output file", default="event summary.html")
    args = parser.parse_args()
    generate_html(load_json_data(), args.output_file)
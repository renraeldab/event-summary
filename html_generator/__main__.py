from pathlib import Path
import json
from jinja2 import Environment, FileSystemLoader


def load_json_files(data_dir):
    data = []
    data_dir_path = Path(data_dir)
    if not data_dir_path.exists():
        return data

    for f in sorted(data_dir_path.iterdir()):
        if f.is_file() and f.suffix.lower() == ".json":
            with open(f, "r", encoding="utf-8") as fp:
                obj = json.load(fp)
                data.append({
                    "query": f.stem,
                    "output": obj
                })
    return data


def generate_html(data, output_file):
    template_dir = Path(__file__).resolve().parent
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=True
    )
    template = env.get_template("template.html")
    html = template.render(data=data)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)

    print("Generated:", output_file)


def main():
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    data = load_json_files(data_dir)
    generate_html(data, "event_summary.html")


if __name__ == "__main__":
    main()
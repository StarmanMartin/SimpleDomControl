import json
import shutil
from os import makedirs
from pathlib import Path

from django.core.management import BaseCommand
from sdc_core.sdc_extentions.models import all_models

def generate_field_config(field):
    config = {
        "type": field["type"],
        "required": not field["null"] and not field["blank"],
        "max_length": field.get("max_length"),
        "is_relation": field["is_relation"],
        "many_to_many": field["many_to_many"],
        "one_to_many": field["one_to_many"],
        "many_to_one": field["many_to_one"],
        "one_to_one": field["one_to_one"],
        "related_model": field["related_model"],
        "remote_field": field["remote_field"],
    }

    if field["type"] == "FileField":
        config.update({
            # optional — you can hardcode or extract from validators
            "max_size": 5 * 1024 * 1024 * 1024,  # 5 MB
            "allowed_types": None,        # or list of mime types
        })

    return config

def generate_schema_js(fields):
    schema = {
        f["name"]: generate_field_config(f)
        for f in fields
    }
    return '  static fields = ' + '\n    '.join(json.dumps(schema, indent=2).split('\n'))

def _generate_js_class(schema):
    class_name = schema["model"]

    lines = ["import {SdcModel, SdcQuerySet} from 'sdc_client';", "", f"export default class {class_name} extends SdcModel {{", ""]
    constructor_line = ["  constructor(data = {}) {", f'    super("{class_name}");', f'    this._toManyFields = [];']
    setter_line = ["  setValues(data = {}) {", f'    data.id ??= data.pk ?? null;']
    getter = []
    setter = []

    field_settings = ["", generate_schema_js(schema["fields"]),""]


    for field in schema["fields"]:
        name = field["name"]
        setter.append(f"  set {name}(value){{")
        setter.append(f"    this.validate(value, {class_name}.fields.{name});")
        getter.append(f"  get {name}(){{")
        if name == 'id':
            setter.append("    this._toManyFields.forEach((x) => x.setFilter({id: value}));")

        if field["is_relation"] and field["related_model"]:
            constructor_line.append(f"    this._{name} = new SdcQuerySet('{field['related_model']}');")
            if field["many_to_many"] or field["one_to_many"]:
                constructor_line.append(f"    this._toManyFields.push(this._{name});")
                setter_line.append(f"    this.{name}.setFilter({{ {field['remote_field']}:  data.id }});")
                setter_line.append(f"    this.{name}.setIds(data.{name} || [])")
                setter.append(f"    this._{name}.setIds(this.parseValue(value, {class_name}.fields.{name}));")
                getter.append(f"    return this._{name};")
            else:
                setter_line.append(f"    this.{name}.filter({{ id: data.{name} }});")
                setter.append(f"    this._{name}.setIds(this.parseValue(value, {class_name}.fields.{name}));")
                getter.append(f"    return this._{name}.length > 0 ? this._{name}[0] : this._{name}.new();")
        else:
            constructor_line.append(f"    this._{name} = null;")
            setter_line.append("    try {")
            setter_line.append(f"      this.{name} = data.{name} ?? null;")
            setter_line.append("    } catch {} ")
            getter.append(f"    return this._{name};")
            setter.append(f"    this._{name} = this.parseValue(value, {class_name}.fields.{name});")
        setter.append("  }\n")
        getter.append("  }\n")
    constructor_line.append("    this.setValues(data);")
    constructor_line.append("  }")
    setter_line.append("  }")

    lines += field_settings + constructor_line + [""] + setter_line + [""] + setter + [""] + getter
    lines.append("}")
    return "\n".join(lines)

def _get_model_schema(model):
    fields = []

    for field in model._meta.get_fields():
        field_info = {
            # "name": field.name,
            "name": field.accessor_name if hasattr(field, 'accessor_name') else field.name,
            "type": field.get_internal_type() if hasattr(field, "get_internal_type") else "Unknown",
            "null": getattr(field, "null", False),
            "blank": getattr(field, "blank", False),
            "max_length": getattr(field, "max_length", None),
            "is_relation": field.is_relation,
            "many_to_many": field.many_to_many,
            "many_to_one": field.many_to_one,
            "one_to_many": field.one_to_many,
            "one_to_one": field.one_to_one,
            "related_model": field.related_model.__name__ if field.related_model else None,
            "remote_field": field.remote_field.name if field.related_model else None,
        }
        fields.append(field_info)

    return {
        "model": model.__name__,
        "app": model._meta.app_label,
        "fields": fields,
    }

def _prepare_js_models():
    file_path = Path('Assets/src/models')
    if file_path.exists():
        shutil.rmtree(file_path)
    makedirs(file_path, exist_ok=True)
    src_js = [f"import {{ registerModel }} from 'sdc_client';", ""]
    for name, model in all_models().items():
        src_js.insert(0, f"import {name} from './{name}.js';")
        src_js.append(f'registerModel("{name}", {name});')
        ms = _get_model_schema(model)
        with open(file_path / f'{name}.js', 'w+') as f:
            f.write(_generate_js_class(ms))
    with open(file_path / 'src.js', 'w+') as f:
        f.write('\n'.join(src_js))

class Command(BaseCommand):
    help = 'This function links all templates into the controller directory'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **ops):
        _prepare_js_models()

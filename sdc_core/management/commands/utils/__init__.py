import sys

from django.core.management import CommandError

from sdc_core.sdc_extentions.models import filter_model_fields


def multi_cli_select(prompt, options):
    if len(options) == 0:
        print(prompt)
        raise CommandError("No options selectable")
    if sys.stdin.isatty():
        from InquirerPy import inquirer
        selected = inquirer.checkbox(
            message=f"{prompt} (With space key)",
            choices=options
        ).execute()
    else:
        print(f"{prompt} (comma-separated numbers):")
        for i, opt in enumerate(options, 1):
            print(f"{i}. {opt}")

        user_input = input("Enter your choices (e.g. 1,3): ").strip()

        try:
            selected_indexes = [int(x.strip()) - 1 for x in user_input.split(",")]
            selected = [options[i] for i in selected_indexes if 0 <= i < len(options)]

        except  ValueError or IndexError:
            raise CommandError("Input has to be a list of numbers between 1 and %d" % (len(options) - 1), 4)
        print(f"You selected: {', '.join(selected)}")
    return selected


def cli_select(prompt, options):
    if len(options) == 0:
        print(prompt)
        raise CommandError("No options selectable")
    if sys.stdin.isatty():
        from InquirerPy import inquirer
        choice = inquirer.select(
            message=prompt,
            choices=options,
            default=options[-1],
        ).execute()
    else:
        # Fallback
        print(prompt)
        for i, option in enumerate(options, 1):
            print(f"{i}. {option}")
        try:
            idx = int(input("Enter number: [%d]" % (len(options) - 1)) or (len(options) - 1))
            choice = options[idx - 1]
        except ValueError or IndexError:
            raise CommandError("Input has to be a number between 1 and %d" % (len(options) - 1), 4)
        print(f"You selected: {choice}")
    return choice



def get_model_schema(model):
    fields = {}

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

        fields[field_info['name']] = field_info

    return {
        "model": model.__name__,
        "app": model._meta.app_label,
        "fields": filter_model_fields(model, fields).values(),
    }
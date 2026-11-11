"""Compile user instructions and the matching active picture labels."""
from ..references.model import reference_instructions, active_cards


def build_prompt(recipe):
    prompt=recipe['prompt']
    if recipe['kind']=='turnaround':
        from ..turnaround.prompt import turnaround_prompt
        prompt=turnaround_prompt(recipe)
    if not active_cards(recipe):
        return prompt
    return f"Edit <Picture 1>. {prompt}\n\nReference instructions:\n{reference_instructions(recipe)}"

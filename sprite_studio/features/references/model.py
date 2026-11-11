"""Reference identity, validation and numbering have one owner."""
import re

ROLES = {
    'identity': ('Identity', 'Preserve this subject\'s identity, proportions and identifying features.'),
    'detail': ('Face / detail', 'Use the specified face or small identifying details.'),
    'clothing': ('Clothing / equipment', 'Use this clothing or equipment while preserving the primary identity.'),
    'construction': ('Side / back construction', 'Use this view to resolve hidden shape and construction.'),
    'style': ('Style', 'Use the rendering style while retaining the primary subject and geometry.'),
    'composition': ('Composition', 'Use the specified framing or arrangement.'),
}


def validate_cards(cards):
    if not isinstance(cards, list) or len(cards) > 32:
        raise ValueError('Keep at most 32 cards, with up to eight enabled.')
    result = []
    for card in cards:
        if not isinstance(card, dict) or not re.fullmatch(r'[0-9a-f]{32}', str(card.get('asset_id', ''))):
            raise ValueError('Select a saved reference image.')
        role = card.get('role', 'identity')
        if role not in ROLES:
            raise ValueError('Choose a supported reference role.')
        note = str(card.get('note', '')).strip()
        if len(note) > 2000:
            raise ValueError('Keep each reference instruction under 2,000 characters.')
        result.append({'asset_id': card['asset_id'], 'role': role, 'note': note, 'enabled': bool(card.get('enabled', True))})
    if sum(c['enabled'] for c in result) > 8:
        raise ValueError('P-H3 accepts up to eight enabled reference pictures.')
    return result


def active_cards(recipe):
    return [c for c in recipe.get('references', []) if c['enabled']]


def reference_instructions(recipe):
    return '\n'.join(f"<Picture {i}> — {ROLES[c['role']][1]} {c['note']}".strip() for i, c in enumerate(active_cards(recipe), 1))

"""Persistent walkthrough progress; kept separate from credentials and user content."""
from .config import read_config, update_config
STEPS = 6

def current():
    saved = read_config().get('walkthrough', {})
    if not isinstance(saved, dict): saved = {}
    step = saved.get('step', 0)
    return {'step': step if type(step) is int and 0 <= step < STEPS else 0,
            'dismissed': saved.get('dismissed') is True,
            'completed': saved.get('completed') is True}

def save(data):
    if set(data) - {'step', 'dismissed', 'completed'}:
        raise ValueError('Unknown walkthrough field.')
    result = current()
    for key, value in data.items():
        if key == 'step':
            if type(value) is not int or not 0 <= value < STEPS:
                raise ValueError('Invalid walkthrough step.')
        elif type(value) is not bool:
            raise ValueError('Expected a boolean.')
        result[key] = value
    update_config({'walkthrough': result})
    return result

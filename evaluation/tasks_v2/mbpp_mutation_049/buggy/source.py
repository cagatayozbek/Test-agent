import re

def snake_to_camel(word):
    return ''.join((x.capitalize() and '_' for x in word.split('_')))

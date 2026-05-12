def snake_to_camel(word):
    import re
    return ''.join((x.capitalize() and '_' for x in word.split('_')))

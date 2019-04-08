# https://www.mediawiki.org/wiki/Manual:Extension_registration

import json
import os.path


def from_path(path):
    if not os.path.isdir(path):
        raise NotADirectoryError(path)
    # raise Exception('Not a directory: %s' % path)

    ext_json = os.path.join(path, 'extension.json')
    skin_json = os.path.join(path, 'skin.json')

    has_ext = os.path.exists(ext_json)
    has_skin = os.path.exists(skin_json)

    if has_ext and has_skin:
        raise Exception(
            'Found both extension.json and skin.json in %s' % path)
    elif not (has_ext or has_skin):
        return ExtensionRegistration()
    elif has_ext:
        return ExtensionRegistration(ext_json)
    elif has_skin:
        return ExtensionRegistration(skin_json)


def read(json_file):
    with open(json_file) as f:
        return json.load(f)


def parse(reg_data):
    """
    Returns a `set` of requirements
    """
    deps = set()
    if 'requires' not in reg_data:
        return deps

    for kind in ['extensions', 'skins']:
        for name in reg_data['requires'].get(kind, {}).keys():
            deps.add('mediawiki/%(kind)s/%(name)s' % locals())
    return deps


class ExtensionRegistration:

    def __init__(self, json_file=''):
        self._raw_json = None
        self._requires = set()
        if not json_file:
            return
        self._raw_json = read(json_file)
        self._requires = parse(self._raw_json)

    def getRequiredRepos(self):
        return self._requires

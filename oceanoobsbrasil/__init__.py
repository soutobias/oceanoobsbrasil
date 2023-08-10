from os.path import dirname, isfile

version_file = "{}/version.txt".format(dirname(__file__))

if isfile(version_file):
    with open(version_file) as version_file:
        __version__ = version_file.read().strip()

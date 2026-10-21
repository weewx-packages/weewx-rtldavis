"""Build a WeeWX archive without generated files or an embedded native binary."""
import ast
from pathlib import Path
import zipfile


def build():
    """Return the path to an archive whose version matches the driver and installer.

    Returns:
        pathlib.Path: Versioned extension archive in dist/.
    """
    root = Path(__file__).resolve().parents[1]
    tree = ast.parse((root / 'bin/user/rtldavis.py').read_text(encoding='latin-1'))
    version = next(ast.literal_eval(node.value) for node in tree.body
                   if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == 'DRIVER_VERSION'
                           for target in node.targets))
    if 'version="%s"' % version not in (root / 'install.py').read_text():
        raise ValueError('Installer and driver versions differ')
    name = 'weewx-rtldavis-%s' % version
    output = root / 'dist' / (name + '.zip')
    output.parent.mkdir(exist_ok=True)
    sources = ['install.py', 'bin', 'docs', 'README.md', 'CHANGELOG.md', 'changelog', 'license']
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for source in sources:
            path = root / source
            for file in sorted(path.rglob('*')) if path.is_dir() else [path]:
                if file.is_file() and '__pycache__' not in file.parts and file.suffix != '.pyc':
                    archive.write(file, str(Path(name) / file.relative_to(root)))
    return output


if __name__ == '__main__':
    print(build())

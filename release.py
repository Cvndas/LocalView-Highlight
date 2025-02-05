import os
import zipfile
import re
import shutil
import subprocess
import argparse

extension_folder = 'autokey_highlight'
path_to_blender = 'C:\\AppInstall\\Blender\\stable\\blender-4.3.2-stable.32f5fdce0a0a\\blender.exe'


def get_base_path():
    return os.path.dirname(os.path.abspath(__file__))


def read_version_init(base_path):
    init_path = os.path.join(base_path, extension_folder, '__init__.py')
    if not os.path.exists(init_path):
        raise FileNotFoundError(f"File not found: {init_path}")
    with open(init_path, 'r') as file:
        content = file.read()
    match = re.search(r'[\'"]version[\'"]\s*:\s*\((\d+),\s*(\d+),\s*(\d+)\)', content)
    if match:
        return tuple(map(int, match.groups()))
    raise ValueError("Version not found in __init__.py")


def read_version_toml(base_path):
    toml_path = os.path.join(base_path, extension_folder, 'blender_manifest.toml')
    if not os.path.exists(toml_path):
        raise FileNotFoundError(f"File not found: {toml_path}")
    with open(toml_path, 'r') as file:
        content = file.read()
    match = re.search(r'^version\s*=\s*"(\d+)\.(\d+)\.(\d+)"', content, re.MULTILINE)
    if match:
        return tuple(map(int, match.groups()))
    raise ValueError("Version not found in blender_manifest.toml")


def create_dev_copy(base_path):
    """ Creates a '_dev' copy of the extension and updates metadata. """
    dev_folder = extension_folder + "_dev"
    dev_path = os.path.join(base_path, dev_folder)

    if os.path.exists(dev_path):
        shutil.rmtree(dev_path)
    shutil.copytree(os.path.join(base_path, extension_folder), dev_path)

    # Modify __init__.py
    init_path = os.path.join(dev_path, '__init__.py')
    with open(init_path, 'r') as file:
        content = file.read()
    content = re.sub(r'("name"\s*:\s*)"([^"]+)"', r'\1"\2_dev"', content)
    content = re.sub(r'("id"\s*:\s*)"([^"]+)"', r'\1"\2_dev"', content)
    with open(init_path, 'w') as file:
        file.write(content)

    # Modify blender_manifest.toml
    toml_path = os.path.join(dev_path, 'blender_manifest.toml')
    with open(toml_path, 'r') as file:
        content = file.read()
    content = re.sub(r'^(name\s*=\s*)"([^"]+)"', r'\1"\2_dev"', content, flags=re.MULTILINE)
    content = re.sub(r'^(id\s*=\s*)"([^"]+)"', r'\1"\2_dev"', content, flags=re.MULTILINE)
    with open(toml_path, 'w') as file:
        file.write(content)

    return dev_folder


def create_zip(base_path, version, source_folder):
    """ Builds the extension using Blender's `--command extension build` tool. """
    if not os.path.exists(f'{base_path}\\Releases'):
        os.mkdir(f'{base_path}\\Releases')

    output_name = f'extension_{source_folder}_v{version[0]}-{version[1]}-{version[2]}.zip'
    command = f'{path_to_blender} --factory-startup --command extension build '
    command += f'--source-dir "{base_path}\\{source_folder}" '
    command += f'--output-filepath "{base_path}\\Releases\\{output_name}"'
    subprocess.call(command)
    print(f"Release zip created: {output_name}")


def main():
    parser = argparse.ArgumentParser(description="Blender Extension Release Script")
    parser.add_argument("--dev", action="store_true", help="Create a development build with '_dev' suffix.")
    args = parser.parse_args()

    base_path = get_base_path()

    if not os.path.isfile(path_to_blender):
        print(f"Error: Blender Executable not found in:\n    `{path_to_blender}`")
        return
    elif not os.path.isdir(os.path.join(base_path, extension_folder)):
        print(f"Error: Extension not found in:\n    `{base_path}\\{extension_folder}`")
        return
    else:
        print(f"Found Blender Executable and Extension. Proceeding!")

    try:
        version_init = read_version_init(base_path)
        version_toml = read_version_toml(base_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"Error: {e}")
        return

    if version_init != version_toml:
        print("Version mismatch detected.")
        new_version = input("Enter new version (X.Y.Z): ")
        try:
            version_tuple = tuple(map(int, new_version.split('.')))
            if len(version_tuple) != 3:
                raise ValueError
        except ValueError:
            print("Invalid version format.")
            return
    else:
        version_tuple = version_init

    source_folder = extension_folder
    if args.dev:
        print("Creating development build...")
        source_folder = create_dev_copy(base_path)

    create_zip(base_path, version_tuple, source_folder)


if __name__ == '__main__':
    main()

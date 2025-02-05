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
    """ Extracts version from __init__.py """
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
    """ Extracts version from blender_manifest.toml """
    toml_path = os.path.join(base_path, extension_folder, 'blender_manifest.toml')
    if not os.path.exists(toml_path):
        raise FileNotFoundError(f"File not found: {toml_path}")
    with open(toml_path, 'r') as file:
        content = file.read()
    match = re.search(r'^version\s*=\s*"(\d+)\.(\d+)\.(\d+)"', content, re.MULTILINE)
    if match:
        return tuple(map(int, match.groups()))
    raise ValueError("Version not found in blender_manifest.toml")


def get_latest_zip_version(base_path):
    """ Finds the latest released ZIP version in the Releases folder """
    releases_dir = os.path.join(base_path, "Releases")
    if not os.path.exists(releases_dir):
        return None

    latest_version = None
    version_pattern = re.compile(rf'extension_{extension_folder}_v(\d+)-(\d+)-(\d+)\.zip')

    for filename in os.listdir(releases_dir):
        match = version_pattern.match(filename)
        if match:
            version = tuple(map(int, match.groups()))
            if latest_version is None or version > latest_version:
                latest_version = version

    return latest_version


def update_version_files(base_path, version):
    """ Updates the version in __init__.py and blender_manifest.toml """
    version_str = f'"version": ({version[0]}, {version[1]}, {version[2]})'
    init_path = os.path.join(base_path, extension_folder, '__init__.py')
    with open(init_path, 'r') as file:
        content = file.read()
    content = re.sub(r'"version"\s*:\s*\(\d+, \d+, \d+\)', version_str, content)
    with open(init_path, 'w') as file:
        file.write(content)

    version_str = f'version = "{version[0]}.{version[1]}.{version[2]}"'
    toml_path = os.path.join(base_path, extension_folder, 'blender_manifest.toml')
    with open(toml_path, 'r') as file:
        content = file.read()
    content = re.sub(r'^version\s*=\s*"\d+\.\d+\.\d+"', version_str, content, flags=re.MULTILINE)
    with open(toml_path, 'w') as file:
        file.write(content)


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

    version_init = read_version_init(base_path)
    version_toml = read_version_toml(base_path)
    latest_zip_version = get_latest_zip_version(base_path)

    # If init.py and toml versions don't match, ask the user to manually enter a version
    if version_init != version_toml:
        print(f"Version mismatch detected:    init: {version_init}    toml: {version_toml}")
        new_version = input("Enter new version (X.Y.Z) or press Enter to keep the current version: ").strip()
        if new_version:
            try:
                version_tuple = tuple(map(int, new_version.split('.')))
                if len(version_tuple) != 3:
                    raise ValueError
                print(f"Using manually entered version: {version_tuple}")
            except ValueError:
                print("Invalid version format. Aborting.")
                return
        else:
            version_tuple = version_init  # Keep the existing version

    else:
        version_tuple = version_init  # Versions match, proceed normally

    # If latest ZIP matches the current version, ask whether to overwrite or increment
    if not args.dev and latest_zip_version == version_tuple:
        print(f"A release with version {latest_zip_version} already exists.")
        while True:
            response = input("Do you want to (O)verwrite, (I)ncrement version, or (C)ancel? (O/I/C): ").strip().lower()
            if response == 'o':
                break  # Proceed with overwriting
            elif response == 'i':
                new_version = input("Enter new version (X.Y.Z): ").strip()
                try:
                    version_tuple = tuple(map(int, new_version.split('.')))
                    if len(version_tuple) != 3:
                        raise ValueError
                    update_version_files(base_path, version_tuple)  # ✅ Now we update the files
                    break
                except ValueError:
                    print("Invalid version format. Try again.")
            elif response == 'c':
                print("Operation canceled.")
                return
            else:
                print("Invalid input. Please enter O, I, or C.")

    source_folder = create_dev_copy(base_path) if args.dev else extension_folder
    create_zip(base_path, version_tuple, source_folder)



if __name__ == '__main__':
    main()

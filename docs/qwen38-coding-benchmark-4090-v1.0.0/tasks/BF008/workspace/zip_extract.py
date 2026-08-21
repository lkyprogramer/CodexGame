import zipfile
def safe_extract(zip_path,destination):
    with zipfile.ZipFile(zip_path) as z:z.extractall(destination)

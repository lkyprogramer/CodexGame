import os, re, shutil, stat, zipfile
from pathlib import Path, PurePosixPath, PureWindowsPath
def safe_extract(zip_path,destination):
    dest=Path(destination).resolve(strict=False)
    plans=[];seen=set()
    try:
        archive=zipfile.ZipFile(zip_path)
    except Exception as exc:raise ValueError('invalid zip') from exc
    with archive:
        for info in archive.infolist():
            name=info.filename
            if not name or '\x00' in name:raise ValueError('invalid member name')
            normalized=name.replace('\\','/')
            posix=PurePosixPath(normalized);win=PureWindowsPath(name)
            if posix.is_absolute() or win.is_absolute() or win.drive or any(part=='..' for part in posix.parts):raise ValueError('unsafe path')
            mode=info.external_attr>>16
            if stat.S_ISLNK(mode):raise ValueError('symlink forbidden')
            target=(dest/Path(*posix.parts)).resolve(strict=False)
            if os.path.commonpath([str(dest),str(target)])!=str(dest):raise ValueError('escape')
            key=os.path.normcase(str(target))
            if key in seen:raise ValueError('duplicate target')
            seen.add(key);plans.append((info,target))
        dest.mkdir(parents=True,exist_ok=True)
        for info,target in plans:
            if info.is_dir():target.mkdir(parents=True,exist_ok=True);continue
            target.parent.mkdir(parents=True,exist_ok=True)
            with archive.open(info) as src,target.open('wb') as out:shutil.copyfileobj(src,out)

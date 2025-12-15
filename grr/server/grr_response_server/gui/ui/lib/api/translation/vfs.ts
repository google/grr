import {
  BrowseFilesystemEntry,
  BrowseFilesystemResult,
  Directory,
  File,
  FileContent,
  PathSpecPathType,
  StatEntry,
} from '../../models/vfs';
import {assertEnum, assertKeyNonNull, assertNonNull} from '../../preconditions';
import {
  ApiBrowseFilesystemEntry,
  ApiBrowseFilesystemResult,
  ApiFile,
  ApiGetFileTextResult,
} from '../api_interfaces';
import {isStatEntry, translateHashToHex, translateStatEntry} from './flow';
import {createDate} from './primitive';

const VFS_PATH_RE = /^(\/*fs\/+)?([a-z]+)(.*)$/;

/** Splits a VFS path "fs/os/foo" into PathType "OS" and path "/foo". */
export function parseVfsPath(vfsPath: string): {
  pathtype: PathSpecPathType;
  path: string;
} {
  const match = VFS_PATH_RE.exec(vfsPath);
  assertNonNull(match, 'match');

  const pathtype = match[2].toUpperCase();
  assertEnum(pathtype, PathSpecPathType);

  return {pathtype, path: match[3]};
}

/** Constructs a File or Directory from the corresponding API data structure */
export function translateFile(file: ApiFile): File | Directory {
  assertKeyNonNull(file, 'isDirectory');
  assertKeyNonNull(file, 'name');
  assertKeyNonNull(file, 'path');
  assertKeyNonNull(file, 'age');

  const {path, pathtype} = parseVfsPath(file.path);

  let stat: StatEntry | undefined;
  if (file.stat) {
    stat = translateStatEntry(file.stat);
    if (!isStatEntry(stat)) {
      throw new Error(
        'translateFile only works for non-Registry files for now.',
      );
    }
  }

  const base = {
    name: file.name,
    path,
    pathtype,
    stat,
    lastMetadataCollected: createDate(file.age),
    isDirectory: file.isDirectory,
  };

  if (base.isDirectory) {
    return base as Directory;
  }

  let lastContentCollected: File['lastContentCollected'];

  if (file.lastCollected) {
    assertKeyNonNull(file, 'lastCollectedSize');

    lastContentCollected = {
      timestamp: createDate(file.lastCollected),
      size: BigInt(file.lastCollectedSize),
    };
  }

  return {
    ...base,
    type: file.type,
    hash: file.hash ? translateHashToHex(file.hash) : undefined,
    lastContentCollected,
  };
}

/** Constructs a FilesystemEntry from the corresponding API data structure */
export function translateBrowseFilesystemEntry(
  entry: ApiBrowseFilesystemEntry,
): BrowseFilesystemEntry {
  return {
    file: entry.file ? translateFile(entry.file) : undefined,
    children: entry.children?.map(translateBrowseFilesystemEntry) ?? undefined,
  };
}

/** Constructs a BrowseFilesystemResult from the corresponding API data structure */
export function translateBrowseFilesystemResult(
  result: ApiBrowseFilesystemResult,
): BrowseFilesystemResult {
  return {
    rootEntry: result.rootEntry
      ? translateBrowseFilesystemEntry(result.rootEntry)
      : undefined,
  };
}

/** Translates from ApiGetFileTextResult to internal FileContent model */
export function translateApiGetFileTextResult(
  result: ApiGetFileTextResult,
): FileContent {
  return {
    totalLength: BigInt(result.totalSize ?? 0),
    textContent: result.content,
  };
}

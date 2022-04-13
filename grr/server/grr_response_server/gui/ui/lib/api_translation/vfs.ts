import {ApiBrowseFilesystemResult, ApiFile} from '../api/api_interfaces';
import {Directory, File, PathSpecPathType} from '../models/vfs';
import {assertEnum, assertKeyNonNull, assertNonNull} from '../preconditions';
import {toMap} from '../type_utils';

import {isStatEntry, translateHashToHex, translateStatEntry} from './flow';
import {createDate} from './primitive';

const VFS_PATH_RE = /^(\/*fs\/+)?([a-z]+)(.*)$/;

/** Splits a VFS path "fs/os/foo" into PathType "OS" and path "/foo". */
export function parseVfsPath(vfsPath: string):
    {pathtype: PathSpecPathType, path: string} {
  const match = VFS_PATH_RE.exec(vfsPath);
  assertNonNull(match, 'match');

  const pathtype = match[2].toUpperCase();
  assertEnum(pathtype, PathSpecPathType);

  return {pathtype, path: match[3]};
}

/** Constructs a File or Directory from the corresponding API data structure */
export function translateFile(file: ApiFile): File|Directory {
  assertKeyNonNull(file, 'isDirectory');
  assertKeyNonNull(file, 'name');
  assertKeyNonNull(file, 'path');

  const {path, pathtype} = parseVfsPath(file.path);

  const base = {
    name: file.name,
    path,
    pathtype,
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

  assertKeyNonNull(file, 'age');
  assertKeyNonNull(file, 'stat');
  const stat = translateStatEntry(file.stat);

  if (!isStatEntry(stat)) {
    throw new Error('translateFile only works for non-Registry files for now.');
  }

  return {
    ...base,
    type: file.type,
    stat,
    hash: file.hash ? translateHashToHex(file.hash) : undefined,
    lastContentCollected,
    lastMetadataCollected: createDate(file.age),
  };
}

/** Constructs a Map from paths to child entries. */
export function translateBrowseFilesytemResult(
    result: ApiBrowseFilesystemResult):
    Map<string, ReadonlyArray<File|Directory>> {
  return toMap(result.items ?? [], (entry) => {
    assertKeyNonNull(entry, 'path');
    return entry.path;
  }, (entry) => (entry.children ?? []).map(translateFile));
}

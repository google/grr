import {ApiFile} from '../api/api_interfaces';
import {File} from '../models/vfs';
import {assertKeyNonNull} from '../preconditions';

import {isStatEntry, translateHashToHex, translateStatEntry} from './flow';
import {createDate} from './primitive';

/** Constructs a File from the corresponding API data structure */
export function translateFile(file: ApiFile): File {
  let lastCollected: File['lastCollected'];

  if (file.lastCollected) {
    assertKeyNonNull(file, 'lastCollectedSize');

    lastCollected = {
      timestamp: createDate(file.lastCollected),
      size: BigInt(file.lastCollectedSize),
    };
  }

  assertKeyNonNull(file, 'stat');
  const stat = translateStatEntry(file.stat);

  if (!isStatEntry(stat)) {
    throw new Error('translateFile only works for non-Registry files for now.');
  }

  return {
    name: file.name,
    path: file.path,
    type: file.type,
    stat,
    isDirectory: file.isDirectory,
    hash: file.hash ? translateHashToHex(file.hash) : undefined,
    lastCollected,
  };
}

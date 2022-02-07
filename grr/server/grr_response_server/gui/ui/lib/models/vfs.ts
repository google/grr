import {HexHash} from './flow';

/** ApiFile mapping for files. */
export declare interface File {
  readonly isDirectory: false;
  readonly name: string;
  readonly path: string;
  readonly pathtype: PathSpecPathType;
  readonly type?: string;
  readonly stat?: StatEntry;
  readonly hash?: HexHash;
  readonly lastContentCollected?: {
    timestamp: Date,
    size: bigint,
  };
  readonly lastMetadataCollected: Date;
}

/** ApiFile mapping for directories. */
export declare interface Directory {
  readonly isDirectory: true;
  readonly name: string;
  readonly path: string;
  readonly pathtype: PathSpecPathType;
}

/** PathSpec.PathType enum mapping. */
export enum PathSpecPathType {
  UNSET = 'UNSET',
  OS = 'OS',
  TSK = 'TSK',
  REGISTRY = 'REGISTRY',
  TMPFILE = 'TMPFILE',
  NTFS = 'NTFS',
}



/**
 * A PathSpec without PathSpec.nestedPath children. The top-most PathSpec
 * contains the `segments` Array, which contains a flattened view of all nested
 * PathSpecs.
 */
export declare interface PathSpecSegment {
  readonly path: string;
  readonly pathtype: PathSpecPathType;
}

/** Simple PathSpec mapping, ignoring PathTypes like REGISTRY for now. */
export declare interface PathSpec extends PathSpecSegment {
  readonly path: string;
  readonly pathtype: PathSpecPathType;
  readonly segments: ReadonlyArray<PathSpecSegment>;
}

/** StatEntry mapping. */
export declare interface StatEntry {
  readonly stMode?: bigint;
  readonly stIno?: bigint;
  readonly stDev?: bigint;
  readonly stNlink?: bigint;
  readonly stUid?: number;
  readonly stGid?: number;
  readonly stSize?: bigint;
  readonly stAtime?: Date;
  readonly stMtime?: Date;
  readonly stCtime?: Date;
  readonly stBtime?: Date;
  readonly stBlocks?: bigint;
  readonly stBlksize?: bigint;
  readonly stRdev?: bigint;
  readonly stFlagsOsx?: number;
  readonly stFlagsLinux?: number;
  readonly symlink?: string;
  readonly pathspec?: PathSpec;
}

/** Identifier of a VFS File: ClientID, PathType, Path. */
export declare interface FileIdentifier {
  readonly clientId: string;
  readonly pathType: PathSpecPathType;
  readonly path: string;
}

/** Splits a path "/foo/bar" into segments ["/", "/foo", "/foo/bar"]. */
export const scanPath = (path: string): ReadonlyArray<string> => {
  if (!path.startsWith('/')) {
    throw new Error(`Expected path to start with "/", got "${path}"`);
  }

  if (path.endsWith('/')) {
    // Also turns the root path "/" to "".
    path = path.slice(0, path.length - 1);
  }

  const parts = path.split('/');

  for (let i = 1; i < parts.length; i++) {
    const previous = parts[i - 1];
    parts[i] = `${previous}/${parts[i]}`;
  }

  parts[0] = '/';

  return parts;
};

/**
 * Returns true if `child` is a sub-directory of `parent`, e.g. `/foo` is a
 * sub-directory of `/`.
 */
export function isSubDirectory(child: string, parent: string) {
  if (parent.endsWith('/')) {
    parent = parent.slice(0, parent.length - 1);
  }

  if (child.endsWith('/')) {
    child = child.slice(0, child.length - 1);
  }

  if (!child.startsWith(parent)) {
    return false;
  }

  // Return false for siblings that prefix-match, e.g. /foo is not a
  // sub-directory of /fo.
  return parent === '/' || child[parent.length] === '/';
}

/**
 * Returns the depth of a given path, e.g. `/foo` has a depth of 2, `/foo/bar`
 * has a depth of 3.
 */
export function pathDepth(path: string) {
  if (path.endsWith('/')) {
    path = path.slice(0, path.length - 1);
  }
  return path.split('/').length;
}

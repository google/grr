import {HexHash} from './flow';

/** A single entry in a browse filesystem result. */
export declare interface BrowseFilesystemEntry {
  readonly file: File | Directory | undefined;
  children: BrowseFilesystemEntry[] | undefined;
}

/** A browse filesystem result. */
export declare interface BrowseFilesystemResult {
  readonly rootEntry: BrowseFilesystemEntry | undefined;
}

/** Common fields for files and directories. */
export declare interface FileOrDirectory {
  readonly isDirectory: boolean;
  readonly name: string;
  readonly path: string;
  readonly pathtype: PathSpecPathType;
  readonly stat?: StatEntry;
  readonly lastMetadataCollected?: Date;
}

/** ApiFile mapping for files. */
export declare interface File extends FileOrDirectory {
  readonly isDirectory: false;
  readonly type?: string;
  readonly hash?: HexHash;
  readonly lastContentCollected?: {
    timestamp: Date;
    size: bigint;
  };
}

/** ApiFile mapping for directories. */
export declare interface Directory extends FileOrDirectory {
  readonly isDirectory: true;
}

/** Type guard for Directory. */
export function isDirectory(
  fileOrDirectory: FileOrDirectory,
): fileOrDirectory is Directory {
  return fileOrDirectory.isDirectory;
}

/** Type guard for File. */
export function isFile(
  fileOrDirectory: FileOrDirectory,
): fileOrDirectory is File {
  return !fileOrDirectory.isDirectory;
}

/** A node in a tree containing directories and their subdirectories. */
export interface DirectoryNode extends Directory {
  readonly children?: readonly DirectoryNode[];
  readonly loading: boolean;
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
  readonly segments: readonly PathSpecSegment[];
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

/** Returns true if the file is a symlink. */
export function isSymlink(statEntry: StatEntry): boolean {
  const stMode = statEntry.stMode;
  if (stMode === undefined) {
    return false;
  }
  return (Number(stMode) & 0o120000) === 0o120000;
}


/** Content of a file. */
export declare interface FileContent {
  readonly totalLength: bigint;
  readonly textContent?: string;
  readonly blobContent?: ArrayBuffer;
}

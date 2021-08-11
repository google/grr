import {HexHash} from './flow';

/** ApiFile mapping. */
export declare interface File {
  readonly name?: string;
  readonly path?: string;
  readonly type?: string;
  readonly stat?: StatEntry;
  readonly isDirectory?: boolean;
  readonly hash?: HexHash;
  readonly lastCollected?: {
    timestamp: Date,
    size: bigint,
  };
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

/** Simple PathSpec mapping, ignoring PathTypes like REGISTRY for now. */
export declare interface PathSpec {
  readonly path?: string;
  readonly pathtype?: PathSpecPathType;
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

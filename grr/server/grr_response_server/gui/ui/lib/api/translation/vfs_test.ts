import {initTestEnvironment} from '../../../testing';
import {Directory, File, PathSpecPathType} from '../../models/vfs';
import {ApiFile, PathSpecOptions} from '../api_interfaces';

import {parseVfsPath, translateFile} from './vfs';

initTestEnvironment();

describe('translateFile', () => {
  it('converts all fields correctly', () => {
    const apiFile: ApiFile = {
      name: 'get_rich_quick.sh',
      path: 'fs/os/foo/bar/get_rich_quick.sh',
      age: '1627894679598719',
      isDirectory: false,
      hash: {
        sha256: 'qfrybrx0NlyN8t1tsLqPM4qisznalWfwHQ5JxpdhOOE=',
        sha1: 'jaaW7R8eBUpBBG2jqvXh+92tRLo=',
        md5: 'YEEyZobfEYMwOTf86uSW6Q==',
        numBytes: '14',
      },
      type: 'FILE',
      lastCollected: '1627313231428831',
      lastCollectedSize: '14',
      stat: {
        stMode: '33261',
        stIno: '14157337',
        stDev: '65025',
        stNlink: '1',
        stUid: 610129,
        stGid: 89939,
        stSize: '14',
        stAtime: '1627312917',
        stMtime: '1580294217',
        stCtime: '1580294236',
        stBtime: '1580294240',
        stBlocks: '8',
        stBlksize: '4096',
        stRdev: '0',
        symlink: 'symlink',
        pathspec: {
          pathtype: 'OS' as PathSpecPathType,
          path: '/foo/bar/get_rich_quick.sh',
          pathOptions: 'CASE_LITERAL' as PathSpecOptions,
        },
        stFlagsOsx: 0,
        stFlagsLinux: 524288,
      },
    };
    const file: File = {
      name: 'get_rich_quick.sh',
      path: '/foo/bar/get_rich_quick.sh',
      isDirectory: false,
      pathtype: PathSpecPathType.OS,
      hash: {
        sha256:
          'a9faf26ebc74365c8df2dd6db0ba8f338aa2b339da9567f01d0e49c6976138e1',
        sha1: '8da696ed1f1e054a41046da3aaf5e1fbddad44ba',
        md5: '6041326686df1183303937fceae496e9',
      },
      lastMetadataCollected: new Date(1627894679598),
      lastContentCollected: {
        timestamp: new Date(1627313231428),
        size: BigInt(14),
      },
      stat: {
        stMode: BigInt(33261),
        stIno: BigInt(14157337),
        stDev: BigInt(65025),
        stNlink: BigInt(1),
        stUid: 610129,
        stGid: 89939,
        stSize: BigInt(14),
        stAtime: new Date(1627312917000),
        stBtime: new Date(1580294240000),
        stMtime: new Date(1580294217000),
        stCtime: new Date(1580294236000),
        stBlocks: BigInt(8),
        stBlksize: BigInt(4096),
        stRdev: BigInt(0),
        pathspec: {
          pathtype: PathSpecPathType.OS,
          path: '/foo/bar/get_rich_quick.sh',
          segments: [
            {
              pathtype: PathSpecPathType.OS,
              path: '/foo/bar/get_rich_quick.sh',
            },
          ],
        },
        stFlagsOsx: 0,
        stFlagsLinux: 524288,
        symlink: 'symlink',
      },
      type: 'FILE',
    };
    expect(translateFile(apiFile)).toEqual(file);
  });

  it('converts optional fields correctly', () => {
    const apiFile: ApiFile = {
      isDirectory: false,
      name: 'get_rich_quick.sh',
      path: 'fs/os/foo/bar/get_rich_quick.sh',
      age: '123000',
      stat: {
        pathspec: {
          pathtype: 'OS' as PathSpecPathType,
          path: '/foo/bar/get_rich_quick.sh',
        },
      },
    };
    const file: File = {
      isDirectory: false,
      name: 'get_rich_quick.sh',
      path: '/foo/bar/get_rich_quick.sh',
      pathtype: PathSpecPathType.OS,
      lastMetadataCollected: new Date(123),
      lastContentCollected: undefined,
      type: undefined,
      hash: undefined,
      stat: {
        stMode: undefined,
        stIno: undefined,
        stDev: undefined,
        stNlink: undefined,
        stUid: undefined,
        stGid: undefined,
        stSize: undefined,
        stAtime: undefined,
        stMtime: undefined,
        stCtime: undefined,
        stBtime: undefined,
        stBlocks: undefined,
        stBlksize: undefined,
        stRdev: undefined,
        stFlagsOsx: undefined,
        stFlagsLinux: undefined,
        symlink: undefined,
        pathspec: {
          pathtype: PathSpecPathType.OS,
          path: '/foo/bar/get_rich_quick.sh',
          segments: [
            {
              pathtype: PathSpecPathType.OS,
              path: '/foo/bar/get_rich_quick.sh',
            },
          ],
        },
      },
    };
    expect(translateFile(apiFile)).toEqual(file);
  });

  it('converts nested pathspecs correctly', () => {
    const apiFile: ApiFile = {
      isDirectory: false,
      name: 'get_rich_quick.sh',
      path: 'fs/ntfs/foo/bar/get_rich_quick.sh',
      age: '123000',
      stat: {
        pathspec: {
          pathtype: 'OS' as PathSpecPathType,
          path: '/foo/bar',
          nestedPath: {
            pathtype: 'NTFS' as PathSpecPathType,
            path: '/get_rich_quick.sh',
          },
        },
      },
    };
    const file: File = {
      isDirectory: false,
      name: 'get_rich_quick.sh',
      path: '/foo/bar/get_rich_quick.sh',
      pathtype: PathSpecPathType.NTFS,
      stat: {
        stMode: undefined,
        stIno: undefined,
        stDev: undefined,
        stNlink: undefined,
        stUid: undefined,
        stGid: undefined,
        stSize: undefined,
        stAtime: undefined,
        stMtime: undefined,
        stCtime: undefined,
        stBtime: undefined,
        stBlocks: undefined,
        stBlksize: undefined,
        stRdev: undefined,
        stFlagsOsx: undefined,
        stFlagsLinux: undefined,
        symlink: undefined,
        pathspec: {
          pathtype: PathSpecPathType.NTFS,
          path: '/foo/bar/get_rich_quick.sh',
          segments: [
            {
              pathtype: PathSpecPathType.OS,
              path: '/foo/bar',
            },
            {
              pathtype: PathSpecPathType.NTFS,
              path: '/get_rich_quick.sh',
            },
          ],
        },
      },
    };
    expect(translateFile(apiFile)).toEqual(jasmine.objectContaining(file));
  });

  it('converts directories correctly', () => {
    const apiFile: ApiFile = {
      isDirectory: true,
      name: 'get_rich_quick',
      path: 'fs/os/foo/bar/get_rich_quick',
      stat: {
        pathspec: {
          pathtype: 'OS' as PathSpecPathType,
          path: '/foo/bar/get_rich_quick',
        },
      },
      age: '123000',
    };
    const dir: Directory = {
      isDirectory: true,
      name: 'get_rich_quick',
      path: '/foo/bar/get_rich_quick',
      pathtype: PathSpecPathType.OS,
      lastMetadataCollected: new Date(123),
      stat: {
        stMode: undefined,
        stIno: undefined,
        stDev: undefined,
        stNlink: undefined,
        stUid: undefined,
        stGid: undefined,
        stSize: undefined,
        stAtime: undefined,
        stMtime: undefined,
        stCtime: undefined,
        stBtime: undefined,
        stBlocks: undefined,
        stBlksize: undefined,
        stRdev: undefined,
        stFlagsOsx: undefined,
        stFlagsLinux: undefined,
        symlink: undefined,
        pathspec: {
          pathtype: PathSpecPathType.OS,
          path: '/foo/bar/get_rich_quick',
          segments: [
            {
              pathtype: PathSpecPathType.OS,
              path: '/foo/bar/get_rich_quick',
            },
          ],
        },
      },
    };
    expect(translateFile(apiFile)).toEqual(dir);
  });
});

describe('parseVfsPath', () => {
  it('converts OS paths correctly', () => {
    expect(parseVfsPath('fs/os/foo/bar')).toEqual({
      pathtype: PathSpecPathType.OS,
      path: '/foo/bar',
    });
  });

  it('converts the root path correctly', () => {
    expect(parseVfsPath('fs/os/')).toEqual({
      pathtype: PathSpecPathType.OS,
      path: '/',
    });
  });
});

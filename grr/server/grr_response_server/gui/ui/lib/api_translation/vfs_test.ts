import {initTestEnvironment, removeUndefinedKeys} from '../../testing';
import {ApiFile, PathSpecOptions, PathSpecPathType} from '../api/api_interfaces';
import {File} from '../models/vfs';

import {translateFile} from './vfs';


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
        numBytes: '14'
      },
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
        stBlocks: '8',
        stBlksize: '4096',
        stRdev: '0',
        pathspec: {
          pathtype: 'OS' as PathSpecPathType,
          path: '/foo/bar/get_rich_quick.sh',
          pathOptions: 'CASE_LITERAL' as PathSpecOptions,
        },
        stFlagsOsx: 0,
        stFlagsLinux: 524288,
      }
    };
    const file: File = {
      name: 'get_rich_quick.sh',
      path: 'fs/os/foo/bar/get_rich_quick.sh',
      isDirectory: false,
      hash: {
        sha256:
            'a9faf26ebc74365c8df2dd6db0ba8f338aa2b339da9567f01d0e49c6976138e1',
        sha1: '8da696ed1f1e054a41046da3aaf5e1fbddad44ba',
        md5: '6041326686df1183303937fceae496e9',
      },
      lastCollected: {
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
        stMtime: new Date(1580294217000),
        stCtime: new Date(1580294236000),
        stBlocks: BigInt(8),
        stBlksize: BigInt(4096),
        stRdev: BigInt(0),
        pathspec: {
          pathtype: PathSpecPathType.OS,
          path: '/foo/bar/get_rich_quick.sh',
        },
        stFlagsOsx: 0,
        stFlagsLinux: 524288
      }
    };
    expect(removeUndefinedKeys(translateFile(apiFile))).toEqual(file);
  });

  it('converts optional fields correctly', () => {
    const apiFile: ApiFile = {
      stat: {
        pathspec: {
          pathtype: 'OS' as PathSpecPathType,
          path: '/foo/bar/get_rich_quick.sh',
        }
      }
    };
    const file: File = {
      stat: {
        pathspec: {
          pathtype: PathSpecPathType.OS,
          path: '/foo/bar/get_rich_quick.sh',
        },
      }
    };
    expect(removeUndefinedKeys(translateFile(apiFile))).toEqual(file);
  });
});

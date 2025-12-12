import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {newDirectory, newFile} from '../../../../../lib/models/model_test_util';
import {Directory, File, PathSpecPathType} from '../../../../../lib/models/vfs';
import {initTestEnvironment} from '../../../../../testing';
import {StatView} from './stat_view';
import {StatViewHarness} from './testing/stat_view_harness';

initTestEnvironment();

async function createComponent(path: File | Directory | undefined) {
  const fixture = TestBed.createComponent(StatView);
  fixture.componentRef.setInput('path', path);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    StatViewHarness,
  );

  return {fixture, harness};
}

describe('Stat View Component', () => {
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      imports: [StatView, NoopAnimationsModule],
      teardown: {destroyAfterEach: true},
    }).compileComponents();
  }));

  it('is created', fakeAsync(async () => {
    const {fixture} = await createComponent(undefined);

    expect(fixture.componentInstance).toBeDefined();
  }));

  it('shows complete details, stats and hashes for a file', fakeAsync(async () => {
    const {harness} = await createComponent(
      newFile({
        name: 'examplefile',
        isDirectory: false,
        path: 'fs/os/examplefile',
        pathtype: PathSpecPathType.OS,
        lastMetadataCollected: new Date(1),
        lastContentCollected: {
          timestamp: new Date(1234567890),
          size: BigInt(1000000),
        },
        hash: {
          sha256: '123abc',
        },
        stat: {
          stDev: BigInt(1),
          stIno: BigInt(2),
          stMode: BigInt(3),
          stNlink: BigInt(4),
          stUid: 5,
          stGid: 6,
          stRdev: BigInt(7),
          stSize: BigInt(8),
          stBlksize: BigInt(9),
          stBlocks: BigInt(10),
          stAtime: new Date(11000000),
          stMtime: new Date(12000000),
          stCtime: new Date(13000000),
          pathspec: {
            path: '/examplefile',
            pathtype: PathSpecPathType.OS,
            segments: [
              {
                path: '/examplefile',
                pathtype: PathSpecPathType.OS,
              },
            ],
          },
        },
      }),
    );

    const detailsTable = await harness.detailsTable();
    expect(detailsTable).toBeDefined();
    expect(await detailsTable!.text()).toContain('Is directory:');
    expect(await detailsTable!.text()).toContain('No');
    expect(await detailsTable!.text()).toContain('Path:');
    expect(await detailsTable!.text()).toContain('OS');
    expect(await detailsTable!.text()).toContain('/examplefile');
    expect(await detailsTable!.text()).toContain('Content collected:');
    expect(await detailsTable!.text()).toContain('1970-01-15 06:56:07 UTC');
    expect(await detailsTable!.text()).toContain('Size:');
    expect(await detailsTable!.text()).toContain('976.56 KiB');

    const statTable = await harness.statTable();
    expect(statTable).toBeDefined();
    expect(await statTable.text()).toContain('st_dev');
    expect(await statTable.text()).toContain('1');
    expect(await statTable.text()).toContain('st_ino');
    expect(await statTable.text()).toContain('2');
    expect(await statTable.text()).toContain('st_mode');
    expect(await statTable.text()).toContain('3');
    expect(await statTable.text()).toContain('st_nlink');
    expect(await statTable.text()).toContain('4');
    expect(await statTable.text()).toContain('st_uid');
    expect(await statTable.text()).toContain('5');
    expect(await statTable.text()).toContain('st_gid');
    expect(await statTable.text()).toContain('6');
    expect(await statTable.text()).toContain('st_rdev');
    expect(await statTable.text()).toContain('7');
    expect(await statTable.text()).toContain('st_size');
    expect(await statTable.text()).toContain('8');
    expect(await statTable.text()).toContain('st_blksize');
    expect(await statTable.text()).toContain('9');
    expect(await statTable.text()).toContain('st_blocks');
    expect(await statTable.text()).toContain('10');
    expect(await statTable.text()).toContain('st_atime');
    expect(await statTable.text()).toContain('1970-01-01 03:03:20 UTC');
    expect(await statTable.text()).toContain('st_mtime');
    expect(await statTable.text()).toContain('1970-01-01 03:20:00 UTC');
    expect(await statTable.text()).toContain('st_ctime');
    expect(await statTable.text()).toContain('1970-01-01 03:36:40 UTC');

    const hashesTable = await harness.hashesTable();
    expect(hashesTable).not.toBeNull();
    expect(await hashesTable!.text()).toContain('SHA-256');
    expect(await hashesTable!.text()).toContain('123abc');
  }));

  it('shows complete details, stats and hashes for a directory', fakeAsync(async () => {
    const {harness} = await createComponent(
      newDirectory({
        name: 'examplefile',
        isDirectory: true,
        path: 'fs/os/examplefile',
        pathtype: PathSpecPathType.OS,
        lastMetadataCollected: new Date(1),
        stat: {
          stDev: BigInt(1),
          stIno: BigInt(2),
          stMode: BigInt(3),
          stNlink: BigInt(4),
          stUid: 5,
          stGid: 6,
          stRdev: BigInt(7),
          stSize: BigInt(8),
          stBlksize: BigInt(9),
          stBlocks: BigInt(10),
          stAtime: new Date(11000000),
          stMtime: new Date(12000000),
          stCtime: new Date(13000000),
          pathspec: {
            path: '/examplefile',
            pathtype: PathSpecPathType.OS,
            segments: [
              {
                path: '/examplefile',
                pathtype: PathSpecPathType.OS,
              },
            ],
          },
        },
      }),
    );

    const detailsTable = await harness.detailsTable();
    expect(detailsTable).toBeDefined();
    expect(await detailsTable!.text()).toContain('Is directory:');
    expect(await detailsTable!.text()).toContain('Yes');
    expect(await detailsTable!.text()).toContain('Path:');
    expect(await detailsTable!.text()).toContain('OS');
    expect(await detailsTable!.text()).toContain('/examplefile');

    const statTable = await harness.statTable();
    expect(statTable).toBeDefined();
    expect(await statTable.text()).toContain('st_dev');
    expect(await statTable.text()).toContain('1');
    expect(await statTable.text()).toContain('st_ino');
    expect(await statTable.text()).toContain('2');
    expect(await statTable.text()).toContain('st_mode');
    expect(await statTable.text()).toContain('3');
    expect(await statTable.text()).toContain('st_nlink');
    expect(await statTable.text()).toContain('4');
    expect(await statTable.text()).toContain('st_uid');
    expect(await statTable.text()).toContain('5');
    expect(await statTable.text()).toContain('st_gid');
    expect(await statTable.text()).toContain('6');
    expect(await statTable.text()).toContain('st_rdev');
    expect(await statTable.text()).toContain('7');
    expect(await statTable.text()).toContain('st_size');
    expect(await statTable.text()).toContain('8');
    expect(await statTable.text()).toContain('st_blksize');
    expect(await statTable.text()).toContain('9');
    expect(await statTable.text()).toContain('st_blocks');
    expect(await statTable.text()).toContain('10');
    expect(await statTable.text()).toContain('st_atime');
    expect(await statTable.text()).toContain('1970-01-01 03:03:20 UTC');
    expect(await statTable.text()).toContain('st_mtime');
    expect(await statTable.text()).toContain('1970-01-01 03:20:00 UTC');
    expect(await statTable.text()).toContain('st_ctime');
    expect(await statTable.text()).toContain('1970-01-01 03:36:40 UTC');

    const hashesTable = await harness.hashesTable();
    expect(hashesTable).toBeNull();
  }));

  it('shows nested pathspecs', fakeAsync(async () => {
    const {harness} = await createComponent(
      newFile({
        name: 'examplefile',
        isDirectory: false,
        path:
          'fs/ntfs/\\\\?\\Volume{17eaa822-d734-498d-b0e7-954c51ffae41}' +
          '/examplefile',
        pathtype: PathSpecPathType.OS,
        lastMetadataCollected: new Date(1),
        stat: {
          pathspec: {
            path: '/\\\\?\\Volume{17eaa822-d734-498d-b0e7-954c51ffae41}/examplefile',
            pathtype: PathSpecPathType.NTFS,
            segments: [
              {
                path: '/\\\\?\\Volume{17eaa822-d734-498d-b0e7-954c51ffae41}',
                pathtype: PathSpecPathType.OS,
              },
              {
                path: '/examplefile',
                pathtype: PathSpecPathType.NTFS,
              },
            ],
          },
        },
      }),
    );

    const detailsTable = await harness.detailsTable();
    expect(detailsTable).toBeDefined();
    expect(await detailsTable!.text()).toContain('Path:');
    expect(await detailsTable!.text()).toContain('OS');
    expect(await detailsTable!.text()).toContain(
      '/\\\\?\\Volume{17eaa822-d734-498d-b0e7-954c51ffae41}',
    );
    expect(await detailsTable!.text()).toContain('NTFS');
    expect(await detailsTable!.text()).toContain('/examplefile');
  }));
});

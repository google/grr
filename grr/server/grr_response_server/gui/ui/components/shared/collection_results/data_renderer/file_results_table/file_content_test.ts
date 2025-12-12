

import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';

import {
  newDirectory,
  newFile,
  newPathSpec,
  newStatEntry,
} from '../../../../../lib/models/model_test_util';
import {PathSpecPathType} from '../../../../../lib/models/vfs';
import {FileStore} from '../../../../../store/file_store';
import {
  FileStoreMock,
  newFileStoreMock,
} from '../../../../../store/store_test_util';
import {initTestEnvironment} from '../../../../../testing';
import {FileContent} from './file_content';
import {FlowFileResult} from './file_results_table';
import {FileContentHarness} from './testing/file_content_harness';

initTestEnvironment();

async function createComponent(file: FlowFileResult | null) {
  const fixture = TestBed.createComponent(FileContent);
  fixture.componentRef.setInput('file', file);

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    FileContentHarness,
  );
  return {fixture, harness};
}

describe('File Content Component', () => {
  let fileStoreMock: FileStoreMock;

  beforeEach(waitForAsync(() => {
    fileStoreMock = newFileStoreMock();

    TestBed.configureTestingModule({
      imports: [FileContent, NoopAnimationsModule],
      teardown: {destroyAfterEach: true},
    })
      .overrideComponent(FileContent, {
        set: {
          providers: [{provide: FileStore, useValue: fileStoreMock}],
        },
      })
      .compileComponents();
  }));

  it('is created', async () => {
    const {fixture} = await createComponent(null);

    expect(fixture.componentInstance).toBeDefined();
  });

  it('renders recollect button if path is a file', fakeAsync(async () => {
    fileStoreMock.fileDetailsMap = signal(
      new Map([
        [
          'C.1234567890',
          new Map([
            [PathSpecPathType.OS, new Map([['/foo/bar/0', newFile({})]])],
          ]),
        ],
      ]),
    );
    const {harness} = await createComponent({
      statEntry: newStatEntry({
        pathspec: newPathSpec({
          path: '/foo/bar/0',
          pathtype: PathSpecPathType.OS,
        }),
      }),
      clientId: 'C.1234567890',
    });

    const recollectButton = await harness.recollectButton();
    expect(recollectButton).not.toBeNull();
  }));

  it('does not render recollect button if path is a directory', fakeAsync(async () => {
    fileStoreMock.fileDetailsMap = signal(
      new Map([
        [
          'C.1234567890',
          new Map([
            [PathSpecPathType.OS, new Map([['/foo/bar', newDirectory({})]])],
          ]),
        ],
      ]),
    );
    const {harness} = await createComponent({
      statEntry: newStatEntry({
        pathspec: newPathSpec({
          path: '/foo/bar',
          pathtype: PathSpecPathType.OS,
        }),
      }),
      clientId: 'C.1234567890',
    });

    const recollectButton = await harness.recollectButton();
    expect(recollectButton).toBeNull();
  }));

  it('hides recollect button if file is null', fakeAsync(async () => {
    const {harness} = await createComponent(null);

    const recollectButton = await harness.recollectButton();
    expect(recollectButton).toBeNull();
  }));

  it('enables recollect button if file is not being recollected', fakeAsync(async () => {
    fileStoreMock.fileDetailsMap = signal(
      new Map([
        [
          'C.1234567890',
          new Map([
            [PathSpecPathType.OS, new Map([['/foo/bar', newFile({})]])],
          ]),
        ],
      ]),
    );
    fileStoreMock.isRecollecting = signal(false);
    const {harness} = await createComponent({
      statEntry: newStatEntry({
        pathspec: newPathSpec({
          path: '/foo/bar',
          pathtype: PathSpecPathType.OS,
        }),
      }),
      clientId: 'C.1234567890',
    });

    const recollectButton = await harness.recollectButton();
    expect(recollectButton).not.toBeNull();
    expect(await recollectButton!.isDisabled()).toBeFalse();
    expect(await harness.getRecollectButtonIcon()).toBe('refresh');
  }));

  it('shows spinner and disables button if file is being recollected', fakeAsync(async () => {
    fileStoreMock.fileDetailsMap = signal(
      new Map([
        [
          'C.1234567890',
          new Map([
            [PathSpecPathType.OS, new Map([['/foo/bar', newFile({})]])],
          ]),
        ],
      ]),
    );
    fileStoreMock.isRecollecting = signal(true);
    const {harness} = await createComponent({
      statEntry: newStatEntry({
        pathspec: newPathSpec({
          path: '/foo/bar',
          pathtype: PathSpecPathType.OS,
        }),
      }),
      clientId: 'C.1234567890',
    });

    expect(await harness.hasRecollectButtonSpinner()).toBeTrue();
  }));

  it('clicking recollect button calls file store', fakeAsync(async () => {
    fileStoreMock.fileDetailsMap = signal(
      new Map([
        [
          'C.1234567890',
          new Map([
            [PathSpecPathType.OS, new Map([['/foo/bar', newFile({})]])],
          ]),
        ],
      ]),
    );
    const {harness} = await createComponent({
      statEntry: newStatEntry({
        pathspec: {
          pathtype: PathSpecPathType.OS,
          path: '/foo/bar',
          segments: [{pathtype: PathSpecPathType.OS, path: '/foo/bar'}],
        },
      }),
      clientId: 'C.1234567890',
    });

    const recollectButton = await harness.recollectButton();
    expect(recollectButton).not.toBeNull();
    await recollectButton!.click();

    expect(fileStoreMock.recollectFile).toHaveBeenCalledWith({
      clientId: 'C.1234567890',
      pathType: PathSpecPathType.OS,
      path: '/foo/bar',
    });
  }));

  it('renders download button', fakeAsync(async () => {
    const {harness} = await createComponent({
      statEntry: newStatEntry({}),
      clientId: 'C.1234567890',
    });

    const downloadButton = await harness.downloadButton();
    expect(downloadButton).toBeDefined();
  }));

  it('disables download button if no download url is available', fakeAsync(async () => {
    const {harness} = await createComponent(null);

    const downloadButton = await harness.downloadButton();
    expect(await downloadButton.isDisabled()).toBeTrue();
  }));

  it('disables download button if no hex content is available', fakeAsync(async () => {
    fileStoreMock.fileBlobMap = signal(
      new Map([
        ['C.1234567890', new Map([[PathSpecPathType.OS, new Map([])]])],
      ]),
    );
    const {harness} = await createComponent({
      statEntry: newStatEntry({
        pathspec: newPathSpec({
          path: '/foo/bar',
          pathtype: PathSpecPathType.OS,
        }),
      }),
      clientId: 'C.1234567890',
    });

    const downloadButton = await harness.downloadButton();
    expect(await downloadButton.isDisabled()).toBeTrue();
  }));

  it('enables download button if download url and hex content is available', fakeAsync(async () => {
    fileStoreMock.fileBlobMap = signal(
      new Map([
        [
          'C.1234567890',
          new Map([
            [
              PathSpecPathType.OS,
              new Map([
                [
                  '/foo/bar',
                  {
                    totalLength: BigInt(5),
                    blobContent: new Uint8Array([1, 2, 3, 4, 5]).buffer,
                  },
                ],
              ]),
            ],
          ]),
        ],
      ]),
    );
    const {harness} = await createComponent({
      statEntry: newStatEntry({
        pathspec: newPathSpec({
          path: '/foo/bar',
          pathtype: PathSpecPathType.OS,
        }),
      }),
      clientId: 'C.1234567890',
    });

    const downloadButton = await harness.downloadButton();
    expect(await downloadButton.isDisabled()).toBeFalse();
  }));

  it('renders loading information if file/directory is not available yet', fakeAsync(async () => {
    fileStoreMock.fileDetailsMap = signal(
      new Map([
        [
          'C.1234567890',
          new Map([[PathSpecPathType.OS, new Map(/* empty */)]]),
        ],
      ]),
    );
    const {harness} = await createComponent({
      statEntry: newStatEntry({
        pathspec: newPathSpec({
          path: '/foo/bar/0',
          pathtype: PathSpecPathType.OS,
        }),
      }),
      clientId: 'C.1234567890',
    });

    expect(await harness.hasIsLoadingMessage()).toBeTrue();
  }));

  it('renders no access message if file/directory is not accessible', fakeAsync(async () => {
    fileStoreMock.fileContentAccessMap = signal(
      new Map([
        [
          'C.1234567890',
          new Map([[PathSpecPathType.OS, new Map([['/foo/bar/0', false]])]]),
        ],
      ]),
    );
    const {harness} = await createComponent({
      statEntry: newStatEntry({
        pathspec: newPathSpec({
          path: '/foo/bar/0',
          pathtype: PathSpecPathType.OS,
        }),
      }),
      clientId: 'C.1234567890',
    });

    expect(await harness.hasNoAccessMessage()).toBeTrue();
  }));

  it('renders stats tab and passes data to stat view if path is a file', fakeAsync(async () => {
    fileStoreMock.fileDetailsMap = signal(
      new Map([
        [
          'C.1234567890',
          new Map([
            [PathSpecPathType.OS, new Map([['/foo/bar/0', newFile({})]])],
          ]),
        ],
      ]),
    );

    const {harness} = await createComponent({
      statEntry: newStatEntry({
        pathspec: newPathSpec({
          path: '/foo/bar/0',
          pathtype: PathSpecPathType.OS,
        }),
      }),
      clientId: 'C.1234567890',
    });

    const statsTab = await harness.getTab('File Stat');
    await statsTab.select();

    const statView = await harness.statView();
    expect(statView).toBeDefined();
    const detailsTable = await statView!.detailsTable();
    expect(await detailsTable.text()).toContain('/foo/bar');
  }));

  it('renders stats tab and passes data to stat view if path is a directory', fakeAsync(async () => {
    fileStoreMock.fileDetailsMap = signal(
      new Map([
        [
          'C.1234567890',
          new Map([
            [
              PathSpecPathType.OS,
              new Map([
                [
                  '/foo/bar',
                  newDirectory({
                    stat: {
                      pathspec: newPathSpec({
                        path: '/foo/bar',
                        pathtype: PathSpecPathType.OS,
                      }),
                    },
                  }),
                ],
              ]),
            ],
          ]),
        ],
      ]),
    );

    const {harness} = await createComponent({
      statEntry: newStatEntry({
        pathspec: newPathSpec({
          path: '/foo/bar',
          pathtype: PathSpecPathType.OS,
        }),
      }),
      clientId: 'C.1234567890',
    });

    const statsTab = await harness.getTab('File Stat');
    await statsTab.select();

    const statView = await harness.statView();
    expect(statView).toBeDefined();
    const detailsTable = await statView!.detailsTable();
    expect(await detailsTable.text()).toContain('/foo/bar');
  }));

  it('renders text tab and passes data to stat view', fakeAsync(async () => {
    fileStoreMock.fileTextMap = signal(
      new Map([
        [
          'C.1234567890',
          new Map([
            [
              PathSpecPathType.OS,
              new Map([
                [
                  '/foo/bar/0',
                  {
                    totalLength: BigInt(7),
                    textContent: 'foo bar',
                  },
                ],
              ]),
            ],
          ]),
        ],
      ]),
    );
    const {harness} = await createComponent({
      statEntry: newStatEntry({
        pathspec: newPathSpec({
          path: '/foo/bar/0',
          pathtype: PathSpecPathType.OS,
        }),
      }),
      clientId: 'C.1234567890',
    });

    const textTab = await harness.getTab('Text Content');
    await textTab.select();

    const textView = await harness.textView();
    expect(textView).toBeDefined();
    const codeblock = await textView!.codeblock();
    expect(await codeblock.linesText()).toEqual(['foo bar']);
  }));

  it('disables text tab if no data is available', fakeAsync(async () => {
    const {harness} = await createComponent({
      statEntry: newStatEntry({
        pathspec: newPathSpec({
          path: '/foo/bar/0',
          pathtype: PathSpecPathType.OS,
        }),
      }),
      clientId: 'C.1234567890',
    });

    const textTab = await harness.getTab('Text Content');

    expect(await textTab.isDisabled()).toBeTrue();
  }));

  it('renders hex tab and passes data to stat view', fakeAsync(async () => {
    fileStoreMock.fileBlobMap = signal(
      new Map([
        [
          'C.1234567890',
          new Map([
            [
              PathSpecPathType.OS,
              new Map([
                [
                  '/foo/bar/0',
                  {
                    totalLength: BigInt(1000000),
                    blobContent: new Uint8Array([1, 2, 3, 4, 5]).buffer,
                  },
                ],
              ]),
            ],
          ]),
        ],
      ]),
    );
    const {harness} = await createComponent({
      statEntry: newStatEntry({
        pathspec: newPathSpec({
          path: '/foo/bar/0',
          pathtype: PathSpecPathType.OS,
        }),
      }),
      clientId: 'C.1234567890',
    });

    const hexTab = await harness.getTab('Binary Content');
    await hexTab.select();

    const hexView = await harness.hexView();
    expect(hexView).toBeDefined();
    const hexTable = await hexView!.hexTable();
    expect(await hexTable.text()).toContain('0102030405');
  }));

  it('disables hex tab if no data is available', fakeAsync(async () => {
    const {harness} = await createComponent({
      statEntry: newStatEntry({
        pathspec: newPathSpec({
          path: '/foo/bar/0',
          pathtype: PathSpecPathType.OS,
        }),
      }),
      clientId: 'C.1234567890',
    });

    const hexTab = await harness.getTab('Binary Content');

    expect(await hexTab.isDisabled()).toBeTrue();
  }));

  it('renders load more button for text content if there is more data available', fakeAsync(async () => {
    fileStoreMock.fileTextMap = signal(
      new Map([
        [
          'C.1234567890',
          new Map([
            [
              PathSpecPathType.OS,
              new Map([
                [
                  '/foo/bar/0',
                  {
                    totalLength: BigInt(100),
                    textContent: 'foo bar',
                  },
                ],
              ]),
            ],
          ]),
        ],
      ]),
    );
    const {harness} = await createComponent({
      statEntry: newStatEntry({
        pathspec: newPathSpec({
          path: '/foo/bar/0',
          pathtype: PathSpecPathType.OS,
        }),
      }),
      clientId: 'C.1234567890',
    });

    const textTab = await harness.getTab('Text Content');
    await textTab.select();

    const loadMoreButton = await harness.loadMoreTextButton();
    expect(loadMoreButton).toBeDefined();
    expect(await loadMoreButton!.isDisabled()).toBeFalse();
  }));

  it('renders load more button for hex content if there is more data available', fakeAsync(async () => {
    fileStoreMock.fileBlobMap = signal(
      new Map([
        [
          'C.1234567890',
          new Map([
            [
              PathSpecPathType.OS,
              new Map([
                [
                  '/foo/bar/0',
                  {
                    totalLength: BigInt(100),
                    blobContent: new Uint8Array([1, 2, 3, 4, 5]).buffer,
                  },
                ],
              ]),
            ],
          ]),
        ],
      ]),
    );
    const {harness} = await createComponent({
      statEntry: newStatEntry({
        pathspec: newPathSpec({
          path: '/foo/bar/0',
          pathtype: PathSpecPathType.OS,
        }),
      }),
      clientId: 'C.1234567890',
    });

    const hexTab = await harness.getTab('Binary Content');
    await hexTab.select();

    const loadMoreButton = await harness.loadMoreHexButton();
    expect(loadMoreButton).toBeDefined();
    expect(await loadMoreButton!.isDisabled()).toBeFalse();
  }));
});

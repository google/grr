import {TestbedHarnessEnvironment} from '@angular/cdk/testing/testbed';
import {signal} from '@angular/core';
import {fakeAsync, TestBed, waitForAsync} from '@angular/core/testing';
import {NoopAnimationsModule} from '@angular/platform-browser/animations';
import {RouterModule} from '@angular/router';
import {RouterTestingHarness} from '@angular/router/testing';

import {HttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_service';
import {mockHttpApiWithTranslationService} from '../../../lib/api/http_api_with_translation_test_util';
import {
  newDirectory,
  newFile,
  newStatEntry,
} from '../../../lib/models/model_test_util';
import {PathSpecPathType} from '../../../lib/models/vfs';
import {FileExplorerStore} from '../../../store/file_explorer_store';
import {FileStore} from '../../../store/file_store';
import {
  FileExplorerStoreMock,
  FileStoreMock,
  newFileExplorerStoreMock,
  newFileStoreMock,
} from '../../../store/store_test_util';
import {initTestEnvironment} from '../../../testing';
import {CLIENT_ROUTES} from '../../app/routing';
import {FileContent} from '../../shared/collection_results/data_renderer/file_results_table/file_content';
import {FileExplorer} from './file_explorer';
import {FileExplorerHarness} from './testing/file_explorer_harness';

initTestEnvironment();

async function createComponent(clientId?: string) {
  const fixture = TestBed.createComponent(FileExplorer);
  if (clientId) {
    fixture.componentRef.setInput('clientId', clientId);
  }

  fixture.detectChanges();
  const harness = await TestbedHarnessEnvironment.harnessForFixture(
    fixture,
    FileExplorerHarness,
  );

  return {fixture, harness};
}

describe('File Explorer', () => {
  let fileExplorerStoreMock: FileExplorerStoreMock;
  let fileStoreMock: FileStoreMock;

  beforeEach(waitForAsync(() => {
    fileExplorerStoreMock = newFileExplorerStoreMock();
    fileStoreMock = newFileStoreMock();

    TestBed.configureTestingModule({
      imports: [
        FileExplorer,
        NoopAnimationsModule,
        RouterModule.forRoot(CLIENT_ROUTES, {
          bindToComponentInputs: true,
          paramsInheritanceStrategy: 'always',
        }),
      ],
      providers: [
        {
          provide: HttpApiWithTranslationService,
          useValue: mockHttpApiWithTranslationService(),
        },
      ],
    })
      .overrideComponent(FileExplorer, {
        set: {
          providers: [
            {
              provide: FileExplorerStore,
              useValue: fileExplorerStoreMock,
            },
          ],
        },
      })
      .overrideComponent(FileContent, {
        set: {
          providers: [
            {
              provide: FileStore,
              useValue: fileStoreMock,
            },
          ],
        },
      })
      .compileComponents();
  }));

  it('is created', async () => {
    const {fixture} = await createComponent();

    expect(fixture.componentInstance).toBeTruthy();
    expect(fixture.componentInstance).toBeInstanceOf(FileExplorer);
  });

  it('initializes the store with the root path if no path is provided', async () => {
    const routerTestingHarness = await RouterTestingHarness.create();
    await routerTestingHarness.navigateByUrl(
      '/clients/C.1234567890123456/files',
    );

    expect(fileExplorerStoreMock.initialize).toHaveBeenCalledWith(
      'C.1234567890123456',
      '/',
    );
  });

  it('initializes the store with the path from the query params', async () => {
    const routerTestingHarness = await RouterTestingHarness.create();
    await routerTestingHarness.navigateByUrl(
      '/clients/C.1234567890123456/files?path=%2FtestPath',
    );

    expect(fileExplorerStoreMock.initialize).toHaveBeenCalledWith(
      'C.1234567890123456',
      '/testPath',
    );
  });

  it('shows children of a folder when expanded', async () => {
    fileExplorerStoreMock.fileSystemTree = signal({
      file: newDirectory({
        name: '',
        path: '/',
      }),
      children: [
        {
          file: newDirectory({
            name: 'nested_1_1',
            path: '/nested_1_1',
          }),
          children: [
            {
              file: newFile({
                name: 'nested_2_1',
                path: '/nested_1_1/nested_2_1',
              }),
              children: undefined,
            },
          ],
        },
        {
          file: newDirectory({
            name: 'nested_1_2',
            path: '/nested_1_2',
          }),
          children: undefined,
        },
      ],
    });
    const {harness} = await createComponent();

    const rootFolderNames = await harness.getFolderNames(0);
    expect(rootFolderNames.length).toBe(1);
    expect(rootFolderNames[0]).toContain('/');
    const nestedFolderNames = await harness.getFolderNames(1);
    expect(nestedFolderNames.length).toBe(2);
    expect(nestedFolderNames[0]).toContain('/nested_1_1');
    expect(nestedFolderNames[1]).toContain('/nested_1_2');
    const nestedNestedFolderNames = await harness.getFolderNames(2);
    expect(nestedNestedFolderNames.length).toBe(1);
    expect(nestedNestedFolderNames[0]).toContain('/nested_2_1');
  });

  it('shows folder icon for folders', async () => {
    fileExplorerStoreMock.fileSystemTree = signal({
      file: newDirectory({
        name: 'test',
        path: '/',
      }),
      children: [],
    });
    const {harness} = await createComponent();

    const folderNames = await harness.getFolderNames(0);
    expect(folderNames.length).toBe(1);
    expect(folderNames[0]).toContain('folder');
  });

  it('shows article icon for files', async () => {
    fileExplorerStoreMock.fileSystemTree = signal({
      file: newFile({
        name: 'test',
        path: '/',
      }),
      children: [],
    });
    const {harness} = await createComponent();

    const folderNames = await harness.getFolderNames(0);
    expect(folderNames.length).toBe(1);
    expect(folderNames[0]).toContain('article');
  });

  it('shows link icon for symlinks', async () => {
    fileExplorerStoreMock.fileSystemTree = signal({
      file: newFile({
        name: 'test',
        path: '/',
        stat: newStatEntry({stMode: BigInt(0o120644)}),
      }),
      children: [],
    });
    const {harness} = await createComponent();

    const folderNames = await harness.getFolderNames(0);
    expect(folderNames.length).toBe(1);
    expect(folderNames[0]).toContain('link');
  });

  it('shows spinner when folder is being refreshed', async () => {
    fileExplorerStoreMock.fileSystemTree = signal({
      file: newDirectory({
        name: 'test',
        path: '/',
      }),
      children: [],
    });
    fileExplorerStoreMock.currentlyRefreshingPaths = signal(new Set(['/test']));
    const {harness} = await createComponent();

    const folderNames = await harness.getFolderNames(0);
    expect(folderNames.length).toBe(1);
    expect(folderNames[0]).toContain('refresh');
  });

  describe('search input', () => {
    it('is shown', async () => {
      const {harness} = await createComponent();

      const searchInput = await harness.getSearchInput();
      expect(searchInput).not.toBeNull();
    });

    it('shows the full tree if the search query is empty', fakeAsync(async () => {
      fileExplorerStoreMock.fileSystemTree = signal({
        file: newDirectory({
          name: '',
          path: '/',
        }),
        children: [
          {
            file: newDirectory({
              name: 'foo',
              path: '/foo',
            }),
            children: [
              {
                file: newDirectory({
                  name: 'bar',
                  path: '/foo/bar',
                }),
                children: undefined,
              },
              {
                file: newDirectory({
                  name: 'baz',
                  path: '/foo/baz',
                }),
                children: undefined,
              },
            ],
          },
          {
            file: newDirectory({
              name: 'qux',
              path: '/qux',
            }),
            children: undefined,
          },
        ],
      });
      const {harness} = await createComponent();

      const searchInput = await harness.getSearchInput();
      await searchInput.setValue('');

      const rootFolderNames = await harness.getFolderNames(0);
      expect(rootFolderNames.length).toBe(1);
      expect(rootFolderNames[0]).toContain('/');
      const nestedFolderNames = await harness.getFolderNames(1);
      expect(nestedFolderNames.length).toBe(2);
      expect(nestedFolderNames[0]).toContain('/foo');
      expect(nestedFolderNames[1]).toContain('/qux');
      const nestedNestedFolderNames = await harness.getFolderNames(2);
      expect(nestedNestedFolderNames.length).toBe(2);
      expect(nestedNestedFolderNames[0]).toContain('/bar');
      expect(nestedNestedFolderNames[1]).toContain('/baz');
    }));

    it('shows the full tree to a nested folder that matches the search query', fakeAsync(async () => {
      fileExplorerStoreMock.fileSystemTree = signal({
        file: newDirectory({
          name: '',
          path: '/',
        }),
        children: [
          {
            file: newDirectory({
              name: 'foo',
              path: '/foo',
            }),
            children: [
              {
                file: newDirectory({
                  name: 'bar',
                  path: '/foo/bar',
                }),
                children: undefined,
              },
              {
                file: newDirectory({
                  name: 'baz',
                  path: '/foo/baz',
                }),
                children: undefined,
              },
            ],
          },
          {
            file: newDirectory({
              name: 'qux',
              path: '/qux',
            }),
            children: undefined,
          },
        ],
      });
      const {harness} = await createComponent();

      const searchInput = await harness.getSearchInput();
      await searchInput.setValue('baz');

      const rootFolderNames = await harness.getFolderNames(0);
      expect(rootFolderNames.length).toBe(1);
      expect(rootFolderNames[0]).toContain('/');
      const nestedFolderNames = await harness.getFolderNames(1);
      expect(nestedFolderNames.length).toBe(1);
      expect(nestedFolderNames[0]).toContain('/foo');
      const nestedNestedFolderNames = await harness.getFolderNames(2);
      expect(nestedNestedFolderNames.length).toBe(1);
      expect(nestedNestedFolderNames[0]).toContain('/baz');
    }));

    it('shows all subfolders of a folder that matches the search query', fakeAsync(async () => {
      fileExplorerStoreMock.fileSystemTree = signal({
        file: newDirectory({
          name: '',
          path: '/',
        }),
        children: [
          {
            file: newDirectory({
              name: 'foo',
              path: '/foo',
            }),
            children: [
              {
                file: newDirectory({
                  name: 'bar',
                  path: '/foo/bar',
                }),
                children: undefined,
              },
              {
                file: newDirectory({
                  name: 'baz',
                  path: '/foo/baz',
                }),
                children: undefined,
              },
            ],
          },
          {
            file: newDirectory({
              name: 'qux',
              path: '/qux',
            }),
            children: undefined,
          },
        ],
      });
      const {harness} = await createComponent();

      const searchInput = await harness.getSearchInput();
      await searchInput.setValue('.*foo.*');

      const rootFolderNames = await harness.getFolderNames(0);
      expect(rootFolderNames.length).toBe(1);
      expect(rootFolderNames[0]).toContain('/');
      const nestedFolderNames = await harness.getFolderNames(1);
      expect(nestedFolderNames.length).toBe(1);
      expect(nestedFolderNames[0]).toContain('/foo');
      const nestedNestedFolderNames = await harness.getFolderNames(2);
      expect(nestedNestedFolderNames.length).toBe(2);
      expect(nestedNestedFolderNames[0]).toContain('/bar');
      expect(nestedNestedFolderNames[1]).toContain('/baz');
    }));

    it('only includes full folder matches for search results', fakeAsync(async () => {
      fileExplorerStoreMock.fileSystemTree = signal({
        file: newDirectory({
          name: '',
          path: '/',
        }),
        children: [
          {
            file: newDirectory({
              name: 'foo',
              path: '/foo',
            }),
            children: undefined,
          },
          {
            file: newDirectory({
              name: 'foobar',
              path: '/foobar',
            }),
            children: undefined,
          },
          {
            file: newDirectory({
              name: 'foobarbaz',
              path: '/foobarbaz',
            }),
            children: undefined,
          },
        ],
      });
      const {harness} = await createComponent();

      const searchInput = await harness.getSearchInput();
      await searchInput.setValue('foobar');

      const rootFolderNames = await harness.getFolderNames(0);
      expect(rootFolderNames.length).toBe(1);
      expect(rootFolderNames[0]).toContain('/');
      const nestedFolderNames = await harness.getFolderNames(1);
      expect(nestedFolderNames.length).toBe(2);
      expect(nestedFolderNames[0]).toContain('/foobar');
      expect(nestedFolderNames[1]).toContain('/foobarbaz');
    }));

    it('shows no folders if the search query does not match any folders', fakeAsync(async () => {
      fileExplorerStoreMock.fileSystemTree = signal({
        file: newDirectory({
          name: '',
          path: '/',
        }),
        children: [
          {
            file: newDirectory({
              name: 'foo',
              path: '/foo',
            }),
            children: undefined,
          },
        ],
      });
      const {harness} = await createComponent();

      const searchInput = await harness.getSearchInput();
      await searchInput.setValue('WOHOO_DO_NOT_MATCH');

      const rootFolderNames = await harness.getFolderNames(0);
      expect(rootFolderNames.length).toBe(0);
    }));

    it('shows a hint if the search query is invalid', fakeAsync(async () => {
      fileExplorerStoreMock.fileSystemTree = signal({
        file: newDirectory({
          name: '',
          path: '/',
        }),
        children: undefined,
      });
      const {harness} = await createComponent();

      const searchInput = await harness.getSearchInput();
      await searchInput.setValue('** invalid regex');

      const formField = await harness.searchFormField();
      expect(await formField.getTextHints()).toEqual(['Invalid search query']);
    }));
  });

  it('shows full path when folder is selected', fakeAsync(async () => {
    fileExplorerStoreMock.fileSystemTree = signal({
      file: newDirectory({
        name: '',
        path: '/',
      }),
      children: [
        {
          file: newDirectory({
            name: 'testFolder',
            path: '/testFolder',
          }),
          children: [
            {
              file: newFile({
                name: 'testFile',
                path: '/testFolder/testFile',
              }),
              children: undefined,
            },
          ],
        },
      ],
    });
    const {harness} = await createComponent();

    await harness.selectFileOrDirectory('testFile');

    const folderNames = await harness.getFolderNames(2);
    expect(folderNames.length).toBe(1);
    expect(folderNames[0]).toContain('/testFolder/testFile');
  }));

  it('shows refresh button for folders that are loaded', async () => {
    fileExplorerStoreMock.fileSystemTree = signal({
      file: newDirectory({
        name: 'test',
        path: '/',
      }),
      children: [],
    });
    const {harness} = await createComponent();

    const refreshButton = await harness.getOptionalRefreshButton('test');
    expect(refreshButton).not.toBeNull();
  });

  it('shows no refresh button for folders that are not loaded', async () => {
    fileExplorerStoreMock.fileSystemTree = signal({
      file: newDirectory({
        name: 'test',
        path: '/',
      }),
      children: undefined,
    });
    const {harness} = await createComponent();

    const refreshButton = await harness.getOptionalRefreshButton('test');
    expect(refreshButton).toBeNull();
  });

  it('hides refresh button for files', async () => {
    fileExplorerStoreMock.fileSystemTree = signal({
      file: newFile({
        name: 'test',
        path: '/',
      }),
      children: [],
    });
    const {harness} = await createComponent();

    const refreshButton = await harness.getOptionalRefreshButton('test');
    expect(refreshButton).toBeNull();
  });

  it('shows no collapsible container folder when children are not loaded', async () => {
    fileExplorerStoreMock.fileSystemTree = signal({
      file: newDirectory({
        name: '',
        path: '/',
        isDirectory: true,
      }),
      children: undefined,
    });
    const {harness} = await createComponent();

    const rootFolderNames = await harness.getFolderNames(0);
    expect(rootFolderNames.length).toBe(1);
    expect(rootFolderNames[0]).toContain('/');
    const rootContainers = await harness.getCollapsibleContainers(0);
    expect(rootContainers.length).toBe(0);
  });

  it('shows a collapsible container folder when children are loaded but empty', async () => {
    fileExplorerStoreMock.fileSystemTree = signal({
      file: newDirectory({
        name: '',
        path: '/',
        isDirectory: true,
      }),
      children: [],
    });
    const {harness} = await createComponent();

    const rootFolderNames = await harness.getFolderNames(0);
    expect(rootFolderNames.length).toBe(1);
    expect(rootFolderNames[0]).toContain('/');
    const rootContainers = await harness.getCollapsibleContainers(0);
    expect(rootContainers.length).toBe(1);
    expect(await rootContainers[0].showsCollapseIcon()).toBeTrue();
  });

  it('shows no collapsible container for files', async () => {
    fileExplorerStoreMock.fileSystemTree = signal({
      file: newFile({
        name: 'test',
        path: '/test',
      }),
      children: undefined,
    });
    const {harness} = await createComponent();

    const folderNames = await harness.getFolderNames(0);
    expect(folderNames.length).toBe(1);
    expect(folderNames[0]).toContain('/test');
    const collapsibleContainers = await harness.getCollapsibleContainers(0);
    expect(collapsibleContainers.length).toBe(0);
  });

  it('disables folder button and shows symlink target when it is a symlink', fakeAsync(async () => {
    fileExplorerStoreMock.fileSystemTree = signal({
      file: newDirectory({
        name: '',
        path: '/',
        isDirectory: true,
      }),
      children: [
        {
          file: newFile({
            name: 'testSymlink',
            path: '/testSymlink',
            stat: newStatEntry({
              stMode: BigInt(0o120644),
              symlink: 'testSymlinkTarget',
            }),
          }),
          children: undefined,
        },
      ],
    });
    const {harness} = await createComponent();

    const folderButton = await harness.getFileOrDirectoryButton('testSymlink');
    expect(folderButton).not.toBeNull();
    expect(await folderButton!.isDisabled()).toBeTrue();
    const folderName = await harness.getFolderNames(1);
    expect(folderName.length).toBe(1);
    expect(folderName[0]).toContain('testSymlink');
    expect(folderName[0]).toContain('testSymlinkTarget');
  }));

  it('loads children when a folder is clicked and not loaded', fakeAsync(async () => {
    fileExplorerStoreMock.fileSystemTree = signal({
      file: newDirectory({
        name: '',
        path: '/',
        isDirectory: true,
      }),
      children: undefined,
    });

    const {harness} = await createComponent();
    await harness.selectFileOrDirectory('/');

    expect(fileExplorerStoreMock.fetchChildren).toHaveBeenCalledWith({
      file: newDirectory({
        name: '',
        path: '/',
        isDirectory: true,
      }),
      children: undefined,
    });
  }));

  it('shows file results table when a folder is selected', fakeAsync(async () => {
    fileExplorerStoreMock.fileSystemTree = signal({
      file: newDirectory({
        name: '',
        path: '/',
        isDirectory: true,
      }),
      children: [
        {
          file: newFile({
            name: 'testFile',
            path: '/testFile',
            stat: newStatEntry({
              pathspec: {
                path: '/testFile',
                pathtype: PathSpecPathType.OS,
                segments: [],
              },
            }),
          }),
          children: undefined,
        },
        {
          file: newDirectory({
            name: 'testFolder',
            path: '/testFolder',
            stat: newStatEntry({
              pathspec: {
                path: '/testFolder',
                pathtype: PathSpecPathType.OS,
                segments: [],
              },
            }),
          }),
          children: undefined,
        },
        {
          file: newDirectory({
            name: 'testFolder2',
            path: '/testFolder2',
            // No stat entry.
            // Some vfs results do not report the stat entry for folders, we
            // are backfilling the path and pathtype in this case for the
            // FileResultsTable.
          }),
          children: undefined,
        },
      ],
    });
    const {harness} = await createComponent('C.1234567890123456');

    await harness.selectFileOrDirectory('/');

    const fileResultsTable = await harness.fileResultsTable();
    expect(fileResultsTable).not.toBeNull();
    const rows = await fileResultsTable!.getRows();
    expect(await rows.length).toBe(3);
    expect(await fileResultsTable!.getCellText(0, 'path')).toContain(
      '/testFile',
    );
    expect(await fileResultsTable!.getCellText(1, 'path')).toContain(
      '/testFolder',
    );
    expect(await fileResultsTable!.getCellText(2, 'path')).toContain(
      '/testFolder2',
    );
  }));

  it('shows file content when a file is selected', fakeAsync(async () => {
    const file = newFile({
      name: 'testFile',
      path: '/testFile',
      stat: newStatEntry({
        pathspec: {
          path: '/testFile',
          pathtype: PathSpecPathType.OS,
          segments: [
            {
              path: '/testFile',
              pathtype: PathSpecPathType.OS,
            },
          ],
        },
      }),
    });
    fileStoreMock.fileDetailsMap = signal(
      new Map([
        [
          'C.1234567890123456',
          new Map([[PathSpecPathType.OS, new Map([['/testFile', file]])]]),
        ],
      ]),
    );
    fileExplorerStoreMock.fileSystemTree = signal({
      file: newDirectory({
        name: '',
        path: '/',
        isDirectory: true,
      }),
      children: [
        {
          file,
          children: undefined,
        },
      ],
    });
    const {harness} = await createComponent('C.1234567890123456');

    await harness.selectFileOrDirectory('/testFile');

    const fileResultsTable = await harness.fileResultsTable();
    expect(fileResultsTable).toBeNull();
    const fileContent = await harness.fileContent();
    expect(fileContent).not.toBeNull();
    const statView = await fileContent!.statView();
    expect(statView).not.toBeNull();
    const detailsTable = await statView!.detailsTable();
    expect(detailsTable).not.toBeNull();
    expect(await detailsTable!.text()).toContain('/testFile');
  }));

  it('calls refreshVfsFolder when List directory button is clicked', fakeAsync(async () => {
    const testFolder = {
      file: newDirectory({
        name: 'testFolder',
        path: '/testFolder',
      }),
      children: undefined,
    };
    fileExplorerStoreMock.fileSystemTree = signal({
      file: newDirectory({
        name: '',
        path: '/',
        isDirectory: true,
      }),
      children: [testFolder],
    });
    const {harness} = await createComponent('C.1234567890123456');

    await harness.selectFileOrDirectory('/testFolder');
    const listDirectoryButton = await harness.listDirectoryButton();
    await listDirectoryButton!.click();

    expect(fileExplorerStoreMock.refreshVfsFolder).toHaveBeenCalledWith(
      testFolder,
      1,
    );
  }));

  it('calls refreshVfsFolder when List directory & subdirectories button is clicked', fakeAsync(async () => {
    const testFolder = {
      file: newDirectory({
        name: 'testFolder',
        path: '/testFolder',
      }),
      children: undefined,
    };
    fileExplorerStoreMock.fileSystemTree = signal({
      file: newDirectory({
        name: '',
        path: '/',
        isDirectory: true,
      }),
      children: [testFolder],
    });
    const {harness} = await createComponent('C.1234567890123456');

    await harness.selectFileOrDirectory('/testFolder');
    const listDirectoryAndSubdirectoriesButton =
      await harness.listDirectoryAndSubdirectoriesButton();
    await listDirectoryAndSubdirectoriesButton!.click();

    expect(fileExplorerStoreMock.refreshVfsFolder).toHaveBeenCalledWith(
      testFolder,
      5,
    );
  }));

  it('shows download all button when root folder is selected', fakeAsync(async () => {
    fileExplorerStoreMock.fileSystemTree = signal({
      file: newDirectory({
        name: '',
        path: '/',
      }),
      children: undefined,
    });
    const {harness} = await createComponent('C.1234567890123456');

    await harness.selectFileOrDirectory('/');
    const downloadAllButton = await harness.downloadAllButton();
    expect(downloadAllButton).not.toBeNull();
  }));

  it('hides download all button when non-root folder is selected', fakeAsync(async () => {
    const testFolder = {
      file: newDirectory({
        name: 'testFolder',
        path: '/testFolder',
      }),
      children: undefined,
    };
    fileExplorerStoreMock.fileSystemTree = signal({
      file: newDirectory({
        name: '',
        path: '/',
        isDirectory: true,
      }),
      children: [testFolder],
    });
    const {harness} = await createComponent('C.1234567890123456');

    await harness.selectFileOrDirectory('/testFolder');
    const downloadAllButton = await harness.downloadAllButton();
    expect(downloadAllButton).toBeNull();
  }));
});

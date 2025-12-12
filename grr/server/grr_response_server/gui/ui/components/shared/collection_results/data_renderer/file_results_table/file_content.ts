

import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
  signal,
} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatProgressSpinnerModule} from '@angular/material/progress-spinner';
import {MatTabsModule} from '@angular/material/tabs';

import {getFileBlobUrl} from '../../../../../lib/api/http_api_service';
import {
  Directory,
  File as VfsFile,
  FileContent as VfsFileContent,
} from '../../../../../lib/models/vfs';
import {FileQuery, FileStore} from '../../../../../store/file_store';
import {FlowFileResult} from './file_results_table';
import {HexView} from './hex_view';
import {StatView} from './stat_view';
import {TextView} from './text_view';

const DEFAULT_CONTENT_OFFSET = 0;
const DEFAULT_CONTENT_LENGTH = 1000;

/**
 * Component that displays a file table.
 */
@Component({
  selector: 'file-content',
  templateUrl: './file_content.ng.html',
  styleUrls: ['./file_content.scss'],
  imports: [
    CommonModule,
    HexView,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatTabsModule,
    StatView,
    TextView,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [FileStore],
})
export class FileContent {
  protected readonly fileStore = inject(FileStore);

  readonly file = input.required<FlowFileResult | null>();

  private readonly hexContentOffset = signal(DEFAULT_CONTENT_OFFSET);
  private readonly hexContentLength = signal(DEFAULT_CONTENT_LENGTH);

  private readonly textContentOffset = signal(DEFAULT_CONTENT_OFFSET);
  private readonly textContentLength = signal(DEFAULT_CONTENT_LENGTH);

  protected readonly downloadUrl = computed<string | null>(() => {
    const file = this.file();
    if (!file || !file.statEntry.pathspec) {
      return null;
    }
    return getFileBlobUrl({
      clientId: file.clientId,
      pathType: file.statEntry.pathspec.pathtype,
      path: file.statEntry.pathspec.path,
    });
  });

  constructor() {
    this.fileStore.fetchFileContentAccess(
      computed<FileQuery | undefined>(() => {
        const file = this.file();
        if (!file || !file.statEntry.pathspec) {
          return undefined;
        }
        return {
          clientId: file.clientId,
          pathType: file.statEntry.pathspec.pathtype,
          path: file.statEntry.pathspec.path,
        };
      }),
    );

    this.fileStore.fetchBinaryFile(
      computed<FileQuery | undefined>(() => {
        const file = this.file();
        if (!file || !file.statEntry.pathspec) {
          return undefined;
        }
        return {
          clientId: file.clientId,
          pathType: file.statEntry.pathspec.pathtype,
          path: file.statEntry.pathspec.path,
          offset: this.hexContentOffset(),
          length: this.hexContentLength(),
          hasFileContentAccess: this.currentFileContentAccess(),
        };
      }),
    );

    this.fileStore.fetchTextFile(
      computed<FileQuery | undefined>(() => {
        const file = this.file();
        if (!file || !file.statEntry.pathspec) {
          return undefined;
        }
        return {
          clientId: file.clientId,
          pathType: file.statEntry.pathspec?.pathtype,
          path: file.statEntry.pathspec?.path,
          offset: this.textContentOffset(),
          length: this.textContentLength(),
          hasFileContentAccess: this.currentFileContentAccess(),
        };
      }),
    );

    this.fileStore.fetchFileDetails(
      computed<FileQuery | undefined>(() => {
        const file = this.file();
        if (!file || !file.statEntry.pathspec) {
          return undefined;
        }
        return {
          clientId: file?.clientId,
          pathType: file?.statEntry.pathspec?.pathtype,
          path: file?.statEntry.pathspec?.path,
          hasFileContentAccess: this.currentFileContentAccess(),
        };
      }),
    );
  }

  protected readonly currentFileContentAccess = computed<boolean | undefined>(
    () => {
      const file = this.file();
      if (!file || !file.statEntry.pathspec) {
        return undefined;
      }
      return this.fileStore
        .fileContentAccessMap()
        ?.get(file.clientId)
        ?.get(file.statEntry.pathspec.pathtype)
        ?.get(file.statEntry.pathspec.path);
    },
  );

  protected currentFileOrDirectoryDetails = computed<
    VfsFile | Directory | undefined
  >(() => {
    const file = this.file();
    if (!file || !file.statEntry.pathspec) {
      return undefined;
    }
    return this.fileStore
      .fileDetailsMap()
      ?.get(file.clientId)
      ?.get(file.statEntry.pathspec.pathtype)
      ?.get(file.statEntry.pathspec.path);
  });

  protected isFile = computed<boolean | undefined>(() => {
    const fileOrDirectory = this.currentFileOrDirectoryDetails();
    if (!fileOrDirectory) {
      return undefined;
    }
    return !fileOrDirectory.isDirectory;
  });

  protected isDirectory = computed<boolean | undefined>(() => {
    const fileOrDirectory = this.currentFileOrDirectoryDetails();
    if (!fileOrDirectory) {
      return undefined;
    }
    return fileOrDirectory.isDirectory;
  });

  protected currentHexContent = computed<VfsFileContent | undefined>(() => {
    const file = this.file();
    if (!file || !file.statEntry.pathspec) {
      return undefined;
    }
    return this.fileStore
      .fileBlobMap()
      ?.get(file.clientId)
      ?.get(file.statEntry.pathspec.pathtype)
      ?.get(file.statEntry.pathspec.path);
  });

  protected currentTextContent = computed<VfsFileContent | undefined>(() => {
    const file = this.file();
    if (!file || !file.statEntry.pathspec) {
      return undefined;
    }
    return this.fileStore
      .fileTextMap()
      ?.get(file.clientId)
      ?.get(file.statEntry.pathspec.pathtype)
      ?.get(file.statEntry.pathspec.path);
  });

  protected hasMoreTextContent = computed<boolean>(() => {
    const textContent = this.currentTextContent();
    if (!textContent) {
      return false;
    }
    return textContent.totalLength > (textContent.textContent?.length ?? 0);
  });

  protected hasMoreHexContent = computed<boolean>(() => {
    const hexContent = this.currentHexContent();
    if (!hexContent) {
      return false;
    }
    return hexContent.totalLength > (hexContent.blobContent?.byteLength ?? 0);
  });

  loadMoreTextContent(amount = DEFAULT_CONTENT_LENGTH) {
    const currentLength = this.currentTextContent()?.textContent?.length ?? 0;
    this.textContentLength.set(currentLength + amount);
  }

  loadMoreHexContent(amount = DEFAULT_CONTENT_LENGTH) {
    const currentLength =
      this.currentHexContent()?.blobContent?.byteLength ?? 0;
    this.hexContentLength.set(currentLength + amount);
  }

  protected isRecollecting() {
    const file = this.file();
    if (!file || !file.statEntry.pathspec) {
      return false;
    }
    return this.fileStore.isRecollecting({
      clientId: file.clientId,
      pathType: file.statEntry.pathspec.pathtype,
      path: file.statEntry.pathspec.path,
    });
  }

  protected recollectFile() {
    const file = this.file();
    if (!file || !file.statEntry.pathspec) {
      return;
    }
    this.fileStore.recollectFile({
      clientId: file.clientId,
      pathType: file.statEntry.pathspec.pathtype,
      path: file.statEntry.pathspec.path,
    });
  }
}

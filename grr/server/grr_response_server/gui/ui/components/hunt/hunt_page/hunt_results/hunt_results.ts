import {Clipboard} from '@angular/cdk/clipboard';
import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  OnDestroy,
  Output,
} from '@angular/core';

import {ExportMenuItem} from '../../../../components/flow_details/plugins/plugin';
import {
  getHuntExportedResultsCsvUrl,
  getHuntExportedResultsSqliteUrl,
  getHuntExportedResultsYamlUrl,
  getHuntFilesArchiveTarGzUrl,
  getHuntFilesArchiveZipUrl,
} from '../../../../lib/api/http_api_service';
import {ERROR_TAB} from '../../../../lib/api_translation/result';
import {
  CellComponent,
  HuntResultOrError,
  HuntResultsTableTabConfig,
  PayloadType,
  TypedHuntResultOrError,
} from '../../../../lib/models/result';
import {observeOnDestroy} from '../../../../lib/reactive';

/**
 * Encapsulates the display of different kind of Hunt Results and Errors.
 */
@Component({
  selector: 'app-hunt-results',
  templateUrl: './hunt_results.ng.html',
  styleUrls: ['./hunt_results.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HuntResults implements OnDestroy {
  @Input() huntId = '';
  @Input() tabsConfig: HuntResultsTableTabConfig[] = [];
  @Input() isLoading = false;

  @Output()
  readonly selectedHuntResult = new EventEmitter<TypedHuntResultOrError>();

  readonly CellComponent = CellComponent;
  readonly ERROR_TAB = ERROR_TAB;

  readonly ngOnDestroy = observeOnDestroy(this);

  protected copied = false;

  constructor(private readonly clipboard: Clipboard) {}

  get exportMenuItems(): readonly ExportMenuItem[] {
    return [
      {
        title: 'Download files (TAR GZ)',
        url: getHuntFilesArchiveTarGzUrl(this.huntId),
        downloadName: `results_hunt_${this.huntId}.tar.gz`,
      },
      {
        title: 'Download files (ZIP)',
        url: getHuntFilesArchiveZipUrl(this.huntId),
        downloadName: `results_hunt_${this.huntId}.zip`,
      },
      {
        title: 'Download (CSV)',
        url: getHuntExportedResultsCsvUrl(this.huntId),
        downloadName: `hunt_${this.huntId}.csv.zip`,
      },
      {
        title: 'Download (YAML)',
        url: getHuntExportedResultsYamlUrl(this.huntId),
        downloadName: `hunt_${this.huntId}.yaml.zip`,
      },
      {
        title: 'Download (SQLite)',
        url: getHuntExportedResultsSqliteUrl(this.huntId),
        downloadName: `hunt_${this.huntId}.sql.zip`,
      },
    ];
  }

  exportCommand() {
    const cmd =
      `/usr/bin/grr_api_shell 'http://localhost:8081' --exec_code` +
      `'grrapi.Hunt("${this.huntId}").GetFilesArchive().WriteToFile(` +
      `"./hunt_results_${this.huntId}.zip")'`;
    this.copied = this.clipboard.copy(cmd);
  }

  trackByPayloadType(index: number, tab: HuntResultsTableTabConfig) {
    return tab.payloadType;
  }
  trackExportMenuItem(index: number, entry: ExportMenuItem) {
    return entry.title;
  }

  emitSelectedHuntResult(
    resultOrError: HuntResultOrError,
    payloadType: PayloadType,
  ): void {
    this.selectedHuntResult.emit({value: resultOrError, payloadType});
  }
}

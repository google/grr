import {Clipboard} from '@angular/cdk/clipboard';
import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  OnDestroy,
  Output,
} from '@angular/core';

import {
  ButtonType,
  ExportMenuItem,
} from '../../../../components/flow_details/plugins/plugin';
import {
  getHuntExportCLICommand,
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

/** Default export command prefix. */
export const DEFAULT_EXPORT_COMMAND_PREFIX =
  "/usr/bin/grr_api_shell 'http://localhost:8081'";

/**
 * Encapsulates the display of different kind of Hunt Results and Errors.
 */
@Component({
  standalone: false,
  selector: 'app-hunt-results',
  templateUrl: './hunt_results.ng.html',
  styleUrls: ['./hunt_results.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HuntResults implements OnDestroy {
  @Input() huntId = '';
  @Input() tabsConfig: HuntResultsTableTabConfig[] = [];
  @Input() isLoading = false;
  @Input() exportCommandPrefix = DEFAULT_EXPORT_COMMAND_PREFIX;

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
        type: ButtonType.LINK,
      },
      {
        title: 'Download files (ZIP)',
        url: getHuntFilesArchiveZipUrl(this.huntId),
        downloadName: `results_hunt_${this.huntId}.zip`,
        type: ButtonType.LINK,
      },
      {
        title: 'Download (CSV)',
        url: getHuntExportedResultsCsvUrl(this.huntId),
        downloadName: `hunt_${this.huntId}.csv.zip`,
        type: ButtonType.LINK,
      },
      {
        title: 'Download (YAML)',
        url: getHuntExportedResultsYamlUrl(this.huntId),
        downloadName: `hunt_${this.huntId}.yaml.zip`,
        type: ButtonType.LINK,
      },
      {
        title: 'Download (SQLite)',
        url: getHuntExportedResultsSqliteUrl(this.huntId),
        downloadName: `hunt_${this.huntId}.sql.zip`,
        type: ButtonType.LINK,
      },
    ];
  }

  exportCommand() {
    const cmd = getHuntExportCLICommand(this.exportCommandPrefix, this.huntId);
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

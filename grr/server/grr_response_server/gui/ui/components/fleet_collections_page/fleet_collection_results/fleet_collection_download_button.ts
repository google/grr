import {Clipboard} from '@angular/cdk/clipboard';
import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
} from '@angular/core';
import {MatButtonModule} from '@angular/material/button';
import {MatIconModule} from '@angular/material/icon';
import {MatMenuModule} from '@angular/material/menu';

import {
  getHuntExportCLICommand,
  getHuntExportedResultsCsvUrl,
  getHuntExportedResultsSqliteUrl,
  getHuntExportedResultsYamlUrl,
  getHuntFilesArchiveTarGzUrl,
  getHuntFilesArchiveZipUrl,
} from '../../../lib/api/http_api_service';
import {GlobalStore} from '../../../store/global_store';

/** An entry in the Flow's Download/Export menu. */
interface ExportMenuItem {
  // The displayed title of the menu item.
  title: string;
  // URL of the file to download.
  url: string;
  // If true, the menu item is a link, otherwise it is a string to copy.
  isLink: boolean;
}

function downloadTarGzFilesMenuItem(fleetCollectionId: string): ExportMenuItem {
  return {
    title: 'Download files (Tarball)',
    url: getHuntFilesArchiveTarGzUrl(fleetCollectionId),
    isLink: true,
  };
}

function downloadZipFilesExportMenuItem(
  fleetCollectionId: string,
): ExportMenuItem {
  return {
    title: 'Download files (ZIP)',
    url: getHuntFilesArchiveZipUrl(fleetCollectionId),
    isLink: true,
  };
}

function csvExportMenuItem(fleetCollectionId: string): ExportMenuItem {
  return {
    title: 'Download CSV',
    url: getHuntExportedResultsCsvUrl(fleetCollectionId),
    isLink: true,
  };
}

function yamlExportMenuItem(fleetCollectionId: string): ExportMenuItem {
  return {
    title: 'Download YAML',
    url: getHuntExportedResultsYamlUrl(fleetCollectionId),
    isLink: true,
  };
}

function sqliteExportMenuItem(fleetCollectionId: string): ExportMenuItem {
  return {
    title: 'Download SQLite',
    url: getHuntExportedResultsSqliteUrl(fleetCollectionId),
    isLink: true,
  };
}

function cliExportMenuItem(
  exportCommandPrefix: string,
  fleetCollectionId: string,
): ExportMenuItem {
  return {
    title: 'Copy CLI Command',
    url: getHuntExportCLICommand(exportCommandPrefix, fleetCollectionId),
    isLink: false,
  };
}

/**
 * Component displaying download button for fleet collection results.
 */
@Component({
  selector: 'fleet-collection-download-button',
  templateUrl: './fleet_collection_download_button.ng.html',
  imports: [CommonModule, MatButtonModule, MatIconModule, MatMenuModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FleetCollectionDownloadButton {
  protected readonly globalStore = inject(GlobalStore);
  protected readonly clipboard = inject(Clipboard);

  protected readonly fleetCollectionId = input.required<string>();

  protected exportMenuItems = computed<readonly ExportMenuItem[]>(() => {
    const exportMenuItems: ExportMenuItem[] = [];
    exportMenuItems.push(
      downloadTarGzFilesMenuItem(this.fleetCollectionId()),
      downloadZipFilesExportMenuItem(this.fleetCollectionId()),
      csvExportMenuItem(this.fleetCollectionId()),
      yamlExportMenuItem(this.fleetCollectionId()),
      sqliteExportMenuItem(this.fleetCollectionId()),
    );
    const exportCommandPrefix = this.globalStore.exportCommandPrefix();
    if (exportCommandPrefix) {
      exportMenuItems.push(
        cliExportMenuItem(exportCommandPrefix, this.fleetCollectionId()),
      );
    }
    return exportMenuItems;
  });

  copyToClipboard(str: string) {
    if (str !== null) {
      this.clipboard.copy(str);
    }
  }
}

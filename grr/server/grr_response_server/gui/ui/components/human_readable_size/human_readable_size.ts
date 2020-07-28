import {Component, Input} from '@angular/core';

/**
 * Shows a size in a human readable format.
 */
@Component({
  selector: 'human-readable-size',
  templateUrl: './human_readable_size.ng.html',
})
export class HumanReadableSizeComponent {
  @Input() size?: number;
  private static readonly UNITS = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB'];

  toHuman(): string {
    if (this.size === undefined || this.size < 0) {
      return '-';
    }

    let i = 0;
    let size = this.size;
    let decimals = 1;

    while (size >= 1024 && i < HumanReadableSizeComponent.UNITS.length - 1) {
      size /= 1024;
      i++;
    }

    if (i == 0) {
      decimals = 0;
    }

    return size.toFixed(decimals) + ' ' + HumanReadableSizeComponent.UNITS[i];
  }
}

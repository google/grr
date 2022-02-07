import {Component, Input} from '@angular/core';

/**
 * Shows a size in a human readable format.
 */
@Component({
  selector: 'human-readable-size',
  templateUrl: './human_readable_size.ng.html',
})
export class HumanReadableSizeComponent {
  @Input() size?: number|bigint|null;
  private static readonly UNITS = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB'];

  getHumanSize(): string {
    if (this.size === undefined || this.size === null || this.size < 0) {
      return '';
    }

    if (typeof this.size === 'bigint') {
      this.size = Number(this.size);
    }

    let i = 0;
    let size = this.size;
    let decimals = 2;

    while (size >= 1024 && i < HumanReadableSizeComponent.UNITS.length - 1) {
      size /= 1024;
      i++;
    }

    if (i === 0) {
      decimals = 0;
    }
    const fixed = Math.pow(10, decimals);

    // Using math here to truncate the unneeded decimals, because there is no
    // implementation for this. See this post for more info
    // https://stackoverflow.com/questions/4187146/truncate-number-to-two-decimal-places-without-rounding
    return `${(Math.floor(size * fixed) / fixed).toFixed(decimals)} ${
        HumanReadableSizeComponent.UNITS[i]}`;
  }
}

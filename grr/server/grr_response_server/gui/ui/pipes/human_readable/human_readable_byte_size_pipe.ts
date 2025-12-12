import {Pipe, PipeTransform} from '@angular/core';

const UNITS = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB'];

/**
 * Pipe that converts number of bytes to a human readable format.
 */
@Pipe({name: 'humanReadableByteSize'})
export class HumanReadableByteSizePipe implements PipeTransform {
  transform(size: number | bigint | null | undefined): string {
    if (size == null || size < 0) {
      return '';
    }

    if (typeof size === 'bigint') {
      size = Number(size);
    }

    let i = 0;
    let decimals = 2;

    while (size >= 1024 && i < UNITS.length - 1) {
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
    return `${(Math.floor(size * fixed) / fixed).toFixed(decimals)} ${UNITS[i]}`;
  }
}

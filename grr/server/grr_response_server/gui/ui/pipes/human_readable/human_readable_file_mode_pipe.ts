

import {Pipe, PipeTransform} from '@angular/core';

const S_IFMT = 0o170000; // type of file
const S_IFIFO = 0o010000; // named pipe
const S_IFCHR = 0o020000; // character device
const S_IFDIR = 0o040000; // directory
const S_IFBLK = 0o060000; // block device
const S_IFREG = 0o100000; // regular file
const S_IFLNK = 0o120000; // symbolic link
const S_IFSOCK = 0o140000; // socket
const S_ISUID = 0o004000; // set user id
const S_ISGID = 0o002000; // set group id
const S_ISVTX = 0o001000; // save swapped text even after use
const S_IRUSR = 0o000400; // owner, read permission
const S_IWUSR = 0o000200; // owner, write permission
const S_IXUSR = 0o000100; // owner, execute/search permission
const S_IRGRP = 0o000040; // group, read permission
const S_IWGRP = 0o000020; // group, write permission
const S_IXGRP = 0o000010; // group, execute/search permission
const S_IROTH = 0o000004; // others, read permission
const S_IWOTH = 0o000002; // others, write permission
const S_IXOTH = 0o000001; // others, execute/search permission

const FILE_TYPE_CHARS_MAP: ReadonlyMap<number, string> = new Map([
  [S_IFREG, '-'],
  [S_IFBLK, 'b'],
  [S_IFCHR, 'c'],
  [S_IFDIR, 'd'],
  [S_IFIFO, 'p'],
  [S_IFLNK, 'l'],
  [S_IFSOCK, 's'],
]);

/**
 * Converts a given file mode (represented as a stringified integer) to a
 * human readable format.
 */
@Pipe({name: 'humanReadableFileMode'})
export class HumanReadableFileModePipe implements PipeTransform {
  transform(statModeStr: string | undefined): string {
    if (statModeStr === undefined || statModeStr === '') {
      return '-';
    }

    // Keep at most 32 bits of the original mode. They're guaranteed to
    // fit into Number integer type.
    const statMode = Number(BigInt(statModeStr) & BigInt(0xffffffff));
    const fileType = FILE_TYPE_CHARS_MAP.get(statMode & S_IFMT) ?? '-';

    let permissions = '';
    permissions += statMode & S_IRUSR ? 'r' : '-';
    permissions += statMode & S_IWUSR ? 'w' : '-';
    if (statMode & S_ISUID) {
      permissions += statMode & S_IXUSR ? 's' : 'S';
    } else {
      permissions += statMode & S_IXUSR ? 'x' : '-';
    }

    permissions += statMode & S_IRGRP ? 'r' : '-';
    permissions += statMode & S_IWGRP ? 'w' : '-';
    if (statMode & S_ISGID) {
      permissions += statMode & S_IXGRP ? 's' : 'S';
    } else {
      permissions += statMode & S_IXGRP ? 'x' : '-';
    }

    permissions += statMode & S_IROTH ? 'r' : '-';
    permissions += statMode & S_IWOTH ? 'w' : '-';
    if (statMode & S_ISVTX) {
      permissions += statMode & S_IXOTH ? 't' : 'T';
    } else {
      permissions += statMode & S_IXOTH ? 'x' : '-';
    }

    return fileType + permissions;
  }
}

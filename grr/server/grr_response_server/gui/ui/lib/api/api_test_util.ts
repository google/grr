/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {StatEntry} from '../../lib/models/vfs';
import {translateStatEntry} from '../api_translation/flow';

import {PathSpec, PathSpecPathType} from './api_interfaces';

export function newPathSpec(
    path: string,
    type: PathSpecPathType.OS|PathSpecPathType.TSK =
        PathSpecPathType.OS): PathSpec {
  return {path, pathtype: type};
}

export function createStatEntry(index: number): StatEntry {
  return translateStatEntry({
    pathspec: newPathSpec(`/home/foo/bar/${index}`),
    stMode: '420',  // 0644
    stDev: (16777220 + index).toString(),
    stNlink: (1 + index).toString(),
    stSize: `${index + 1}42`,
    stAtime: `${index + 1}40000`,
    stMtime: `${index + 1}400000`,
    stCtime: `${index + 1}4000000`,
    stBtime: `${index + 1}40000000`,
  });
}

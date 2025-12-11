/**
 * Test helpers.
 */
// tslint:disable:enforce-comments-on-exported-symbols

import {StatEntry} from '../../lib/models/vfs';
import {translateStatEntry} from '../api/translation/flow';

import {PathSpec, PathSpecPathType} from './api_interfaces';

export function newPathSpec(
  path: string,
  type: PathSpecPathType.OS | PathSpecPathType.TSK = PathSpecPathType.OS,
): PathSpec {
  return {path, pathtype: type};
}

export function createStatEntry(index: number): StatEntry {
  return translateStatEntry({
    pathspec: newPathSpec(`/home/foo/bar/${index}`),
    stMode: '420', // 0644
    stDev: (16777220 + index).toString(),
    stNlink: (1 + index).toString(),
    stSize: `${index + 1}42`,
    stAtime: `16801${index + 1}0`,
    stMtime: `16801${index + 1}1`,
    stCtime: `16801${index + 1}2`,
    stBtime: `16801${index + 1}3`,
  });
}

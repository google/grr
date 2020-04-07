/** Test helpers. */
// tslint:disable:enforce-comments-on-exported-symbols

import {PathSpec, PathSpecPathType} from './api_interfaces';

export function newPathSpec(
    path: string,
    type: PathSpecPathType.OS|PathSpecPathType.TSK =
        PathSpecPathType.OS): PathSpec {
  return {path, pathtype: type};
}

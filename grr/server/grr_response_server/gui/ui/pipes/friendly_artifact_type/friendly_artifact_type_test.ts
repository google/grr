import {SourceType} from '../../lib/models/flow';
import {FriendlyArtifactTypePipe} from './friendly_artifact_type';

describe('Friendly Artifact Type Pipe', () => {
  const pipe: FriendlyArtifactTypePipe = new FriendlyArtifactTypePipe();

  it('returns the artifact type name', () => {
    expect(pipe.transform(SourceType.COMMAND)).toEqual('Executes command');
    expect(pipe.transform(SourceType.FILE)).toEqual('Collects file');
    expect(pipe.transform(SourceType.PATH)).toEqual('Collects path');
    expect(pipe.transform(SourceType.REGISTRY_KEY)).toEqual(
      'Collects Windows Registry key',
    );
    expect(pipe.transform(SourceType.REGISTRY_VALUE)).toEqual(
      'Collects Windows Registry value',
    );
    expect(pipe.transform(SourceType.WMI)).toEqual('Queries WMI');
    expect(pipe.transform(SourceType.COLLECTOR_TYPE_UNKNOWN)).toEqual(
      'Unknown artifact',
    );
  });
});

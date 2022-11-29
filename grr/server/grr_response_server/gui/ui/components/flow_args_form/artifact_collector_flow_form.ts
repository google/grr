import {NestedTreeControl} from '@angular/cdk/tree';
import {ChangeDetectionStrategy, Component} from '@angular/core';
import {FormControl} from '@angular/forms';
import {MatTreeNestedDataSource} from '@angular/material/tree';
import {combineLatest} from 'rxjs';
import {distinctUntilChanged, map, startWith, takeUntil} from 'rxjs/operators';

import {FlowArgumentForm} from '../../components/flow_args_form/form_interface';
import {ArtifactCollectorFlowArgs} from '../../lib/api/api_interfaces';
import {safeTranslateOperatingSystem} from '../../lib/api_translation/flow';
import {ArtifactDescriptor, ArtifactSource, OperatingSystem, SourceType} from '../../lib/models/flow';
import {isNonNull, isNull} from '../../lib/preconditions';
import {ClientPageGlobalStore} from '../../store/client_page_global_store';
import {ConfigGlobalStore} from '../../store/config_global_store';

import {ControlValues} from './form_interface';

const READABLE_SOURCE_NAME: {[key in SourceType]?: string} = {
  [SourceType.ARTIFACT_FILES]: 'Collects artifact',
  [SourceType.ARTIFACT_GROUP]: 'Collects artifact',
  [SourceType.ARTIFACT]: 'Collects artifact',
  [SourceType.COMMAND]: 'Executes command',
  [SourceType.DIRECTORY]: 'Collects directory',
  [SourceType.FILE]: 'Collects file',
  [SourceType.GREP]: 'Greps',
  [SourceType.GRR_CLIENT_ACTION]: 'Executes client action',
  [SourceType.LIST_FILES]: 'Lists files in',
  [SourceType.PATH]: 'Collects path',
  [SourceType.REGISTRY_KEY]: 'Collects Windows Registry key',
  [SourceType.REGISTRY_VALUE]: 'Collects Windows Registry value',
  [SourceType.WMI]: 'Queries WMI',
};

declare interface SampleSource {
  readonly name: string;
  readonly value: string;
}

declare interface SourceNode {
  readonly type: SourceType;
  readonly name: string;
  readonly values: ReadonlyArray<string>;
  readonly children: ReadonlyArray<SourceNode>;
}

declare interface ArtifactListEntry extends ArtifactDescriptor {
  readonly readableSources: ReadonlyMap<SourceType, ReadonlyArray<string>>;
  readonly totalSources: number;
  readonly sampleSource?: SampleSource;
  readonly availableOnClient: boolean;
  readonly searchStrings: ReadonlyArray<string>;
}

function getOrSet<K, V>(map: Map<K, V>, key: K, factory: () => V): V {
  let value = map.get(key);
  if (value === undefined) {
    value = factory();
    map.set(key, value);
  }
  return value;
}

function getReadableSources(source: ArtifactSource): ReadonlyArray<string> {
  switch (source.type) {
    case SourceType.ARTIFACT_GROUP:
    case SourceType.ARTIFACT_FILES:
      return source.names;

    case SourceType.GRR_CLIENT_ACTION:
      return [source.clientAction];

    case SourceType.COMMAND:
      return [source.cmdline];

    case SourceType.DIRECTORY:
    case SourceType.FILE:
    case SourceType.GREP:
    case SourceType.PATH:
      return source.paths;

    case SourceType.REGISTRY_KEY:
      return source.keys;

    case SourceType.REGISTRY_VALUE:
      return source.values;

    case SourceType.WMI:
      return [source.query];

    default:
      return [];
  }
}

function createListEntry(
    ad: ArtifactDescriptor,
    clientOs?: OperatingSystem|null): ArtifactListEntry {
  const readableSources = new Map<SourceType, string[]>();

  for (const source of ad.sources) {
    if (isNonNull(clientOs) && source.supportedOs.size > 0 &&
        !source.supportedOs.has(clientOs)) {
      // Skip sources that explicitly state they don't support the current OS.
      continue;
    }

    const sourceList =
        getOrSet<SourceType, string[]>(readableSources, source.type, Array);
    sourceList.push(...getReadableSources(source));
  }

  let sampleSource: SampleSource|undefined;
  for (const [type, values] of readableSources.entries()) {
    const name = READABLE_SOURCE_NAME[type];
    if (name !== undefined && values.length > 0) {
      sampleSource = {name, value: values[0]};
      break;
    }
  }

  const totalSources = Array.from(readableSources.values())
                           .reduce((acc, cur) => acc + cur.length, 0);

  const availableOnClient = isNull(clientOs) || ad.supportedOs.has(clientOs);

  const searchStrings =
      [
        ad.name,
        ad.doc ?? '',
        ...ad.supportedOs,
      ].concat(...readableSources.values())
          .map(str => str.toLowerCase());

  return {
    ...ad,
    readableSources,
    totalSources,
    sampleSource,
    availableOnClient,
    searchStrings,
  };
}

function matches(entry: ArtifactListEntry, searchString: string): boolean {
  return entry.searchStrings.some(str => str.includes(searchString));
}

function readableSourceToNodes(
    entries: Map<string, ArtifactListEntry>, type: SourceType,
    readableSources: ReadonlyArray<string>): SourceNode[] {
  if (type === SourceType.ARTIFACT || type === SourceType.ARTIFACT_FILES ||
      type === SourceType.ARTIFACT_GROUP) {
    return readableSources.map(source => ({
                                 type,
                                 name: READABLE_SOURCE_NAME[type] ?? 'Unknown',
                                 values: [source],
                                 children: artifactToNodes(entries, source),
                               }));
  } else {
    return [{
      type,
      name: READABLE_SOURCE_NAME[type] ?? 'Unknown',
      values: readableSources,
      children: [],
    }];
  }
}

function artifactToNodes(
    entries: Map<string, ArtifactListEntry>,
    artifactName: string): SourceNode[] {
  const artifact = entries.get(artifactName);
  if (artifact === undefined) {
    return [];
  } else {
    return Array.from(artifact.readableSources.entries())
        .flatMap(
            ([type, sources]) => readableSourceToNodes(entries, type, sources));
  }
}

function makeControls() {
  return {
    artifactName: new FormControl<string>('', {nonNullable: true}),
  };
}

type Controls = ReturnType<typeof makeControls>;

/** Form that configures a ArtifactCollectorFlow. */
@Component({
  selector: 'artifact-collector-flow-form',
  templateUrl: './artifact_collector_flow_form.ng.html',
  styleUrls: ['./artifact_collector_flow_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ArtifactCollectorFlowForm extends
    FlowArgumentForm<ArtifactCollectorFlowArgs, Controls> {
  readonly SourceType = SourceType;
  readonly readableSourceName = READABLE_SOURCE_NAME;

  override makeControls() {
    return makeControls();
  }

  override convertFlowArgsToFormState(flowArgs: ArtifactCollectorFlowArgs) {
    return {
      artifactName:
          flowArgs.artifactList?.[0] ?? this.controls.artifactName.defaultValue,
    };
  }

  override convertFormStateToFlowArgs(formState: ControlValues<Controls>) {
    return {
      artifactList: formState.artifactName ? [formState.artifactName] : [],
      applyParsers: false,
    };
  }

  private readonly clientOs$ = this.clientPageGlobalStore.selectedClient$.pipe(
      map(client => safeTranslateOperatingSystem(client?.knowledgeBase.os)),
      startWith(null),
      distinctUntilChanged(),
  );

  readonly artifactListEntries$ =
      combineLatest([
        this.configGlobalStore.artifactDescriptors$,
        this.clientOs$,
      ])
          .pipe(
              map(([descriptors, clientOs]) => {
                return Array.from(descriptors.values())
                    .map(ad => createListEntry(ad, clientOs));
              }),
          );


  readonly filteredArtifactDescriptors$ =
      combineLatest([
        this.artifactListEntries$,
        this.controls.artifactName.valueChanges.pipe(startWith('')),
      ])
          .pipe(
              map(([entries, searchString]) => {
                const str = searchString?.toLowerCase() ?? '';
                return entries.filter(ad => matches(ad, str));
              }),
          );

  readonly selectedArtifact$ =
      combineLatest([
        this.artifactListEntries$,
        this.controls.artifactName.valueChanges,
      ])
          .pipe(
              map(([entries, searchString]) =>
                      entries.find(ad => ad.name === searchString)),
              startWith(undefined),
          );


  readonly clientId$ = this.clientPageGlobalStore.selectedClient$.pipe(
      map(client => client?.clientId),
  );

  readonly treeControl =
      new NestedTreeControl<SourceNode>(node => [...node.children]);

  readonly dataSource = new MatTreeNestedDataSource<SourceNode>();

  constructor(
      private readonly configGlobalStore: ConfigGlobalStore,
      private readonly clientPageGlobalStore: ClientPageGlobalStore) {
    super();

    combineLatest([
      this.selectedArtifact$,
      this.artifactListEntries$.pipe(
          map((entries) => new Map(entries.map(e => [e.name, e])))),
    ])
        .pipe(takeUntil(this.ngOnDestroy.triggered$))
        .subscribe(([artifact, entries]) => {
          if (artifact === undefined) {
            this.dataSource.data = [];
          } else {
            this.dataSource.data = artifactToNodes(entries, artifact.name);
          }
        });
  }

  trackArtifactDescriptor(index: number, ad: ArtifactDescriptor) {
    return ad.name;
  }

  selectArtifact(artifactName: string) {
    this.controls.artifactName.setValue(artifactName);
  }

  printOs(artifact: ArtifactListEntry): string {
    return Array.from(artifact.supportedOs.values()).join(', ');
  }

  hasChild(index: number, node: SourceNode): boolean {
    return node.children.length > 0;
  }
}

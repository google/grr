import {NestedTreeControl} from '@angular/cdk/tree';
import {ChangeDetectionStrategy, Component, OnDestroy, OnInit, Output} from '@angular/core';
import {FormControl, FormGroup} from '@angular/forms';
import {MatTreeNestedDataSource} from '@angular/material/tree';
import {FlowArgumentForm} from '@app/components/flow_args_form/form_interface';
import {combineLatest, Subject} from 'rxjs';
import {distinctUntilChanged, map, shareReplay, startWith, takeUntil} from 'rxjs/operators';

import {ArtifactCollectorFlowArgs} from '../../lib/api/api_interfaces';
import {safeTranslateOperatingSystem} from '../../lib/api_translation/flow';
import {ArtifactDescriptor, ArtifactSource, OperatingSystem, SourceType} from '../../lib/models/flow';
import {ClientPageFacade} from '../../store/client_page_facade';
import {ConfigFacade} from '../../store/config_facade';


const ARTIFACT_NAME = 'artifactName';

const MAX_AUTOCOMPLETE_RESULTS = 50;

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
  name: string;
  value: string;
}

declare interface SourceNode {
  type: SourceType;
  name: string;
  values: ReadonlyArray<string>;
  children: SourceNode[];
}

declare interface ArtifactListEntry extends ArtifactDescriptor {
  readableSources: ReadonlyMap<SourceType, ReadonlyArray<string>>;
  totalSources: number;
  sampleSource?: SampleSource;
  availableOnClient: boolean;
  searchStrings: string[];
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
    ad: ArtifactDescriptor, clientOs?: OperatingSystem): ArtifactListEntry {
  const readableSources = new Map<SourceType, string[]>();

  for (const source of ad.sources) {
    if (clientOs !== undefined && source.supportedOs.size > 0 &&
        !source.supportedOs.has(clientOs)) {
      // Skip sources that explicitly state they don't support the current OS.
      continue;
    }

    const sourceList = getOrSet(readableSources, source.type, Array);
    getReadableSources(source).forEach(val => {
      sourceList.push(val);
    });
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

  const availableOnClient =
      clientOs === undefined || ad.supportedOs.has(clientOs);

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

/** Form that configures a ArtifactCollectorFlow. */
@Component({
  selector: 'artifact-collector-flow-form',
  templateUrl: './artifact_collector_flow_form.ng.html',
  styleUrls: ['./artifact_collector_flow_form.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ArtifactCollectorFlowForm extends
    FlowArgumentForm<ArtifactCollectorFlowArgs> implements OnInit, OnDestroy {
  readonly SourceType = SourceType;
  readonly readableSourceName = READABLE_SOURCE_NAME;

  readonly form = new FormGroup({
    [ARTIFACT_NAME]: new FormControl(),
  });

  @Output()
  readonly formValues$ = this.form.valueChanges.pipe(
      map(values => ({
            ...this.defaultFlowArgs,
            artifactList: [values[ARTIFACT_NAME]],
            applyParsers: false,
          })),
      shareReplay(1),
  );
  @Output() readonly status$ = this.form.statusChanges.pipe(shareReplay(1));

  private readonly clientOs$ = this.clientPageFacade.selectedClient$.pipe(
      map(client => safeTranslateOperatingSystem(client.knowledgeBase.os)),
      startWith(undefined),
      distinctUntilChanged(),
  );

  readonly artifactListEntries$ =
      combineLatest([
        this.configFacade.artifactDescriptors$,
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
        this.form.controls[ARTIFACT_NAME].valueChanges.pipe(startWith('')),
      ])
          .pipe(
              map(([entries, searchString]) => {
                searchString = searchString.toLowerCase();
                return entries.filter(ad => matches(ad, searchString))
                    .slice(0, MAX_AUTOCOMPLETE_RESULTS);
              }),
          );

  readonly selectedArtifact$ =
      combineLatest([
        this.artifactListEntries$,
        this.form.controls[ARTIFACT_NAME].valueChanges,
      ])
          .pipe(
              map(([entries, searchString]) =>
                      entries.find(ad => ad.name === searchString)),
              startWith(undefined),
          );


  readonly clientId$ = this.clientPageFacade.selectedClient$.pipe(
      map(client => client?.clientId),
  );

  readonly treeControl =
      new NestedTreeControl<SourceNode>(node => node.children);

  readonly dataSource = new MatTreeNestedDataSource<SourceNode>();

  readonly unsubscribe$ = new Subject<void>();

  constructor(
      private readonly configFacade: ConfigFacade,
      private readonly clientPageFacade: ClientPageFacade) {
    super();
  }

  ngOnInit() {
    combineLatest([
      this.selectedArtifact$,
      this.artifactListEntries$.pipe(
          map((entries) => new Map(entries.map(e => [e.name, e])))),
    ])
        .pipe(takeUntil(this.unsubscribe$))
        .subscribe(([artifact, entries]) => {
          if (artifact === undefined) {
            this.dataSource.data = [];
          } else {
            this.dataSource.data = artifactToNodes(entries, artifact.name);
          }
        });

    this.form.patchValue({
      [ARTIFACT_NAME]: this.defaultFlowArgs.artifactList?.[0] ?? '',
    });
  }

  trackArtifactDescriptor(ad: ArtifactDescriptor) {
    return ad.name;
  }

  selectArtifact(artifactName: string) {
    this.form.patchValue({
      [ARTIFACT_NAME]: artifactName,
    });
  }

  printOs(artifact: ArtifactListEntry): string {
    return Array.from(artifact.supportedOs.values()).join(', ');
  }

  ngOnDestroy() {
    this.unsubscribe$.next();
    this.unsubscribe$.complete();
  }

  hasChild(index: number, node: SourceNode): boolean {
    return node.children.length > 0;
  }
}

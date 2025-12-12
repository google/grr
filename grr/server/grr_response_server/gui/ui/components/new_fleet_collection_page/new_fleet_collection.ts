import {CommonModule} from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  signal,
  ViewChild,
} from '@angular/core';
import {toSignal} from '@angular/core/rxjs-interop';
import {FormControl, FormsModule, ReactiveFormsModule} from '@angular/forms';
import {MatButtonModule} from '@angular/material/button';
import {MatChipsModule} from '@angular/material/chips';
import {MatFormFieldModule} from '@angular/material/form-field';
import {MatIconModule} from '@angular/material/icon';
import {MatInputModule} from '@angular/material/input';
import {MatTooltipModule} from '@angular/material/tooltip';
import {Title} from '@angular/platform-browser';
import {ActivatedRoute, Router, RouterModule} from '@angular/router';

import {
  ApiFlowReference,
  ApiHuntReference,
  ForemanClientRuleSet,
  ForemanClientRuleSetMatchMode,
  ForemanClientRuleType,
} from '../../lib/api/api_interfaces';
import {FLOW_DETAILS_BY_TYPE} from '../../lib/data/flows/flow_definitions';
import {SafetyLimits} from '../../lib/models/hunt';
import {OutputPlugin} from '../../lib/models/output_plugin';
import {GlobalStore} from '../../store/global_store';
import {NewFleetCollectionStore} from '../../store/new_fleet_collection_store';
import {
  CollapsibleContainer,
  CollapsibleContent,
  CollapsibleTitle,
} from '../shared/collapsible_container';
import {ErrorMessage} from '../shared/error_message';
import {FleetCollectionStateChip} from '../shared/fleet_collection_state_chip';
import {ClientsForm} from '../shared/fleet_collections/clients_form';
import {OutputPluginsForm} from '../shared/fleet_collections/output_plugins_form';
import {RolloutForm} from '../shared/fleet_collections/rollout_form';
import {FlowArgsForm} from '../shared/flow_args_form/flow_args_form';
import {FlowStateIcon} from '../shared/flow_state_icon';
import {FormErrors, requiredInput} from '../shared/form/form_validation';

/**
 * Provides the fleet collection creation page.
 * Reads clientId, flowId or fleetCollectionId from the query params.
 */
@Component({
  templateUrl: './new_fleet_collection.ng.html',
  styleUrls: ['./new_fleet_collection.scss'],
  imports: [
    ClientsForm,
    CollapsibleContainer,
    CollapsibleTitle,
    CollapsibleContent,
    CommonModule,
    ErrorMessage,
    FleetCollectionStateChip,
    FlowArgsForm,
    FlowStateIcon,
    FormErrors,
    FormsModule,
    MatButtonModule,
    MatChipsModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatTooltipModule,
    OutputPluginsForm,
    ReactiveFormsModule,
    RolloutForm,
    RouterModule,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [NewFleetCollectionStore],
})
export class NewFleetCollection {
  protected readonly newFleetCollectionStore = inject(NewFleetCollectionStore);
  protected readonly globalStore = inject(GlobalStore);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  @ViewChild(ClientsForm, {static: false}) clientsForm!: ClientsForm;
  @ViewChild(RolloutForm, {static: false}) rolloutForm!: RolloutForm;
  @ViewChild(OutputPluginsForm, {static: false})
  outputPluginsForm!: OutputPluginsForm;

  private readonly queryParams = toSignal(this.route.queryParams);

  protected createdFleetCollection = false;

  protected controls = {
    title: new FormControl('', {
      nonNullable: true,
      validators: [requiredInput()],
    }),
  };

  protected initialSafetyLimits = signal<SafetyLimits | undefined>(undefined);
  protected initialOutputPlugins = signal<readonly OutputPlugin[] | undefined>(
    undefined,
  );
  protected initialClientRules = signal<ForemanClientRuleSet | undefined>(
    undefined,
  );

  private readonly defaultClientRules = computed<ForemanClientRuleSet>(() => {
    return {
      matchMode: ForemanClientRuleSetMatchMode.MATCH_ALL,
      rules: [
        {
          ruleType: ForemanClientRuleType.OS,
          os: {osWindows: false, osLinux: false, osDarwin: false},
        },
        ...(this.globalStore.uiConfig()?.defaultHuntRunnerArgs?.clientRuleSet
          ?.rules ?? []),
      ],
    };
  });

  protected readonly hasAccessToFlowType = computed<boolean | undefined>(() => {
    const adminUser = this.globalStore.currentUser()?.isAdmin;

    const flowType = this.newFleetCollectionStore.flowType();
    const flowIsRestricted = flowType
      ? FLOW_DETAILS_BY_TYPE.get(flowType)?.restricted
      : undefined;

    // Check explicitly for `false` as an undefined value means that the
    // information is not available, e.g. not yet loaded.
    if (adminUser || flowIsRestricted === false) {
      return true;
    }
    if (adminUser === false && flowIsRestricted) {
      return false;
    }
    return undefined;
  });

  protected readonly friendlyFlowName = computed<string | undefined>(() => {
    const flowType = this.newFleetCollectionStore.flowType();
    if (!flowType) {
      return undefined;
    }
    return FLOW_DETAILS_BY_TYPE.get(flowType)?.friendlyName;
  });

  constructor() {
    inject(Title).setTitle('GRR | New Fleet Collection');

    // Already fetch the output plugin descriptors when the page is loaded. This
    // will make the output plugin form initialization faster.
    this.globalStore.fetchOutputPluginDescriptors();

    effect(() => {
      const clientId = this.queryParams()?.['clientId'];
      const flowId = this.queryParams()?.['flowId'];
      const fleetCollectionId = this.queryParams()?.['fleetCollectionId'];

      let fleetCollectionRef: ApiHuntReference | undefined;
      let flowRef: ApiFlowReference | undefined;

      if (clientId && flowId) {
        flowRef = {clientId, flowId};
      } else if (fleetCollectionId) {
        fleetCollectionRef = {huntId: fleetCollectionId};
      }
      if (fleetCollectionRef || flowRef) {
        this.newFleetCollectionStore.initialize(fleetCollectionRef, flowRef);
      }
    });

    effect(() => {
      if (this.newFleetCollectionStore.originalFlowRef()) {
        const uiConfig = this.globalStore.uiConfig();
        this.initialSafetyLimits.set(uiConfig?.safetyLimits);
        this.initialOutputPlugins.set(uiConfig?.defaultOutputPlugins ?? []);
        this.initialClientRules.set(this.defaultClientRules());
      } else if (this.newFleetCollectionStore.originalFleetCollectionRef()) {
        const originalFleetCollection =
          this.newFleetCollectionStore.originalFleetCollection();
        this.initialSafetyLimits.set(originalFleetCollection?.safetyLimits);
        this.initialOutputPlugins.set(originalFleetCollection?.outputPlugins);
        this.initialClientRules.set(originalFleetCollection?.clientRuleSet);

        this.controls.title.setValue(
          (originalFleetCollection?.description ?? '') + ' - (copy)',
        );
      }
    });

    effect(() => {
      // As soon as the new fleet collection is created we redirect to the
      // fleet collection results page.
      // TODO: Check approval and only then redirect to the
      // approval page.
      if (this.newFleetCollectionStore.newFleetCollection() !== undefined) {
        this.router.navigate([
          '/fleet-collections',
          this.newFleetCollectionStore.newFleetCollection()!.huntId,
          'approvals',
        ]);
      }
    });
  }

  createFleetCollection() {
    this.newFleetCollectionStore.createFleetCollection(
      this.controls.title.value,
      this.rolloutForm.getFormState(),
      this.clientsForm.getFormState(),
      this.outputPluginsForm.getFormState(),
    );
    this.createdFleetCollection = true;
  }
}

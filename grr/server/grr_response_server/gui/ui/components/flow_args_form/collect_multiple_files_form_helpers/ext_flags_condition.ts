import {ChangeDetectionStrategy, Component, EventEmitter, OnInit, Output} from '@angular/core';
import {ControlContainer, FormControl, FormGroup} from '@angular/forms';
import {distinctUntilChanged, map, startWith} from 'rxjs/operators';

import {safeTranslateOperatingSystem} from '../../../lib/api_translation/flow';
import {OperatingSystem} from '../../../lib/models/flow';
import {Flag, LINUX_FLAGS_ORDERED, OSX_FLAGS} from '../../../lib/models/os_extended_flags';
import {ClientPageGlobalStore} from '../../../store/client_page_global_store';

/** Different possible statuses of OS file flags */
export enum MaskCondition {
  IGNORE,
  REQUIRE_SET,
  REQUIRE_UNSET,
}

interface FlagWithCondition extends Flag {
  condition: MaskCondition;
}

const TOGGLE_ORDER: {[key in MaskCondition]: MaskCondition} = {
  [MaskCondition.IGNORE]: MaskCondition.REQUIRE_SET,
  [MaskCondition.REQUIRE_SET]: MaskCondition.REQUIRE_UNSET,
  [MaskCondition.REQUIRE_UNSET]: MaskCondition.IGNORE,
};

function makeControls() {
  return new FormGroup({
    linuxBitsSet: new FormControl(0, {nonNullable: true}),
    linuxBitsUnset: new FormControl(0, {nonNullable: true}),
    osxBitsSet: new FormControl(0, {nonNullable: true}),
    osxBitsUnset: new FormControl(0, {nonNullable: true}),
  });
}

type Controls = ReturnType<typeof makeControls>;

/** Form that configures an ext flags condition. */
@Component({
  selector: 'ext-flags-condition',
  templateUrl: './ext_flags_condition.ng.html',
  styleUrls: ['./ext_flags_condition.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ExtFlagsCondition implements OnInit {
  constructor(
      private readonly controlContainer: ControlContainer,
      private readonly clientPageGlobalStore: ClientPageGlobalStore) {}

  @Output() readonly conditionRemoved = new EventEmitter<void>();

  readonly LINUX_FLAGS = LINUX_FLAGS_ORDERED;
  readonly OSX_FLAGS = OSX_FLAGS;
  readonly ICONS = {
    [MaskCondition.IGNORE]: 'remove',
    [MaskCondition.REQUIRE_SET]: 'check',
    [MaskCondition.REQUIRE_UNSET]: 'block',
  };

  readonly linuxFlags: readonly FlagWithCondition[] = this.LINUX_FLAGS.map(
      flag => ({...flag, condition: MaskCondition.IGNORE}));

  readonly osxFlags: readonly FlagWithCondition[] =
      this.OSX_FLAGS.map(flag => ({...flag, condition: MaskCondition.IGNORE}));

  private readonly os$ = this.clientPageGlobalStore.selectedClient$.pipe(
      map(client => safeTranslateOperatingSystem(client?.knowledgeBase.os)),
      startWith(null),
      distinctUntilChanged(),
  );

  // Iff the client's OS is Linux or macOS, show only the specific form. For
  // all other clients (Windows, unknown OS), show both forms as fallback.
  // In the future, it might make sense to hide the forms for other clients
  // or always show unapplicable forms in a collapsed state.
  readonly showLinux$ = this.os$.pipe(map(os => os !== OperatingSystem.DARWIN));
  readonly showOsx$ = this.os$.pipe(map(os => os !== OperatingSystem.LINUX));

  get formGroup(): Controls {
    return this.controlContainer.control as Controls;
  }

  static createFormGroup() {
    return makeControls();
  }

  ngOnInit() {
    this.updateFlagConditions(this.formGroup.value);
  }

  toggleFlag(flag: FlagWithCondition) {
    flag.condition = TOGGLE_ORDER[flag.condition];

    this.formGroup.setValue({
      linuxBitsSet: computeMask(this.linuxFlags, MaskCondition.REQUIRE_SET),
      linuxBitsUnset: computeMask(this.linuxFlags, MaskCondition.REQUIRE_UNSET),
      osxBitsSet: computeMask(this.osxFlags, MaskCondition.REQUIRE_SET),
      osxBitsUnset: computeMask(this.osxFlags, MaskCondition.REQUIRE_UNSET),
    });
  }

  tooltip(flag: FlagWithCondition) {
    let name = flag.name;

    if (flag.description) {
      name += ` (${flag.description})`;
    }

    switch (flag.condition) {
      case MaskCondition.REQUIRE_SET:
        return `Only include files with flag ${name}`;
      case MaskCondition.REQUIRE_UNSET:
        return `Exclude files with flag ${name}`;
      default:
        return `Ignore flag ${name}`;
    }
  }

  private updateFlagConditions(mask: Controls['value']): void {
    // Set the condition as "REQUIRE_SET" for checked Linux flag elements
    updateFlagConditionsForOS(
        this.linuxFlags, mask.linuxBitsSet || 0, MaskCondition.REQUIRE_SET);

    // Set the condition as "REQUIRE_UNSET" for unchecked Linux flag elements
    updateFlagConditionsForOS(
        this.linuxFlags, mask.linuxBitsUnset || 0, MaskCondition.REQUIRE_UNSET);

    // Set the condition as "REQUIRE_SET" for checked macOS flag elements
    updateFlagConditionsForOS(
        this.osxFlags, mask.osxBitsSet || 0, MaskCondition.REQUIRE_SET);

    // Set the condition as "REQUIRE_UNSET" for unchecked macOS flag elements
    updateFlagConditionsForOS(
        this.osxFlags, mask.osxBitsUnset || 0, MaskCondition.REQUIRE_UNSET);
  }
}

/**
 * Mutates @param flags to update the "condition" property for each element if
 * if any of the bits collide with the mask.
 */
export function updateFlagConditionsForOS(
    flags: readonly FlagWithCondition[],
    mask: number,
    condition: MaskCondition,
    ): void {
  flags.forEach(flag => {
    const maskBitCollision = flag.mask & mask;

    if (maskBitCollision > 0) {
      flag.condition = condition;
    }
  });
}

function computeMask(
    flags: readonly FlagWithCondition[], value: MaskCondition) {
  return flags.filter(f => f.condition === value)
      .reduce((acc, flag) => acc | flag.mask, 0);
}

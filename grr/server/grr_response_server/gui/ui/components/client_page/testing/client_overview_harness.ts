import {ComponentHarness} from '@angular/cdk/testing';
import {MatButtonHarness} from '@angular/material/button/testing';
import {MatChipHarness} from '@angular/material/chips/testing';
import {ApprovalChipHarness} from '../../shared/testing/approval_chip_harness';
import {ErrorMessageHarness} from '../../shared/testing/error_message_harness';
import {OnlineChipHarness} from '../../shared/testing/online_chip_harness';

/** Harness for the ClientOverview component. */
export class ClientOverviewHarness extends ComponentHarness {
  static hostSelector = 'client-overview';

  private readonly clientName = this.locatorFor('.client-name');
  private readonly id = this.locatorFor('.id');

  private readonly onlineChip = this.locatorForOptional(OnlineChipHarness);
  private readonly approvalChip = this.locatorForOptional(ApprovalChipHarness);

  private readonly infoSection = this.locatorForOptional('.info');
  private readonly fqdn = this.locatorFor('.fqdn');
  private readonly os = this.locatorFor('.os');
  private readonly users = this.locatorFor('.users');
  private readonly grrAgent = this.locatorFor('.grr-agent');
  private readonly grrAgentBuild = this.locatorFor('.grr-agent-build');
  private readonly rrgAgent = this.locatorFor('.rrg-agent');
  private readonly firstSeen = this.locatorFor('.first-seen');
  private readonly lastSeen = this.locatorFor('.last-seen');
  private readonly lastBootedAt = this.locatorFor('.last-boot');

  private readonly labelChips = this.locatorForAll(
    MatChipHarness.with({selector: '.label-chip'}),
  );
  private readonly addLabelButton = this.locatorFor(
    MatButtonHarness.with({selector: '.add_label'}),
  );

  readonly errorMessages = this.locatorForAll(ErrorMessageHarness);

  async getClientNameText(): Promise<string> {
    return (await this.clientName()).text();
  }

  async getIdText(): Promise<string> {
    return (await this.id()).text();
  }

  async getFqdnText(): Promise<string> {
    return (await this.fqdn()).text();
  }

  async getOsText(): Promise<string> {
    return (await this.os()).text();
  }

  async getUsersText(): Promise<string> {
    return (await this.users()).text();
  }

  async getGRRAgentText(): Promise<string> {
    return (await this.grrAgent()).text();
  }

  async getGRRAgentBuildText(): Promise<string> {
    return (await this.grrAgentBuild()).text();
  }

  async getRRGAgentText(): Promise<string> {
    return (await this.rrgAgent()).text();
  }

  async getFirstSeenText(): Promise<string> {
    return (await this.firstSeen()).text();
  }

  async getLastSeenText(): Promise<string> {
    return (await this.lastSeen()).text();
  }

  async getLastBootedAtText(): Promise<string> {
    return (await this.lastBootedAt()).text();
  }

  async getLabelChip(label: string): Promise<MatChipHarness> {
    const chip = await this.locatorFor(MatChipHarness.with({text: label}))();
    if (!chip) {
      throw new Error(`Chip with label '${label}' not found`);
    }
    return chip;
  }

  async getAllLabelChipTexts(): Promise<string[]> {
    const chips = await this.labelChips();
    return Promise.all(chips.map((chip) => chip.getText()));
  }

  async isAddLabelButtonVisible(): Promise<boolean> {
    return !!(await this.addLabelButton());
  }

  async getOnlineChipHarness(): Promise<OnlineChipHarness> {
    const onlineChip = await this.onlineChip();
    if (!onlineChip) {
      throw new Error('Online chip not found');
    }
    return onlineChip;
  }

  async getApprovalChipHarness(): Promise<ApprovalChipHarness> {
    const approvalChip = await this.approvalChip();
    if (!approvalChip) {
      throw new Error('Approval chip not found');
    }
    return approvalChip;
  }

  async isApprovalChipVisible(): Promise<boolean> {
    return !!(await this.approvalChip());
  }

  async hasInfoSection(): Promise<boolean> {
    return !!(await this.infoSection());
  }
}

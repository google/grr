import {ComponentHarness} from '@angular/cdk/testing';

/** Harness for the ExecuteResponseResults component. */
export class ExecuteResponseResultsHarness extends ComponentHarness {
  static hostSelector = 'execute-response-results';

  readonly clientIds = this.locatorForAll('.client-id');
  readonly results = this.locatorForAll('.result');

  async getCmd(index: number) {
    const cmd = this.locatorFor(`.cmd_${index}`);
    return cmd();
  }

  async getExitStatus(index: number) {
    const exitStatus = this.locatorFor(`.exit-status_${index}`);
    return exitStatus();
  }

  async getStdout(index: number) {
    const stdout = this.locatorFor(`.stdout_${index}`);
    return stdout();
  }

  async getStderr(index: number) {
    const stderr = this.locatorForOptional(`.stderr_${index}`);
    if (stderr == null) {
      throw new Error('Stderr not found');
    }
    return stderr();
  }

  async numResults() {
    const results = await this.results();
    return results.length;
  }
}

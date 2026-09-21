import fs from "node:fs/promises";
import path from "node:path";
import type { BundleRecord, ConditionId, LongRunRecord, MachineInfo, RunRecord } from "./types";

function conditionFileName(condition: ConditionId): string {
  return `${condition.toLowerCase().replace(/[^a-z0-9-]/g, "-")}.json`;
}

// 条件ごとに JSON ファイルを持ち、rep が終わるたびに書き直す。
// 途中で落ちても、それまでに済んだ条件・rep の結果は results/*.json に残る。
export class ResultsStore {
  private readonly outDir: string;
  private readonly perCondition = new Map<ConditionId, RunRecord[]>();
  private bundleRecord: BundleRecord | null = null;
  private longRecords: LongRunRecord[] = [];

  constructor(outDir: string) {
    this.outDir = outDir;
  }

  async init(): Promise<void> {
    await fs.mkdir(this.outDir, { recursive: true });
  }

  async setBundleRecord(record: BundleRecord): Promise<void> {
    this.bundleRecord = record;
    await this.writeJson("bundle.json", record);
  }

  async addRun(record: RunRecord): Promise<void> {
    const existing = this.perCondition.get(record.condition) ?? [];
    existing.push(record);
    this.perCondition.set(record.condition, existing);
    await this.writeJson(conditionFileName(record.condition), {
      condition: record.condition,
      runs: existing,
    });
  }

  async setLongRecords(records: LongRunRecord[]): Promise<void> {
    this.longRecords = records;
    await this.writeJson("long.json", { runs: records });
  }

  async writeMachineInfo(machineInfo: MachineInfo): Promise<void> {
    await this.writeJson("machine.json", machineInfo);
  }

  getAllRuns(): RunRecord[] {
    return [...this.perCondition.values()].flat();
  }

  getBundleRecord(): BundleRecord | null {
    return this.bundleRecord;
  }

  getLongRecords(): LongRunRecord[] {
    return this.longRecords;
  }

  async writeSummaryMarkdown(markdown: string): Promise<void> {
    await fs.writeFile(path.join(this.outDir, "summary.md"), markdown, "utf8");
  }

  private async writeJson(fileName: string, data: unknown): Promise<void> {
    await fs.writeFile(path.join(this.outDir, fileName), JSON.stringify(data, null, 2), "utf8");
  }
}

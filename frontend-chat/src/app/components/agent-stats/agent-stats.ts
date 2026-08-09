import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { AgentStats as AgentStatsModel } from '../../models/agent.model';

@Component({
  selector: 'app-agent-stats',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './agent-stats.html',
  styleUrl: './agent-stats.scss',
})
export class AgentStats {
  @Input() stats!: AgentStatsModel;

  get rateEntries(): [string, number][] {
    if (!this.stats?.commission_by_rate) {
      return [];
    }

    return (Object.entries(this.stats.commission_by_rate) as [string, number][])
      .sort((a, b) => b[1] - a[1]);
  }

  getBarWidth(count: number): number {
    const entries = this.rateEntries;
    const max = Math.max(...entries.map(x => x[1]), 1);
    return (count / max) * 100;
  }
}
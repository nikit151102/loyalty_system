import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { Message, ChatButton } from '../../models/message.model';
import { AddClient } from '../add-client/add-client';
import { AddPurchase } from '../add-purchase/add-purchase';
import { AgentClients } from '../agent-clients/agent-clients';
import { ReferralSection } from '../referral-section/referral-section';
import { QrDisplay } from '../qr-display/qr-display';

@Component({
  selector: 'app-message-bubble',
  imports: [CommonModule, AgentClients, AddClient, AddPurchase, ReferralSection, QrDisplay],
  templateUrl: './message-bubble.html',
  styleUrl: './message-bubble.scss',
})
export class MessageBubble {
  @Input() message!: Message;
  @Output() buttonClick = new EventEmitter<{ action: string; data: any }>();

  formatText(text: string): string {
    return text
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/`(.+?)`/g, '<code>$1</code>');
  }

  getBtnClass(btn: ChatButton): string {
    const classes = ['btn'];
    if (btn.variant) classes.push(`btn-${btn.variant}`);
    return classes.join(' ');
    
  }
}

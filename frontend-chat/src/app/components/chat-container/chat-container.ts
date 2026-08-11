import { CommonModule } from '@angular/common';
import { AfterViewInit, Component, ElementRef, inject, ViewChild, OnDestroy } from '@angular/core';
import { chatAnimations } from '../../animations/chat.animations';
import { Chat } from '../../services/chat';
import { PhoneInput } from '../phone-input/phone-input';
import { TypingIndicator } from '../typing-indicator/typing-indicator';
import { MessageBubble } from '../message-bubble/message-bubble';
import { EmailInput } from '../email-input';
import { TextInput } from '../text-input/text-input';

@Component({
  selector: 'app-chat-container',
  imports: [CommonModule, MessageBubble, TypingIndicator, PhoneInput, EmailInput, TextInput],
  animations: [chatAnimations.messageEnter],
  templateUrl: './chat-container.html',
  styleUrl: './chat-container.scss',
})
export class ChatContainer implements AfterViewInit, OnDestroy {
  chat = inject(Chat);
  config = { BOT_NAME: 'Программа лояльности Пакетон.рф', BOT_AVATAR: '' };

  @ViewChild('messagesContainer') messagesContainer!: ElementRef;
  private mutationObserver: MutationObserver | null = null;

  ngAfterViewInit(): void {
    if (this.messagesContainer?.nativeElement) {
      this.mutationObserver = new MutationObserver(() => {
        requestAnimationFrame(() => {
          setTimeout(() => {
            this.scrollToBottom();
          }, 150); 
        });
      });

      this.mutationObserver.observe(this.messagesContainer.nativeElement, {
        childList: true,
        subtree: true
      });
      
      this.scrollToBottom();
    }
  }

  ngOnDestroy(): void {
    if (this.mutationObserver) {
      this.mutationObserver.disconnect();
    }
  }

  private scrollToBottom(): void {
    if (this.messagesContainer?.nativeElement) {
      const container = this.messagesContainer.nativeElement;
      container.scrollTo({
        top: container.scrollHeight,
        behavior: 'auto'
      });
    }
  }

  onPhoneSubmit(phone: string): void {
    this.chat.submitPhone(phone);
  }

  onRegStepSubmit(step: number, value: string): void {
    this.chat.submitRegStep(step, value);
  }

  onClientStepSubmit(step: number, value: string): void {
    this.chat.submitClientStep(step, value);
  }

  onButtonClick(action: string, data: any): void {
    if (action === 'back_to_menu') {
      this.chat.handleBackToMenu();
    } else {
      this.chat.handleButtonAction(action, data);
    }
  }
}
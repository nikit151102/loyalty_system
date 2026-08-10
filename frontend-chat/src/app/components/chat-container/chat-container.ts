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
  config = { BOT_NAME: 'Макс-Бот', BOT_AVATAR: '🤖' };

  @ViewChild('messagesContainer') messagesContainer!: ElementRef;
  
  // Используем MutationObserver вместо ResizeObserver
  private mutationObserver: MutationObserver | null = null;

  ngAfterViewInit(): void {
    if (this.messagesContainer?.nativeElement) {
      this.mutationObserver = new MutationObserver(() => {
        // requestAnimationFrame гарантирует, что браузер успел добавить узлы в DOM
        requestAnimationFrame(() => {
          // Небольшая задержка критически важна, чтобы дождаться завершения 
          // CSS-анимации (chatAnimations.messageEnter). 
          // Если анимация длится 300мс, поставьте здесь 300 или 350.
          setTimeout(() => {
            this.scrollToBottom();
          }, 150); 
        });
      });

      // Следим за добавлением/удалением дочерних элементов и изменениями внутри них
      this.mutationObserver.observe(this.messagesContainer.nativeElement, {
        childList: true,
        subtree: true
      });
      
      // Скроллим вниз при первой инициализации
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
      
      // Опционально: раскомментируйте эти строки, если хотите, чтобы чат 
      // НЕ прыгал вниз, когда пользователь вручную прокрутил вверх для чтения истории
      /*
      const threshold = 100;
      const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < threshold;
      if (!isNearBottom && container.scrollTop > 0) {
        return; // Не скроллим, если пользователь читает старые сообщения
      }
      */

      container.scrollTo({
        top: container.scrollHeight,
        behavior: 'auto' // 'auto' надежнее при частых обновлениях, чем 'smooth'
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
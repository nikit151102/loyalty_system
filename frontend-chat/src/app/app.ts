import { Component, signal } from '@angular/core';
import { Toast } from './components/toast/toast';
import { ChatContainer } from './components/chat-container/chat-container';

@Component({
  selector: 'app-root',
  imports: [Toast, ChatContainer],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
  protected readonly title = signal('frontend-chat');
}

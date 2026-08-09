import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ChatContainer } from './chat-container';

describe('ChatContainer', () => {
  let component: ChatContainer;
  let fixture: ComponentFixture<ChatContainer>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ChatContainer],
    }).compileComponents();

    fixture = TestBed.createComponent(ChatContainer);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

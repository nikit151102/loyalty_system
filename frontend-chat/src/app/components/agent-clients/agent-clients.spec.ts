import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AgentClients } from './agent-clients';

describe('AgentClients', () => {
  let component: AgentClients;
  let fixture: ComponentFixture<AgentClients>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AgentClients],
    }).compileComponents();

    fixture = TestBed.createComponent(AgentClients);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

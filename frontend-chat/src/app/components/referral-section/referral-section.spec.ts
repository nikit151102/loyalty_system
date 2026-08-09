import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ReferralSection } from './referral-section';

describe('ReferralSection', () => {
  let component: ReferralSection;
  let fixture: ComponentFixture<ReferralSection>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ReferralSection],
    }).compileComponents();

    fixture = TestBed.createComponent(ReferralSection);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AddPurchase } from './add-purchase';

describe('AddPurchase', () => {
  let component: AddPurchase;
  let fixture: ComponentFixture<AddPurchase>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AddPurchase],
    }).compileComponents();

    fixture = TestBed.createComponent(AddPurchase);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});

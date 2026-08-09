import { trigger, transition, style, animate, query, stagger } from '@angular/animations';

export const chatAnimations = {
    messageEnter: trigger('messageEnter', [
        transition(':enter', [
            style({ opacity: 0, transform: 'translateY(20px) scale(0.95)' }),
            animate('350ms cubic-bezier(0.4, 0, 0.2, 1)',
                style({ opacity: 1, transform: 'translateY(0) scale(1)' })
            )
        ])
    ]),

    menuEnter: trigger('menuEnter', [
        transition(':enter', [
            style({ opacity: 0, transform: 'translateY(30px)' }),
            animate('400ms cubic-bezier(0.4, 0, 0.2, 1)',
                style({ opacity: 1, transform: 'translateY(0)' })
            )
        ])
    ]),

    listStagger: trigger('listStagger', [
        transition('* => *', [
            query(':enter', [
                style({ opacity: 0, transform: 'translateY(10px)' }),
                stagger(60, [
                    animate('300ms ease-out',
                        style({ opacity: 1, transform: 'translateY(0)' })
                    )
                ])
            ], { optional: true })
        ])
    ]),

    fadeSlide: trigger('fadeSlide', [
        transition(':enter', [
            style({ opacity: 0, transform: 'translateX(-20px)' }),
            animate('300ms ease-out',
                style({ opacity: 1, transform: 'translateX(0)' })
            )
        ]),
        transition(':leave', [
            animate('200ms ease-in',
                style({ opacity: 0, transform: 'translateX(20px)' })
            )
        ])
    ])
};
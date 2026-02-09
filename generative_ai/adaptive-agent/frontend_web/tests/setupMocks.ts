import { vi } from 'vitest'

// --- FIX for MSW + JSDOM localStorage ---
const localStorageMock = (() => {
    let store: Record<string, string> = {}

    return {
        getItem: vi.fn((key: string) => store[key] ?? null),
        setItem: vi.fn((key: string, value: string) => {
            store[key] = value.toString()
        }),
        removeItem: vi.fn((key: string) => {
            delete store[key]
        }),
        clear: vi.fn(() => {
            store = {}
        }),
    }
})()

Object.defineProperty(window, 'localStorage', {
    value: localStorageMock,
    writable: true,
})

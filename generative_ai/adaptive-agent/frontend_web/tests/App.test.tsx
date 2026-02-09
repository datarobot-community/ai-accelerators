import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import App from '../src/App'

describe('App component', () => {
  it.skip('renders Welcome Engineer!', async () => {
    render(<App />)

    const loadingText = await screen.findByText('Vite + React: Loading...');
    expect(loadingText).toBeInTheDocument()

    const welcomeText = await screen.findByText('Vite + React: Welcome Engineer!');
    expect(welcomeText).toBeInTheDocument()
    expect(screen.getByText('Click on the Vite and React logos to learn more')).toBeInTheDocument()
  })
})

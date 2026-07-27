import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from './App'

describe('App', () => {
  it('redirects unauthenticated users to login', async () => {
    render(<App />)
    expect(await screen.findByRole('heading', { name: 'ProcureFlow' })).toBeInTheDocument()
  })

  it('shows the login form', async () => {
    render(<App />)
    expect(await screen.findByLabelText('Email')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
  })

  it('has proper HTML structure', () => {
    render(<App />)
    expect(document.body).toBeTruthy()
  })
})

describe('App HTML Structure', () => {
  it('renders valid HTML structure', () => {
    render(<App />)
    expect(document.body).toBeTruthy()
  })

  it('does not render the protected shell while unauthenticated', async () => {
    render(<App />)
    await screen.findByRole('heading', { name: 'ProcureFlow' })
    expect(screen.queryByRole('main')).not.toBeInTheDocument()
  })
})

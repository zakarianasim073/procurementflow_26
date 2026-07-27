import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import { Skeleton } from './Skeleton'

describe('Skeleton Component', () => {
  it('renders skeleton element', () => {
    render(<Skeleton />)
    const skeleton = document.querySelector('.animate-pulse')
    expect(skeleton).toBeInTheDocument()
    expect(skeleton).toHaveClass('animate-pulse')
  })

  it('applies custom className', () => {
    render(<Skeleton className="custom-class" />)
    const skeleton = document.querySelector('.custom-class')
    expect(skeleton).toBeInTheDocument()
    expect(skeleton).toHaveClass('custom-class')
  })

  it('applies custom styles via style prop', () => {
    render(<Skeleton style={{ width: '100px', height: '20px' }} />)
    const skeleton = document.querySelector('[style*="100px"]')
    expect(skeleton).toBeInTheDocument()
  })

  it('renders multiple lines when lines > 1', () => {
    render(<Skeleton lines={3} />)
    const container = document.querySelector('.space-y-2')
    expect(container).toBeInTheDocument()
    const lines = container?.querySelectorAll(':scope > div')
    expect(lines?.length).toBe(3)
  })

  it('applies variant styles correctly', () => {
    const { rerender } = render(<Skeleton variant="text" />)
    expect(document.querySelector('.rounded')).toBeInTheDocument()
    
    rerender(<Skeleton variant="circular" />)
    expect(document.querySelector('.rounded-full')).toBeInTheDocument()
    
    rerender(<Skeleton variant="rectangular" />)
    expect(document.querySelector(':not(.rounded)')).toBeInTheDocument()
    
    rerender(<Skeleton variant="rounded" />)
    expect(document.querySelector('.rounded-xl')).toBeInTheDocument()
  })

  it('passes through additional props', () => {
    render(<Skeleton id="test-skeleton" data-test="custom" />)
    const skeleton = document.getElementById('test-skeleton')
    expect(skeleton).toBeInTheDocument()
    expect(skeleton).toHaveAttribute('data-test', 'custom')
  })

  it('has correct base classes', () => {
    render(<Skeleton />)
    const skeleton = document.querySelector('.animate-pulse')
    expect(skeleton).toBeInTheDocument()
    expect(skeleton).toHaveClass('bg-gray-200')
  })

  it('applies width and height correctly', () => {
    render(<Skeleton width="200px" height="40px" />)
    const skeleton = document.querySelector('[style*="200px"]')
    expect(skeleton).toBeInTheDocument()
  })
})
# VirtualList Component Contract

**Module:** `shared/ui/VirtualList`
**Layer:** shared
**Version:** 1.0.0
**Status:** Draft

## Purpose
High-performance scrolling container that renders only visible items, enabling smooth display of 100K+ rows (tender lists, award histories, contractor directories).

## Props
```typescript
interface VirtualListProps<T> {
  items: T[];
  itemHeight: number | ((index: number, item: T) => number);
  renderItem: (props: { item: T; index: number; style: CSSProperties }) => ReactNode;
  overscan?: number;
  onEndReached?: () => void;
  onEndReachedThreshold?: number;
  onScroll?: (scrollTop: number, scrollDirection: 'forward' | 'backward') => void;
  scrollElement?: HTMLElement;
  height: number;
  width?: number | string;
  className?: string;
  testId?: string;
  loading?: boolean;
  loadingComponent?: ReactNode;
  emptyComponent?: ReactNode;
  headerComponent?: ReactNode;
  footerComponent?: ReactNode;
}
```

## Slots
- `header` — Sticky header above virtual area
- `footer` — Footer below virtual area
- `loading` — Loading indicator for infinite scroll
- `empty` — Empty state when no items

## State
```typescript
interface VirtualListState {
  scrollTop: number;
  scrollDirection: 'forward' | 'backward';
  isScrolling: boolean;
  measuredItems: Map<number, number>; // index → measured height
}
```

## Accessibility
- **ARIA:** `role="list"`, items have `role="listitem"`
- **Keyboard:** Standard scroll behavior; arrow keys for item focus
- **Focus:** Visible focus ring on focused item

## Loading
- Skeleton placeholder matching item height during initial render
- Loading spinner at bottom for infinite scroll
- Smooth scroll restoration on data append

## Errors
- Empty state when items array is empty
- Graceful handling of measurement failures

## Keyboard
| Key | Action |
|-----|--------|
| ArrowDown | Focus next item |
| ArrowUp | Focus previous item |
| PageDown | Scroll by viewport height |
| PageUp | Scroll up by viewport height |
| Home | Scroll to top |
| End | Scroll to bottom |

## Mobile
- Touch scrolling with momentum
- Reduced overscan (2-3 items) for memory efficiency
- Pull-to-refresh integration point

## Permissions
- No restrictions — pure rendering optimization

## Telemetry
- `virtual_list.scroll` — Scroll events (throttled)
- `virtual_list.end_reached` — Infinite scroll triggered

## React Query
- Parent manages infinite query with `useInfiniteQuery`
- `onEndReached` triggers `fetchNextPage()`

## Dependencies
- None — standalone utility component

## Future Extensions
- Variable height with measurement cache
- Horizontal virtual scrolling
- Grid layout mode (virtualized grid)
- Window resize observer for dynamic height

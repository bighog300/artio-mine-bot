# Phase 3+ Advanced Mobile Enhancements - TODO

**Optional mobile features to enhance user experience**

---

## 📋 OVERVIEW

Phase 3 is complete with all 21 pages mobile-responsive. These are **optional enhancements** that can further improve the mobile experience based on user feedback and usage patterns.

**Status:** Not started (optional)  
**Priority:** Low to Medium  
**Estimated Time:** 12-20 hours  
**When to do:** After Phase 4 (Accessibility) or based on user demand

---

## 🎯 ENHANCEMENT CATEGORIES

### 1. Touch Gestures
### 2. Progressive Web App (PWA)
### 3. Mobile-Specific Features
### 4. Performance Optimizations
### 5. Advanced Interactions

---

## 1️⃣ TOUCH GESTURES

### Swipe Navigation

**What:** Swipe left/right to navigate between records/pages  
**Where:** RecordDetail, SourceDetail, JobDetail  
**Effort:** 3-4 hours  
**Value:** Medium

**Implementation:**

```typescript
// Install dependency
npm install react-swipeable

// In RecordDetail.tsx
import { useSwipeable } from 'react-swipeable';

const handlers = useSwipeable({
  onSwipedLeft: () => navigate(`/records/${nextId}`),
  onSwipedRight: () => navigate(`/records/${prevId}`),
  preventDefaultTouchmoveEvent: true,
  trackMouse: false, // Only touch devices
});

return <div {...handlers}>{content}</div>;
```

**Pages to add:**
- [ ] RecordDetail - Swipe between records
- [ ] SourceDetail - Swipe between sources
- [ ] JobDetail - Swipe between jobs
- [ ] ImageViewer - Swipe through images

**Testing:**
- [ ] Swipe left advances
- [ ] Swipe right goes back
- [ ] Works on iOS Safari
- [ ] Works on Chrome Android
- [ ] Doesn't interfere with scrolling

---

### Pull to Refresh

**What:** Pull down on lists to refresh data  
**Where:** Sources, Records, Jobs, Logs  
**Effort:** 2-3 hours  
**Value:** High (common mobile pattern)

**Implementation:**

```typescript
// Create hook: usePullToRefresh
export function usePullToRefresh(onRefresh: () => Promise<void>) {
  const [isPulling, setIsPulling] = useState(false);
  const [pullDistance, setPullDistance] = useState(0);
  const startY = useRef(0);
  
  const handleTouchStart = (e: TouchEvent) => {
    if (window.scrollY === 0) {
      startY.current = e.touches[0].clientY;
    }
  };
  
  const handleTouchMove = (e: TouchEvent) => {
    if (startY.current && window.scrollY === 0) {
      const currentY = e.touches[0].clientY;
      const distance = currentY - startY.current;
      
      if (distance > 0) {
        setPullDistance(Math.min(distance, 100));
        if (distance > 80) {
          setIsPulling(true);
        }
      }
    }
  };
  
  const handleTouchEnd = async () => {
    if (isPulling) {
      await onRefresh();
    }
    setIsPulling(false);
    setPullDistance(0);
    startY.current = 0;
  };
  
  return { isPulling, pullDistance };
}

// Usage
const { isPulling, pullDistance } = usePullToRefresh(async () => {
  await fetchSources();
});
```

**Pages to add:**
- [ ] Sources list
- [ ] Records list
- [ ] Jobs list
- [ ] Workers list
- [ ] Logs view

**Features:**
- [ ] Visual indicator (spinner or arrow)
- [ ] Haptic feedback (if available)
- [ ] Smooth animation
- [ ] Threshold at 80px pull

---

### Long Press Actions

**What:** Long press on items for quick actions  
**Where:** Lists (Sources, Records, Jobs)  
**Effort:** 2-3 hours  
**Value:** Medium

**Implementation:**

```typescript
export function useLongPress(
  onLongPress: () => void,
  delay = 500
) {
  const timeout = useRef<NodeJS.Timeout>();
  
  const start = () => {
    timeout.current = setTimeout(onLongPress, delay);
  };
  
  const clear = () => {
    if (timeout.current) {
      clearTimeout(timeout.current);
    }
  };
  
  return {
    onTouchStart: start,
    onTouchEnd: clear,
    onTouchMove: clear,
  };
}

// Usage
const longPressHandlers = useLongPress(() => {
  setShowContextMenu(true);
});

<div {...longPressHandlers}>Item</div>
```

**Actions to enable:**
- [ ] Long press source → Quick actions menu
- [ ] Long press record → Edit/Delete/Share
- [ ] Long press job → Cancel/Restart
- [ ] Visual feedback during press

---

## 2️⃣ PROGRESSIVE WEB APP (PWA)

### Install Prompt

**What:** Allow users to install app to home screen  
**Effort:** 4-6 hours  
**Value:** High (native-like experience)

**Implementation:**

```typescript
// 1. Create manifest.json
{
  "name": "Artio Mine Bot",
  "short_name": "Artio",
  "description": "Web mining and data extraction tool",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#3b82f6",
  "icons": [
    {
      "src": "/icons/icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/icons/icon-512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}

// 2. Create service worker
// public/sw.js
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open('artio-v1').then((cache) => {
      return cache.addAll([
        '/',
        '/index.html',
        '/assets/index.js',
        '/assets/index.css',
      ]);
    })
  );
});

// 3. Register service worker
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js');
}

// 4. Add install prompt
const [showInstallPrompt, setShowInstallPrompt] = useState(false);
const deferredPrompt = useRef<any>(null);

useEffect(() => {
  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault();
    deferredPrompt.current = e;
    setShowInstallPrompt(true);
  });
}, []);

const handleInstall = async () => {
  if (deferredPrompt.current) {
    deferredPrompt.current.prompt();
    const { outcome } = await deferredPrompt.current.userChoice;
    deferredPrompt.current = null;
    setShowInstallPrompt(false);
  }
};
```

**Tasks:**
- [ ] Create manifest.json
- [ ] Design app icons (192px, 512px)
- [ ] Implement service worker
- [ ] Add install prompt UI
- [ ] Test on iOS (Add to Home Screen)
- [ ] Test on Android (Install app)

---

### Offline Support

**What:** App works without internet for viewed pages  
**Effort:** 6-8 hours  
**Value:** Medium

**Implementation:**

```typescript
// Service worker with offline strategy
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request).then((fetchResponse) => {
        return caches.open('artio-v1').then((cache) => {
          cache.put(event.request, fetchResponse.clone());
          return fetchResponse;
        });
      });
    }).catch(() => {
      // Return offline page
      return caches.match('/offline.html');
    })
  );
});

// Show offline indicator
const [isOnline, setIsOnline] = useState(navigator.onLine);

useEffect(() => {
  const handleOnline = () => setIsOnline(true);
  const handleOffline = () => setIsOnline(false);
  
  window.addEventListener('online', handleOnline);
  window.addEventListener('offline', handleOffline);
  
  return () => {
    window.removeEventListener('online', handleOnline);
    window.removeEventListener('offline', handleOffline);
  };
}, []);

{!isOnline && (
  <Alert variant="warning">
    You're offline. Some features may be limited.
  </Alert>
)}
```

**Tasks:**
- [ ] Implement offline caching strategy
- [ ] Create offline fallback page
- [ ] Show offline indicator
- [ ] Queue actions when offline
- [ ] Sync when back online

---

## 3️⃣ MOBILE-SPECIFIC FEATURES

### Native Share API

**What:** Share records/sources via native share sheet  
**Effort:** 1-2 hours  
**Value:** Medium

**Implementation:**

```typescript
async function handleShare(item: Record) {
  if (navigator.share) {
    try {
      await navigator.share({
        title: item.title,
        text: `Check out this record: ${item.title}`,
        url: `${window.location.origin}/records/${item.id}`,
      });
    } catch (err) {
      // User cancelled or error
      console.log('Share failed', err);
    }
  } else {
    // Fallback: copy to clipboard
    navigator.clipboard.writeText(
      `${window.location.origin}/records/${item.id}`
    );
    toast.success('Link copied to clipboard');
  }
}

// Add share button
<IconButton 
  onClick={() => handleShare(record)}
  aria-label="Share"
>
  <Share className="h-4 w-4" />
</IconButton>
```

**Add to:**
- [ ] RecordDetail
- [ ] SourceDetail
- [ ] Search results
- [ ] Export page

---

### Camera Integration

**What:** Take photos directly from mobile for image upload  
**Effort:** 2-3 hours  
**Value:** Medium (if users upload images)

**Implementation:**

```typescript
// Add camera input
<input
  type="file"
  accept="image/*"
  capture="environment" // Use back camera
  onChange={handleImageCapture}
  className="hidden"
  ref={cameraInputRef}
/>

<Button
  onClick={() => cameraInputRef.current?.click()}
  fullWidth
>
  <Camera className="h-4 w-4" />
  Take Photo
</Button>

const handleImageCapture = async (e: React.ChangeEvent<HTMLInputElement>) => {
  const file = e.target.files?.[0];
  if (file) {
    // Compress image
    const compressed = await compressImage(file);
    // Upload
    await uploadImage(compressed);
  }
};
```

**Add to:**
- [ ] Record creation
- [ ] Image upload forms
- [ ] Profile photos

---

### Location Services

**What:** Auto-detect location for location-based features  
**Effort:** 2-3 hours  
**Value:** Low (unless location is relevant)

**Implementation:**

```typescript
const [location, setLocation] = useState<{lat: number; lng: number} | null>(null);

const requestLocation = () => {
  if ('geolocation' in navigator) {
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocation({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        });
      },
      (error) => {
        console.error('Location error:', error);
      }
    );
  }
};
```

**Use cases:**
- [ ] Geo-tag records (if applicable)
- [ ] Show nearby sources (if applicable)
- [ ] Location-based search

---

### Haptic Feedback

**What:** Vibration feedback for actions  
**Effort:** 1 hour  
**Value:** Low (nice-to-have)

**Implementation:**

```typescript
function hapticFeedback(type: 'light' | 'medium' | 'heavy' = 'medium') {
  if ('vibrate' in navigator) {
    const patterns = {
      light: 10,
      medium: 20,
      heavy: 30,
    };
    navigator.vibrate(patterns[type]);
  }
}

// Usage
<Button
  onClick={() => {
    hapticFeedback('light');
    handleAction();
  }}
>
  Action
</Button>
```

**Add to:**
- [ ] Pull to refresh
- [ ] Swipe gestures
- [ ] Long press
- [ ] Important actions

---

## 4️⃣ PERFORMANCE OPTIMIZATIONS

### Image Lazy Loading

**What:** Load images only when visible  
**Effort:** 1-2 hours  
**Value:** High (faster page loads)

**Implementation:**

```typescript
// Already partially implemented with loading="lazy"
// Add intersection observer for more control

const ImageLazyLoad = ({ src, alt }: { src: string; alt: string }) => {
  const [isLoaded, setIsLoaded] = useState(false);
  const imgRef = useRef<HTMLImageElement>(null);
  
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsLoaded(true);
          observer.disconnect();
        }
      },
      { rootMargin: '50px' } // Load 50px before visible
    );
    
    if (imgRef.current) {
      observer.observe(imgRef.current);
    }
    
    return () => observer.disconnect();
  }, []);
  
  return (
    <img
      ref={imgRef}
      src={isLoaded ? src : '/placeholder.png'}
      alt={alt}
      className="w-full h-full object-cover"
    />
  );
};
```

**Apply to:**
- [ ] Records list (thumbnails)
- [ ] Images page
- [ ] Source previews

---

### Virtual Scrolling

**What:** Render only visible items in long lists  
**Effort:** 3-4 hours  
**Value:** High (for lists with 100+ items)

**Implementation:**

```typescript
import { useVirtualizer } from '@tanstack/react-virtual';

const parentRef = useRef<HTMLDivElement>(null);

const rowVirtualizer = useVirtualizer({
  count: items.length,
  getScrollElement: () => parentRef.current,
  estimateSize: () => 80, // Row height
  overscan: 5, // Render 5 extra rows
});

return (
  <div ref={parentRef} style={{ height: '600px', overflow: 'auto' }}>
    <div style={{ height: `${rowVirtualizer.getTotalSize()}px` }}>
      {rowVirtualizer.getVirtualItems().map((virtualRow) => (
        <div
          key={virtualRow.index}
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: `${virtualRow.size}px`,
            transform: `translateY(${virtualRow.start}px)`,
          }}
        >
          <ItemCard item={items[virtualRow.index]} />
        </div>
      ))}
    </div>
  </div>
);
```

**Apply to:**
- [ ] Records list (if > 100 items)
- [ ] Sources list (if > 100 items)
- [ ] Logs (already has virtual scroll)

---

### Code Splitting

**What:** Load page code only when needed  
**Effort:** 2-3 hours  
**Value:** Medium (faster initial load)

**Implementation:**

```typescript
// Use React.lazy for route-based splitting
import { lazy, Suspense } from 'react';

const Dashboard = lazy(() => import('./pages/Dashboard'));
const Sources = lazy(() => import('./pages/Sources'));
const Records = lazy(() => import('./pages/Records'));

<Routes>
  <Route
    path="/"
    element={
      <Suspense fallback={<LoadingSpinner />}>
        <Dashboard />
      </Suspense>
    }
  />
  <Route
    path="/sources"
    element={
      <Suspense fallback={<LoadingSpinner />}>
        <Sources />
      </Suspense>
    }
  />
</Routes>
```

**Apply to:**
- [ ] All route components
- [ ] Heavy components (charts, editors)
- [ ] Modals (load when opened)

---

### Bundle Optimization

**What:** Reduce JavaScript bundle size  
**Effort:** 2-3 hours  
**Value:** High

**Tasks:**
- [ ] Analyze bundle with `vite-bundle-visualizer`
- [ ] Tree-shake unused code
- [ ] Replace heavy dependencies
- [ ] Enable compression (gzip/brotli)
- [ ] Target modern browsers only

**Commands:**

```bash
# Analyze
npx vite-bundle-visualizer

# Check what can be removed
npm run build -- --analyze

# Optimize
# Remove unused dependencies
# Use lighter alternatives
```

---

## 5️⃣ ADVANCED INTERACTIONS

### Drag and Drop

**What:** Reorder items by dragging  
**Effort:** 3-4 hours  
**Value:** Medium

**Implementation:**

```typescript
// Use react-beautiful-dnd or @dnd-kit
import { DndContext, closestCenter } from '@dnd-kit/core';
import { arrayMove, SortableContext, useSortable } from '@dnd-kit/sortable';

function SortableItem({ id, item }) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id });
  
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };
  
  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      {item.name}
    </div>
  );
}

function handleDragEnd(event) {
  const { active, over } = event;
  if (active.id !== over.id) {
    setItems((items) => {
      const oldIndex = items.findIndex((i) => i.id === active.id);
      const newIndex = items.findIndex((i) => i.id === over.id);
      return arrayMove(items, oldIndex, newIndex);
    });
  }
}
```

**Add to:**
- [ ] Dashboard widgets
- [ ] Priority lists
- [ ] Image galleries

---

### Pinch to Zoom

**What:** Pinch to zoom images  
**Effort:** 2-3 hours  
**Value:** Medium (for image viewing)

**Implementation:**

```typescript
// Use react-pinch-zoom-pan or implement custom
import PinchZoomPan from 'react-pinch-zoom-pan';

<PinchZoomPan
  min={1}
  max={4}
  initialScale={1}
>
  <img src={imageUrl} alt="Zoomable" />
</PinchZoomPan>
```

**Add to:**
- [ ] Image viewer/gallery
- [ ] RecordDetail images
- [ ] Full-screen image mode

---

### Voice Input

**What:** Voice-to-text for search/forms  
**Effort:** 2-3 hours  
**Value:** Low (experimental)

**Implementation:**

```typescript
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const recognition = new SpeechRecognition();

recognition.onresult = (event) => {
  const transcript = event.results[0][0].transcript;
  setSearchQuery(transcript);
};

<IconButton onClick={() => recognition.start()}>
  <Mic />
</IconButton>
```

**Add to:**
- [ ] Search boxes
- [ ] Form inputs
- [ ] Notes/comments

---

## 📊 PRIORITY MATRIX

### High Value, Low Effort (Do First)
1. **Pull to Refresh** - 2-3 hours, high value
2. **Image Lazy Loading** - 1-2 hours, high value
3. **Native Share API** - 1-2 hours, medium value

### High Value, Medium Effort (Do Next)
4. **PWA Install Prompt** - 4-6 hours, high value
5. **Bundle Optimization** - 2-3 hours, high value
6. **Virtual Scrolling** - 3-4 hours, high value (if needed)

### Medium Value (Do Later)
7. **Swipe Navigation** - 3-4 hours
8. **Long Press Actions** - 2-3 hours
9. **Camera Integration** - 2-3 hours
10. **Code Splitting** - 2-3 hours

### Low Value (Nice to Have)
11. **Haptic Feedback** - 1 hour
12. **Offline Support** - 6-8 hours
13. **Voice Input** - 2-3 hours
14. **Location Services** - 2-3 hours

---

## 🎯 RECOMMENDED ROADMAP

### Phase 3.1: Quick Wins (4-6 hours)
- [ ] Pull to Refresh
- [ ] Image Lazy Loading
- [ ] Native Share API
- [ ] Haptic Feedback

### Phase 3.2: PWA (8-10 hours)
- [ ] PWA Install Prompt
- [ ] Service Worker
- [ ] App Icons
- [ ] Basic Offline Support

### Phase 3.3: Performance (6-8 hours)
- [ ] Bundle Optimization
- [ ] Code Splitting
- [ ] Virtual Scrolling (if needed)

### Phase 3.4: Advanced (8-12 hours)
- [ ] Swipe Navigation
- [ ] Long Press Actions
- [ ] Camera Integration
- [ ] Pinch to Zoom

**Total Time:** 26-36 hours for all enhancements

---

## 🔍 DECISION CRITERIA

**When to implement these:**

### User Demand
- Users request offline support → Priority ⬆️
- Users want to install app → PWA Priority ⬆️
- Users share content often → Share API Priority ⬆️

### Analytics
- High mobile traffic → All enhancements Priority ⬆️
- Slow load times → Performance Priority ⬆️
- High bounce rate on mobile → Quick Wins Priority ⬆️

### Business Goals
- Need native-like experience → PWA Priority ⬆️
- Need engagement → Gestures Priority ⬆️
- Need performance → Optimization Priority ⬆️

---

## ✅ SUCCESS METRICS

Track these after implementation:

### Engagement
- [ ] Time on site (mobile)
- [ ] Pages per session
- [ ] Return visit rate

### Performance
- [ ] Lighthouse mobile score
- [ ] Time to interactive
- [ ] Bounce rate

### Adoption
- [ ] PWA install rate
- [ ] Offline usage
- [ ] Share actions

---

## 📝 NOTES

- These are **optional** enhancements
- Phase 4 (Accessibility) is higher priority
- Implement based on user feedback
- Start with high-value, low-effort items
- Measure impact before continuing

---

**Last Updated:** Phase 3 Complete  
**Status:** Planning / Not Started  
**Next Review:** After Phase 4 or based on user requests

---

## 🚀 GETTING STARTED

When ready to implement:

1. Review analytics and user feedback
2. Prioritize based on demand
3. Start with Phase 3.1 (Quick Wins)
4. Measure impact
5. Continue based on results

**Don't implement all at once!** Pick 2-3 features, implement, measure, then decide what's next.

---

**End of Phase 3+ TODO**

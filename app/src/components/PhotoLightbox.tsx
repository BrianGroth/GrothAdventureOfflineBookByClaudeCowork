import { useEffect, useCallback } from 'react'

interface Photo {
  url: string
  alt?: string
  caption?: string
  width?: number
  height?: number
}

interface PhotoLightboxProps {
  photos: Photo[]
  currentIndex: number
  onClose: () => void
  onPrev: () => void
  onNext: () => void
}

export default function PhotoLightbox({
  photos,
  currentIndex,
  onClose,
  onPrev,
  onNext,
}: PhotoLightboxProps) {
  const photo = photos[currentIndex]

  const handleKey = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
      else if (e.key === 'ArrowLeft') onPrev()
      else if (e.key === 'ArrowRight') onNext()
    },
    [onClose, onPrev, onNext],
  )

  useEffect(() => {
    document.addEventListener('keydown', handleKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', handleKey)
      document.body.style.overflow = ''
    }
  }, [handleKey])

  if (!photo) return null

  // Clicking anywhere — including the photo itself — closes the lightbox;
  // only the prev/next arrows stop the click from bubbling.
  return (
    <div className="lightbox" onClick={onClose} role="dialog" aria-label="Photo viewer">
      {photos.length > 1 && (
        <button
          className="lightbox-arrow prev"
          onClick={(e) => { e.stopPropagation(); onPrev() }}
          aria-label="Previous photo"
        >
          ‹
        </button>
      )}

      <figure className="lightbox-stage">
        <img src={photo.url} alt={photo.alt || ''} title="Click to close" />
        {photo.caption && <figcaption>{photo.caption}</figcaption>}
        <p className="lightbox-counter">{currentIndex + 1} / {photos.length}</p>
      </figure>

      {photos.length > 1 && (
        <button
          className="lightbox-arrow next"
          onClick={(e) => { e.stopPropagation(); onNext() }}
          aria-label="Next photo"
        >
          ›
        </button>
      )}
    </div>
  )
}

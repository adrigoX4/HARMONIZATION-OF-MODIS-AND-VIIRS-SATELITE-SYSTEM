import React from 'react'

/**
 * The one loading primitive: a rounded block in the --skel-base token with a
 * left-to-right shimmer (opacity pulse under prefers-reduced-motion).
 *
 *   <Skeleton width="60%" height={12} />
 *   <Skeleton width={160} height={180} radius="var(--r-ctl)" raised />
 *
 * `raised` draws it as a card-coloured block with a hairline, for shapes that
 * sit on top of another skeleton (e.g. the map legend).
 */
export default function Skeleton({ width = '100%', height = 12, radius, raised = false, className = '', style, as: Tag = 'span' }) {
  return (
    <Tag
      aria-hidden="true"
      className={`skeleton ${raised ? 'skeleton-raised' : ''} ${className}`}
      style={{ width, height, ...(radius !== undefined ? { borderRadius: radius } : null), ...style }}
    />
  )
}

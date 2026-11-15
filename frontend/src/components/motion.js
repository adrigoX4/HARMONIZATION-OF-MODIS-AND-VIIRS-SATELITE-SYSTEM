// One easing curve and a single fade-and-rise entrance per page.
export const EASE = [0.22, 1, 0.36, 1]

export const pageVariants = {
  hidden: { opacity: 0, y: 8 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.32, ease: EASE, staggerChildren: 0.05 },
  },
  exit: { opacity: 0, transition: { duration: 0.14, ease: EASE } },
}

export const itemVariants = {
  hidden: { opacity: 0, y: 8 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.32, ease: EASE } },
}

export const pageProps = {
  className: 'page',
  variants: pageVariants,
  initial: 'hidden',
  animate: 'visible',
  exit: 'exit',
}

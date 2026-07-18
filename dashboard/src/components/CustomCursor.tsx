import { useEffect, useRef } from 'react';

export function CustomCursor() {
  const dotRef = useRef<HTMLDivElement>(null);
  const ringRef = useRef<HTMLDivElement>(null);
  const requestRef = useRef<number>(0);
  
  // Real mouse position
  const mouse = useRef({ x: 0, y: 0 });
  // Interpolated ring position
  const ring = useRef({ x: 0, y: 0 });
  // Hover state
  const isHovering = useRef(false);

  useEffect(() => {
    // Hide default cursor on mount
    document.documentElement.style.cursor = 'none';

    const onMouseMove = (e: MouseEvent) => {
      mouse.current.x = e.clientX;
      mouse.current.y = e.clientY;

      // Update dot instantly
      if (dotRef.current) {
        dotRef.current.style.transform = `translate3d(${e.clientX}px, ${e.clientY}px, 0)`;
      }

      // Check hover state (if hovering over clickable elements)
      const target = e.target as HTMLElement;
      const isClickable = target.tagName.toLowerCase() === 'button' || 
                          target.tagName.toLowerCase() === 'a' || 
                          target.tagName.toLowerCase() === 'input' || 
                          target.closest('button') || 
                          target.closest('a');
      
      if (isClickable && !isHovering.current) {
        isHovering.current = true;
        if (ringRef.current) {
          ringRef.current.classList.add('cursor-hover');
        }
      } else if (!isClickable && isHovering.current) {
        isHovering.current = false;
        if (ringRef.current) {
          ringRef.current.classList.remove('cursor-hover');
        }
      }
    };

    const render = () => {
      // Lerp the ring towards the mouse
      // 0.2 is the lerp factor (higher = faster, lower = smoother but more trailing)
      ring.current.x += (mouse.current.x - ring.current.x) * 0.2;
      ring.current.y += (mouse.current.y - ring.current.y) * 0.2;

      if (ringRef.current) {
        ringRef.current.style.transform = `translate3d(${ring.current.x}px, ${ring.current.y}px, 0)`;
      }

      requestRef.current = requestAnimationFrame(render);
    };

    window.addEventListener('mousemove', onMouseMove, { passive: true });
    requestRef.current = requestAnimationFrame(render);

    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      cancelAnimationFrame(requestRef.current);
      document.documentElement.style.cursor = 'auto';
    };
  }, []);

  return (
    <>
      <div 
        ref={ringRef}
        className="fixed top-0 left-0 w-8 h-8 -ml-4 -mt-4 rounded-full border border-[#00ffcc]/50 pointer-events-none z-[9999] transition-[background-color,border-color,width,height,margin] duration-300 ease-out flex items-center justify-center will-change-transform"
        style={{ 
          boxShadow: '0 0 15px rgba(0,255,204,0.1), inset 0 0 10px rgba(0,255,204,0.1)',
          backdropFilter: 'blur(2px)'
        }}
      >
        {/* Inner crosshair lines for sci-fi look */}
        <div className="absolute w-[2px] h-[6px] bg-[#00ffcc]/30 top-0 left-1/2 -translate-x-1/2" />
        <div className="absolute w-[2px] h-[6px] bg-[#00ffcc]/30 bottom-0 left-1/2 -translate-x-1/2" />
        <div className="absolute w-[6px] h-[2px] bg-[#00ffcc]/30 left-0 top-1/2 -translate-y-1/2" />
        <div className="absolute w-[6px] h-[2px] bg-[#00ffcc]/30 right-0 top-1/2 -translate-y-1/2" />
      </div>
      
      <div 
        ref={dotRef}
        className="fixed top-0 left-0 w-2 h-2 -ml-1 -mt-1 bg-[#00ffcc] rounded-full pointer-events-none z-[10000] will-change-transform drop-shadow-[0_0_5px_rgba(0,255,204,1)]"
      />
    </>
  );
}

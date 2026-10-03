// grid.js — 2D virtualized grid for 200k cams
// Renders only the visible tiles based on scroll position.

export class VirtualGrid {
  /**
   * @param {HTMLElement} canvas - the grid canvas container (absolutely positioned tiles go here)
   * @param {HTMLElement} scroller - the scrollable parent
   * @param {Object} opts
   * @param {Function} opts.render - (cam, index) => HTMLElement
   * @param {Function} opts.dispose - (tile, cam, index) => void  (cleanup before re-render or remove)
   * @param {number} opts.tileWidth - tile width in px
   * @param {number} opts.tileHeight - tile height in px (including media + meta)
   * @param {number} opts.gap - gap between tiles
   * @param {number} opts.cols - number of columns (computed if not given)
   */
  constructor(canvas, scroller, opts) {
    this.canvas = canvas;
    this.scroller = scroller;
    this.render = opts.render;
    this.dispose = opts.dispose || (() => {});
    this.tileWidth = opts.tileWidth || 320;
    this.tileHeight = opts.tileHeight || 240;
    this.gap = opts.gap || 8;
    this.explicitCols = opts.cols || null;

    this.data = [];
    this.cols = 1;
    this.rows = 0;
    this._tiles = new Map(); // idx -> { node, cam, index }
    this._scheduled = false;
    this._lastRange = { start: -1, end: -1 };

    this._onScroll = this._onScroll.bind(this);
    this._onResize = this._onResize.bind(this);
    scroller.addEventListener('scroll', this._onScroll, { passive: true });
    window.addEventListener('resize', this._onResize);
    this._ro = new ResizeObserver(() => this._onResize());
    this._ro.observe(scroller);

    this._onResize();
  }

  setData(data) {
    this.data = data;
    // Clear existing tiles
    for (const { node } of this._tiles.values()) {
      this.canvas.removeChild(node);
    }
    this._tiles.clear();
    this._lastRange = { start: -1, end: -1 };
    this._computeLayout();
    this._setCanvasHeight();
    this._scheduleRender();
  }

  _computeLayout() {
    const w = this.scroller.clientWidth - 0; // padding accounted for by canvas
    this.cols = this.explicitCols || Math.max(1, Math.floor((w + this.gap) / (this.tileWidth + this.gap)));
    this.rows = Math.ceil(this.data.length / this.cols);
  }

  _setCanvasHeight() {
    const h = this.rows * this.tileHeight + (this.rows - 1) * this.gap;
    this.canvas.style.height = `${h}px`;
  }

  _onScroll() { this._scheduleRender(); }
  _onResize() {
    this._computeLayout();
    this._setCanvasHeight();
    // Invalidate tiles because columns changed
    this._lastRange = { start: -1, end: -1 };
    for (const { node } of this._tiles.values()) {
      this.canvas.removeChild(node);
    }
    this._tiles.clear();
    this._scheduleRender();
  }

  _scheduleRender() {
    if (this._scheduled) return;
    this._scheduled = true;
    requestAnimationFrame(() => {
      this._scheduled = false;
      this._render();
    });
  }

  _render() {
    if (!this.data.length || !this.cols) return;
    const scrollTop = this.scroller.scrollTop;
    const scrollBottom = scrollTop + this.scroller.clientHeight;
    const rowH = this.tileHeight + this.gap;

    // 1 row overscan each side is enough; IntersectionObserver
    // (in app.js with rootMargin 400px) handles the prefetch.
    const overscan = 1;
    const firstRow = Math.max(0, Math.floor(scrollTop / rowH) - overscan);
    const lastRow = Math.min(this.rows - 1, Math.ceil(scrollBottom / rowH) + overscan);

    const startIdx = firstRow * this.cols;
    const endIdx = Math.min(this.data.length, (lastRow + 1) * this.cols);

    // Near-end detection: 80% scrolled → fire onNearEnd
    if (this.onNearEnd && this.data.length >= 200) {
      const scrollPct = scrollBottom / (this.rows * rowH);
      if (scrollPct > 0.8) {
        try { this.onNearEnd(); } catch {}
      }
    }

    // Remove tiles outside range
    for (const [idx, entry] of this._tiles.entries()) {
      if (idx < startIdx || idx >= endIdx) {
        this.canvas.removeChild(entry.node);
        try { this.dispose(entry.node, entry.cam, idx); } catch {}
        this._tiles.delete(idx);
      }
    }

    // Render tiles in range
    for (let i = startIdx; i < endIdx; i++) {
      if (this._tiles.has(i)) continue;
      const cam = this.data[i];
      if (!cam) continue;
      let node;
      try { node = this.render(cam, i); }
      catch (e) { continue; }
      const row = Math.floor(i / this.cols);
      const col = i % this.cols;
      node.style.width = `${this.tileWidth}px`;
      node.style.height = `${this.tileHeight}px`;
      node.style.transform = `translate3d(${col * (this.tileWidth + this.gap)}px, ${row * rowH}px, 0)`;
      this.canvas.appendChild(node);
      this._tiles.set(i, { node, cam });
    }
  }

  destroy() {
    this.scroller.removeEventListener('scroll', this._onScroll);
    window.removeEventListener('resize', this._onResize);
    this._ro.disconnect();
    for (const { node } of this._tiles.values()) {
      this.canvas.removeChild(node);
    }
    this._tiles.clear();
  }
}